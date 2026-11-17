import { INestApplication } from '@nestjs/common';
import { ApiExceptionFilter } from './common/api-exception.filter';
import { validationPipe } from './common/validation';

/** Global configuration shared by the server and the test runner. */
export function configureApp(app: INestApplication): void {
  app.useGlobalFilters(new ApiExceptionFilter());
  app.useGlobalPipes(validationPipe());
}
