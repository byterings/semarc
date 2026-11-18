process.env.DB_CONNECTION = 'sqlite';
process.env.DB_DATABASE = ':memory:';
process.env.JWT_SECRET = process.env.JWT_SECRET || 'semarc-test-secret-semarc-test-secret';
