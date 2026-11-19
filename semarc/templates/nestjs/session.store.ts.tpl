import { Injectable } from '@nestjs/common';
import { createHash, randomBytes } from 'crypto';
import { Request, Response } from 'express';
import { DataSource, IsNull } from 'typeorm';
import { settings } from '../../config/settings';
import { nowUtc } from '../../database/column-types';
import { UserSession } from './session.entity';

export const SESSION_COOKIE = '{{cookie}}';
export const CSRF_COOKIE = '{{csrf_cookie}}';
export const CSRF_HEADER = '{{csrf_header_lower}}';

export const hashToken = (token: string): string => createHash('sha256').update(token).digest('hex');

/** Value of a request cookie, or undefined. */
export function readCookie(request: Request, name: string): string | undefined {
  for (const pair of (request.headers.cookie ?? '').split(';')) {
    const index = pair.indexOf('=');
    if (index > 0 && pair.slice(0, index).trim() === name) {
      return decodeURIComponent(pair.slice(index + 1).trim());
    }
  }
  return undefined;
}

function setCookie(response: Response, name: string, value: string, maxAgeSeconds: number, httpOnly: boolean): void {
  response.cookie(name, value, {
    path: '/',
    maxAge: maxAgeSeconds * 1000,
    sameSite: 'lax',
    httpOnly,
    secure: settings.sessionSecureCookie,
  });
}

/**
 * Server-side sessions behind an HttpOnly cookie. POST, PUT, PATCH and DELETE requests must
 * send the CSRF token (also readable from the {{csrf_cookie}} cookie) in the {{csrf_header}} header.
 */
@Injectable()
export class SessionStore {
  constructor(private readonly dataSource: DataSource) {}

  /** Starts a session and sets the session and CSRF cookies. */
  async issue(userId: number, response: Response): Promise<{ csrf_token: string; expires_in: number }> {
    const token = randomBytes(32).toString('hex');
    const csrf = randomBytes(32).toString('hex');
    const now = nowUtc();
    await this.dataSource.getRepository(UserSession).insert({
      user_id: userId,
      token_hash: hashToken(token),
      csrf_hash: hashToken(csrf),
      expires_at: new Date(now.getTime() + settings.sessionTtl * 1000),
      revoked_at: null,
      created_at: now,
      updated_at: now,
    });
    setCookie(response, SESSION_COOKIE, token, settings.sessionTtl, true);
    setCookie(response, CSRF_COOKIE, csrf, settings.sessionTtl, false);
    return { csrf_token: csrf, expires_in: settings.sessionTtl };
  }

  /** The active session for a cookie value, or null when missing, ended or expired. */
  async find(token: string | undefined): Promise<UserSession | null> {
    if (!token) {
      return null;
    }
    const record = await this.dataSource.getRepository(UserSession).findOne({ where: { token_hash: hashToken(token) } });
    if (!record || record.revoked_at !== null || record.expires_at.getTime() <= Date.now()) {
      return null;
    }
    return record;
  }

  /** Ends a session and clears its cookies. */
  async end(token: string | undefined, response: Response): Promise<void> {
    if (token) {
      await this.dataSource
        .getRepository(UserSession)
        .update({ token_hash: hashToken(token), revoked_at: IsNull() }, { revoked_at: nowUtc(), updated_at: nowUtc() });
    }
    setCookie(response, SESSION_COOKIE, '', 0, true);
    setCookie(response, CSRF_COOKIE, '', 0, false);
  }

  async revokeAll(userId: number): Promise<void> {
    await this.dataSource
      .getRepository(UserSession)
      .update({ user_id: userId, revoked_at: IsNull() }, { revoked_at: nowUtc(), updated_at: nowUtc() });
  }
}
