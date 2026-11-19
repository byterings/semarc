import { createHmac, randomBytes, timingSafeEqual } from 'crypto';
import { ApiError } from '../../common/api-error';
import { settings } from '../../config/settings';

/**
 * Sign-in with OAuth providers (authorization code flow).
 *
 * GET /oauth/<provider> returns the provider authorization URL and a signed `state`. The
 * front end sends the user there; the provider redirects back to OAUTH_<PROVIDER>_REDIRECT_URI
 * with `code` and `state`, which the front end posts to POST /oauth/<provider>/callback. The
 * front end must check that the returned `state` equals the one it received.
 */
const STATE_TTL_SECONDS = {{state_ttl}};
const TIMEOUT_MS = 10000;
const MIN_SECRET_LENGTH = 32;

interface ProviderDetails {
  authorize_url: string;
  token_url: string;
  profile_url: string;
  emails_url: string | null;
  scopes: string[];
  subject_field: string;
  email_field: string | null;
  verified_field: string | null;
  name_field: string;
}

interface ProviderConfig {
  clientId: string;
  clientSecret: string;
  redirectUri: string;
  endpoint: string;
}

export interface OAuthIdentity {
  subject: string;
  email: string;
  name: string;
}

const PROVIDERS: Record<string, ProviderDetails> = {{providers}};

function config(provider: string): ProviderConfig {
  const prefix = `OAUTH_${provider.toUpperCase()}`;
  const values = {
    clientId: process.env[`${prefix}_CLIENT_ID`] ?? '',
    clientSecret: process.env[`${prefix}_CLIENT_SECRET`] ?? '',
    redirectUri: process.env[`${prefix}_REDIRECT_URI`] ?? '',
    endpoint: process.env[`${prefix}_ENDPOINT`] ?? '',
  };
  if (!values.clientId || !values.clientSecret || !values.redirectUri) {
    throw new ApiError(503, 'service_unavailable', `OAuth provider ${provider} is not configured.`);
  }
  return values;
}

/** OAUTH_<PROVIDER>_ENDPOINT replaces the provider origin (used with a mock provider in tests). */
function url(values: ProviderConfig, address: string): string {
  if (!values.endpoint) {
    return address;
  }
  const target = new URL(address);
  const endpoint = new URL(values.endpoint);
  target.protocol = endpoint.protocol;
  target.host = endpoint.host;
  return target.toString();
}

function signature(payload: string): string {
  if (settings.jwtSecret.length < MIN_SECRET_LENGTH) {
    throw new Error(`JWT_SECRET must be set to at least ${MIN_SECRET_LENGTH} characters.`);
  }
  return createHmac('sha256', settings.jwtSecret).update(`oauth-state:${payload}`).digest('hex');
}

async function request(provider: string, address: string, form?: Record<string, string>, token?: string): Promise<unknown> {
  const headers: Record<string, string> = { Accept: 'application/json', 'User-Agent': settings.appName };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  let response: Response;
  try {
    response = await fetch(address, {
      method: form ? 'POST' : 'GET',
      headers: form ? { ...headers, 'Content-Type': 'application/x-www-form-urlencoded' } : headers,
      body: form ? new URLSearchParams(form).toString() : undefined,
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch {
    throw new ApiError(502, 'bad_gateway', `OAuth provider ${provider} is unavailable.`);
  }
  if (response.status >= 400) {
    if (form && response.status < 500) {
      throw ApiError.validation({ code: ['code is invalid or expired'] });
    }
    throw new ApiError(502, 'bad_gateway', `OAuth provider ${provider} returned an error.`);
  }
  try {
    return await response.json();
  } catch {
    throw new ApiError(502, 'bad_gateway', `OAuth provider ${provider} returned invalid JSON.`);
  }
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value);

export const OAuth = {
  start(provider: string): { authorization_url: string; state: string } {
    const values = config(provider);
    const details = PROVIDERS[provider];
    const payload = `${provider}.${Math.floor(Date.now() / 1000) + STATE_TTL_SECONDS}.${randomBytes(16).toString('hex')}`;
    const state = `${payload}.${signature(payload)}`;
    const query = new URLSearchParams({
      response_type: 'code',
      client_id: values.clientId,
      redirect_uri: values.redirectUri,
      scope: details.scopes.join(' '),
      state,
    });
    return { authorization_url: `${url(values, details.authorize_url)}?${query.toString()}`, state };
  },

  verifyState(provider: string, state: string): void {
    const parts = state.split('.');
    const expected = parts.length === 4 ? Buffer.from(signature(parts.slice(0, 3).join('.'))) : Buffer.alloc(0);
    const given = Buffer.from(parts[3] ?? '');
    const valid =
      parts.length === 4 &&
      parts[0] === provider &&
      /^\d+$/.test(parts[1]) &&
      Number(parts[1]) > Date.now() / 1000 &&
      given.length === expected.length &&
      timingSafeEqual(given, expected);
    if (!valid) {
      throw ApiError.validation({ state: ['state is invalid or expired'] });
    }
  },

  /** Exchanges the code and returns the provider subject, verified email and display name. */
  async fetchIdentity(provider: string, code: string): Promise<OAuthIdentity> {
    const values = config(provider);
    const details = PROVIDERS[provider];
    const tokens = await request(provider, url(values, details.token_url), {
      grant_type: 'authorization_code',
      code,
      redirect_uri: values.redirectUri,
      client_id: values.clientId,
      client_secret: values.clientSecret,
    });
    const accessToken = isRecord(tokens) ? tokens.access_token : undefined;
    if (typeof accessToken !== 'string' || !accessToken) {
      throw ApiError.validation({ code: ['code is invalid or expired'] });
    }

    const profile = await request(provider, url(values, details.profile_url), undefined, accessToken);
    const subject = isRecord(profile) ? profile[details.subject_field] : undefined;
    if (!isRecord(profile) || (typeof subject !== 'string' && typeof subject !== 'number') || subject === '') {
      throw new ApiError(502, 'bad_gateway', `OAuth provider ${provider} returned an unexpected profile.`);
    }
    let email: unknown;
    if (details.emails_url) {
      const addresses = await request(provider, url(values, details.emails_url), undefined, accessToken);
      for (const address of Array.isArray(addresses) ? addresses : []) {
        if (isRecord(address) && address.primary === true && address.verified === true) {
          email = address.email;
        }
      }
    } else if (details.verified_field && profile[details.verified_field] === true && details.email_field) {
      email = profile[details.email_field];
    }
    if (typeof email !== 'string' || !email.includes('@')) {
      throw ApiError.validation({ email: [`${provider} did not confirm a verified email address`] });
    }

    const name = profile[details.name_field];
    const displayName = typeof name === 'string' && name.trim() ? name.trim() : email.split('@')[0];
    return { subject: `${provider}:${String(subject)}`, email, name: displayName };
  },
};
