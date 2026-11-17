import { ValidationError, ValidationPipe } from '@nestjs/common';
import { ApiError, ErrorDetails } from './api-error';

/** Strict request validation: no type coercion, unknown fields stripped, 422 with field details. */
export function validationPipe(): ValidationPipe {
  return new ValidationPipe({
    whitelist: true,
    transform: true,
    transformOptions: { enableImplicitConversion: false },
    exceptionFactory: (errors: ValidationError[]) => ApiError.validation(collect(errors)),
  });
}

function collect(errors: ValidationError[], prefix = ''): ErrorDetails {
  const details: ErrorDetails = {};
  for (const error of errors) {
    const field = prefix + error.property;
    if (error.constraints) {
      details[field] = Object.values(error.constraints);
    }
    Object.assign(details, collect(error.children ?? [], `${field}.`));
  }
  return details;
}
