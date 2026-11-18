import { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import { readFileSync } from 'fs';
import { join } from 'path';
import request from 'supertest';
import { AppModule } from '../src/app.module';
import { configureApp } from '../src/app.setup';

interface MailCheck {
  to: string;
  subject: string;
  pattern: string;
  save: string;
}

interface Step {
  name: string;
  mail?: MailCheck;
  external?: string;
  csrf?: boolean;
  method: string;
  path: string;
  expect: number | number[];
  headers?: Record<string, string>;
  expect_headers?: Record<string, string>;
  auth?: boolean;
  auth_as?: string;
  token?: string;
  body?: unknown;
  equals?: Record<string, unknown>;
  absent?: string[];
  save?: Record<string, string>;
}

const MISSING = Symbol('missing');
interface SessionSettings {
  cookie: string;
  csrf_cookie: string;
  csrf_header: string;
}

const scenario: { steps: Step[]; session?: SessionSettings } = JSON.parse(readFileSync(join(__dirname, 'api_scenario.json'), 'utf8'));

function dig(data: unknown, path: string): unknown {
  let current: unknown = data;
  for (const key of path.split('.')) {
    if (current === null || typeof current !== 'object' || Array.isArray(current) || !(key in current)) {
      return MISSING;
    }
    current = (current as Record<string, unknown>)[key];
  }
  return current;
}

function resolve(value: unknown, variables: Record<string, unknown>): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => resolve(item, variables));
  }
  if (value !== null && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 1 && entries[0][0] === '$ref') {
      return variables[entries[0][1] as string];
    }
    return Object.fromEntries(entries.map(([key, item]) => [key, resolve(item, variables)]));
  }
  return value;
}

function readMail(name: string, mail: MailCheck): string {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { Mailer } = require('../src/common/mailer') as { Mailer: { outbox: { to: string; subject: string; body: string }[] } };
  for (const message of [...Mailer.outbox].reverse()) {
    if (message.to === mail.to && message.subject === mail.subject) {
      const match = new RegExp(mail.pattern).exec(message.body);
      if (match) {
        return match[1];
      }
    }
  }
  throw new Error(`${name}: no email "${mail.subject}" to ${mail.to} matching ${mail.pattern}`);
}

describe('API scenario (test/api_scenario.json)', () => {
  let app: INestApplication;

  beforeAll(async () => {
    const moduleRef = await Test.createTestingModule({ imports: [AppModule] }).compile();
    app = moduleRef.createNestApplication();
    configureApp(app);
    await app.init();
  });

  afterAll(async () => {
    await app.close();
  });

  it('replays every step', async () => {
    const variables: Record<string, unknown> = {};
    // AUTH SESSION: credentials are a session cookie per saved variable plus a CSRF header.
    const session = scenario.session;
    const sessionCookies: Record<string, string> = {};
    for (const step of scenario.steps) {
      if (step.external) {
        continue; // needs an external service (see the scenario description)
      }
      if (step.mail) {
        variables[step.mail.save] = readMail(step.name, step.mail);
        continue;
      }
      const path = step.path.replace(/\$\{(\w+)\}/g, (_match, name: string) => String(variables[name] ?? ''));
      const method = step.method.toLowerCase() as 'get' | 'post' | 'put' | 'patch' | 'delete' | 'options';
      let call = request(app.getHttpServer())[method](path);
      for (const [name, value] of Object.entries(step.headers ?? {})) {
        call = call.set(name, value);
      }
      let credential: [string, string] | undefined;
      if (step.auth) {
        const name = step.auth_as ?? 'token';
        credential = [sessionCookies[name] ?? '', String(variables[name] ?? '')];
      }
      if (step.token) {
        credential = [step.token, step.token];
      }
      if (credential && !session) {
        call = call.set('Authorization', `Bearer ${credential[1]}`);
      } else if (credential && session) {
        call = call.set('Cookie', `${session.cookie}=${credential[0]}`);
        if (!['GET', 'HEAD', 'OPTIONS'].includes(step.method) && step.csrf !== false) {
          call = call.set(session.csrf_header, credential[1]);
        }
      }
      const response = step.body !== undefined ? await call.send(resolve(step.body, variables) as object) : await call;
      const label = `${step.name} (${step.method} ${path}): ${response.text.slice(0, 300)}`;

      const expected = Array.isArray(step.expect) ? step.expect : [step.expect];
      expect({ step: label, status: expected.includes(response.status) }).toEqual({ step: label, status: true });
      for (const [name, value] of Object.entries(step.expect_headers ?? {})) {
        expect({ step: label, header: name, value: response.headers[name.toLowerCase()] }).toEqual({ step: label, header: name, value });
      }
      for (const [jsonPath, expected] of Object.entries(step.equals ?? {})) {
        expect({ step: label, path: jsonPath, value: dig(response.body, jsonPath) }).toEqual({
          step: label,
          path: jsonPath,
          value: resolve(expected, variables),
        });
      }
      for (const jsonPath of step.absent ?? []) {
        expect({ step: label, absent: dig(response.body, jsonPath) === MISSING }).toEqual({ step: label, absent: true });
      }
      let issued: string | undefined;
      const setCookies = response.headers['set-cookie'] as unknown as string[] | undefined;
      for (const cookie of session ? (setCookies ?? []) : []) {
        if (session && cookie.startsWith(`${session.cookie}=`)) {
          const attributes = cookie.toLowerCase();
          expect({ step: label, cookie, secure: attributes.includes('httponly') && attributes.includes('samesite=lax') }).toEqual({
            step: label,
            cookie,
            secure: true,
          });
          issued = decodeURIComponent(cookie.split(';')[0].slice(session.cookie.length + 1));
        }
      }
      for (const [name, jsonPath] of Object.entries(step.save ?? {})) {
        variables[name] = dig(response.body, jsonPath);
        if (issued !== undefined && jsonPath.endsWith('csrf_token')) {
          sessionCookies[name] = issued;
        }
      }
    }
  });
});
