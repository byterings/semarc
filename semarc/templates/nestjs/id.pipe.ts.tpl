import { Injectable, PipeTransform } from '@nestjs/common';
import { ApiError } from './api-error';

/** Parses positive integer route ids; anything else is a missing record (404). */
@Injectable()
export class IdPipe implements PipeTransform<string, number> {
  transform(value: string): number {
    if (!/^[1-9]\d{0,14}$/.test(value)) {
      throw ApiError.notFound(`Record ${value} not found.`);
    }
    return Number(value);
  }
}
