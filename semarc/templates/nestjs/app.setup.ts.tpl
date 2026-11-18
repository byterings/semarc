import { INestApplication } from '@nestjs/common';
import { ApiExceptionFilter } from './common/api-exception.filter';
import { validationPipe } from './common/validation';
import { settings } from './config/settings';

/** Global configuration shared by the server and the test runner. */
export function configureApp(app: INestApplication): void {
  app.enableCors({
    origin: settings.corsOrigins.includes('*') ? '*' : settings.corsOrigins,
    methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Authorization', 'Content-Type'],
    maxAge: 600,
  });
  app.useGlobalFilters(new ApiExceptionFilter());
  app.useGlobalPipes(validationPipe());
}
