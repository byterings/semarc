import { CanActivate, ExecutionContext, Injectable } from '@nestjs/common';
import { Request } from 'express';
import { settings } from '../config/settings';
import { ApiError } from './api-error';

const windows = new Map<string, { count: number; reset: number }>();

/** Fixed-window, in-process rate limiting for POST /register and POST /login. */
@Injectable()
export class AuthRateLimitGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<Request>();
    const key = `${request.path}|${request.ip ?? 'unknown'}`;
    const now = Date.now();
    let window = windows.get(key);
    if (!window || window.reset <= now) {
      window = { count: 0, reset: now + settings.authRateWindow * 1000 };
      windows.set(key, window);
    }
    window.count += 1;

    if (window.count > settings.authRateLimit) {
      const retry = Math.max(1, Math.ceil((window.reset - now) / 1000));
      throw new ApiError(429, 'too_many_requests', `Too many attempts. Try again in ${retry} seconds.`, {}, {
        'Retry-After': String(retry),
      });
    }
    return true;
  }
}
