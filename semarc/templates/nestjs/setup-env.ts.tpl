import { readFileSync } from 'fs';
import { join } from 'path';

process.env.DB_CONNECTION = 'sqlite';
process.env.DB_DATABASE = ':memory:';
process.env.BOOTSTRAP_ADMIN_EMAIL = 'admin@example.com';
process.env.MAIL_DRIVER = 'memory';
process.env.JWT_SECRET = process.env.JWT_SECRET || 'semarc-test-secret-semarc-test-secret';

const scenario = JSON.parse(readFileSync(join(__dirname, 'api_scenario.json'), 'utf8')) as { env?: Record<string, string> };
Object.assign(process.env, scenario.env ?? {});
