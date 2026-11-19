import { timingSafeEqual } from 'crypto';
import { CanActivate, ExecutionContext, Injectable, SetMetadata } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Request } from 'express';
import { DataSource } from 'typeorm';
import { ApiError } from '../common/api-error';
import { {{auth_model}} } from '../modules/{{auth_folder}}/{{auth_file}}.entity';
import { CSRF_HEADER, SESSION_COOKIE, SessionStore, hashToken, readCookie } from '../modules/auth/session.store';

export interface AuthenticatedRequest extends Request {
  userId?: number;
  userRole?: string;
}

const ROLES_KEY = 'semarc:roles';
const SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS'];

/** Restricts a route to callers with one of the given roles (used with AuthGuard). */
export const Roles = (...roles: string[]) => SetMetadata(ROLES_KEY, roles);

/**
 * Requires an active session cookie for an existing user (and the CSRF header on unsafe
 * methods), enforces @Roles(...) when present and stores the user id and role on the request.
 */
@Injectable()
export class AuthGuard implements CanActivate {
  constructor(
    private readonly sessions: SessionStore,
    private readonly dataSource: DataSource,
    private readonly reflector: Reflector,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest<AuthenticatedRequest>();
    const session = await this.sessions.find(readCookie(request, SESSION_COOKIE));
    if (!session) {
      throw ApiError.unauthorized('Missing, ended or expired session.');
    }
    if (!SAFE_METHODS.includes(request.method)) {
      const given = Buffer.from(hashToken(String(request.headers[CSRF_HEADER] ?? '')));
      const expected = Buffer.from(session.csrf_hash);
      if (!request.headers[CSRF_HEADER] || given.length !== expected.length || !timingSafeEqual(given, expected)) {
        throw ApiError.forbidden('Missing or invalid CSRF token.');
      }
    }

    const userId = session.user_id;
    const user = await this.dataSource.getRepository({{auth_model}}).findOne({ where: { id: userId } });
    if (!user) {
      throw ApiError.unauthorized('Session user no longer exists.');
    }

    request.userId = userId;
    request.userRole = (user as { role?: string }).role;
    const roles = this.reflector.getAllAndOverride<string[] | undefined>(ROLES_KEY, [context.getHandler(), context.getClass()]);
    if (roles && roles.length > 0 && !roles.includes(request.userRole ?? '')) {
      throw ApiError.forbidden(`This action requires the role: ${roles.join(' or ')}.`);
    }
    return true;
  }
}
