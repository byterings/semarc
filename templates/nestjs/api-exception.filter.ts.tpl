import { ArgumentsHost, Catch, ExceptionFilter, HttpException, Logger } from '@nestjs/common';
import { Response } from 'express';
import { QueryFailedError } from 'typeorm';
import { ApiError, ErrorDetails } from './api-error';

const HTTP_ERROR_CODES: Record<number, string> = {
  400: 'bad_request',
  401: 'unauthorized',
  403: 'forbidden',
  404: 'not_found',
  405: 'method_not_allowed',
};
const UNIQUE_VIOLATIONS = ['ER_DUP_ENTRY', '23505', 'SQLITE_CONSTRAINT_UNIQUE'];

@Catch()
export class ApiExceptionFilter implements ExceptionFilter {
  private readonly logger = new Logger(ApiExceptionFilter.name);

  catch(exception: unknown, host: ArgumentsHost): void {
    const response = host.switchToHttp().getResponse<Response>();

    if (exception instanceof ApiError) {
      this.send(response, exception.status, exception.code, exception.message, exception.details);
      return;
    }
    if (exception instanceof HttpException) {
      const status = exception.getStatus();
      const message =
        status === 404 ? 'Route not found.' : status === 400 ? 'Request body must be valid JSON.' : exception.message;
      this.send(response, status, HTTP_ERROR_CODES[status] ?? 'http_error', message);
      return;
    }
    if (exception instanceof QueryFailedError && UNIQUE_VIOLATIONS.includes(String((exception.driverError as { code?: string })?.code))) {
      this.send(response, 409, 'conflict', 'A record with the same unique value already exists.');
      return;
    }

    this.logger.error(exception instanceof Error ? exception.stack : String(exception));
    this.send(response, 500, 'internal_error', 'Internal server error.');
  }

  private send(response: Response, status: number, code: string, message: string, details: ErrorDetails = {}): void {
    const error: Record<string, unknown> = { code, message };
    if (Object.keys(details).length > 0) {
      error.details = details;
    }
    response.status(status).json({ error });
  }
}
