import { ValidationError, ValidationPipe } from '@nestjs/common';
import { ValidationArguments, registerDecorator } from 'class-validator';
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

const DECIMAL_PATTERN = /^-?\d{1,10}(\.\d{1,2})?$/;

/** A DECIMAL as "123.40", or undefined when the value is not a decimal with up to 2 decimals. */
export function decimalValue(value: unknown): string | undefined {
  if (typeof value === 'number') {
    if (!Number.isFinite(value) || Math.round(value * 100) / 100 !== value) {
      return undefined;
    }
    value = value.toFixed(2);
  }
  if (typeof value !== 'string' || !DECIMAL_PATTERN.test(value)) {
    return undefined;
  }
  const [whole, fraction = ''] = value.split('.');
  return `${whole}.${fraction.padEnd(2, '0')}`;
}

/** A JSON number or numeric string with up to 10 digits before and 2 after the point, within min/max. */
export function IsDecimalValue(min: number | null, max: number | null) {
  return (target: object, property: string) =>
    registerDecorator({
      name: 'isDecimalValue',
      target: target.constructor,
      propertyName: property,
      validator: {
        validate: (value: unknown) => {
          const decimal = decimalValue(value);
          return decimal !== undefined && (min === null || Number(decimal) >= min) && (max === null || Number(decimal) <= max);
        },
        defaultMessage: (args?: ValidationArguments) => {
          const range = [min !== null ? `at least ${min}` : '', max !== null ? `at most ${max}` : ''].filter(Boolean).join(' and ');
          return `${args?.property ?? property} must be a decimal with at most 10 digits before and 2 after the point${range ? `, ${range}` : ''}`;
        },
      },
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
