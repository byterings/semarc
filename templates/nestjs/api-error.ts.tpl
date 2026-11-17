export type ErrorDetails = Record<string, string[]>;

/** An API error rendered as an `error` object with code, message and optional details. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: ErrorDetails = {},
  ) {
    super(message);
  }

  static unauthorized(message = 'Authentication required.'): ApiError {
    return new ApiError(401, 'unauthorized', message);
  }

  static notFound(message = 'Resource not found.'): ApiError {
    return new ApiError(404, 'not_found', message);
  }

  static conflict(message: string, details: ErrorDetails = {}): ApiError {
    return new ApiError(409, 'conflict', message, details);
  }

  static validation(details: ErrorDetails): ApiError {
    return new ApiError(422, 'validation_failed', 'The given data was invalid.', details);
  }

  static notImplemented(message: string): ApiError {
    return new ApiError(501, 'not_implemented', message);
  }
}
