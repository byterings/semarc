process.env.DB_CONNECTION = 'sqlite';
process.env.DB_DATABASE = ':memory:';
process.env.BOOTSTRAP_ADMIN_EMAIL = 'admin@example.com';
process.env.MAIL_DRIVER = 'memory';
process.env.JWT_SECRET = process.env.JWT_SECRET || 'semarc-test-secret-semarc-test-secret';
