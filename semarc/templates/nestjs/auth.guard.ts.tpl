import { CanActivate, ExecutionContext, Injectable, SetMetadata } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { Request } from 'express';
import { DataSource } from 'typeorm';
import { ApiError } from '../common/api-error';
import { {{auth_model}} } from '../modules/{{auth_folder}}/{{auth_file}}.entity';
import { TokenService } from '../modules/auth/token.service';

export interface AuthenticatedRequest extends Request {
  userId?: number;
  userRole?: string;
}

const ROLES_KEY = 'semarc:roles';

/** Restricts a route to callers with one of the given roles (used with AuthGuard). */
export const Roles = (...roles: string[]) => SetMetadata(ROLES_KEY, roles);

/**
 * Requires a valid bearer token for an existing user, enforces @Roles(...) when present
 * and stores the user id and role on the request.
 */
@Injectable()
export class AuthGuard implements CanActivate {
  constructor(
    private readonly tokens: TokenService,
    private readonly dataSource: DataSource,
    private readonly reflector: Reflector,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest<AuthenticatedRequest>();
    const match = /^Bearer\s+(\S+)$/i.exec(request.headers.authorization ?? '');
    if (!match) {
      throw ApiError.unauthorized('Missing bearer token.');
    }

    const userId = await this.tokens.userIdFrom(match[1]);
    const user = await this.dataSource.getRepository({{auth_model}}).findOne({ where: { id: userId } });
    if (!user) {
      throw ApiError.unauthorized('Token user no longer exists.');
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
