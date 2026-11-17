import { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import { readFileSync } from 'fs';
import { join } from 'path';
import request from 'supertest';
import { AppModule } from '../src/app.module';
import { configureApp } from '../src/app.setup';

interface Step {
  name: string;
  method: string;
  path: string;
  expect: number;
  auth?: boolean;
  token?: string;
  body?: unknown;
  equals?: Record<string, unknown>;
  absent?: string[];
  save?: Record<string, string>;
}

const MISSING = Symbol('missing');
const scenario: { steps: Step[] } = JSON.parse(readFileSync(join(__dirname, 'api_scenario.json'), 'utf8'));

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
    for (const step of scenario.steps) {
      const path = step.path.replace(/\$\{(\w+)\}/g, (_match, name: string) => String(variables[name] ?? ''));
      const method = step.method.toLowerCase() as 'get' | 'post' | 'put' | 'patch' | 'delete';
      let call = request(app.getHttpServer())[method](path);
      if (step.auth) {
        call = call.set('Authorization', `Bearer ${String(variables.token ?? '')}`);
      }
      if (step.token) {
        call = call.set('Authorization', `Bearer ${step.token}`);
      }
      const response = step.body !== undefined ? await call.send(resolve(step.body, variables) as object) : await call;
      const label = `${step.name} (${step.method} ${path}): ${response.text.slice(0, 300)}`;

      expect({ step: label, status: response.status }).toEqual({ step: label, status: step.expect });
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
      for (const [name, jsonPath] of Object.entries(step.save ?? {})) {
        variables[name] = dig(response.body, jsonPath);
      }
    }
  });
});
