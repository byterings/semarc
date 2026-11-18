import { CanActivate, ExecutionContext, Injectable } from '@nestjs/common';
import { Request } from 'express';
import { DataSource } from 'typeorm';
import { ApiError } from '../common/api-error';
import { {{auth_model}} } from '../modules/{{auth_folder}}/{{auth_file}}.entity';
import { TokenService } from '../modules/auth/token.service';

export interface AuthenticatedRequest extends Request {
  userId?: number;
}

/** Requires a valid bearer token for an existing user and stores the user id on the request. */
@Injectable()
export class AuthGuard implements CanActivate {
  constructor(
    private readonly tokens: TokenService,
    private readonly dataSource: DataSource,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest<AuthenticatedRequest>();
    const match = /^Bearer\s+(\S+)$/i.exec(request.headers.authorization ?? '');
    if (!match) {
      throw ApiError.unauthorized('Missing bearer token.');
    }

    const userId = await this.tokens.userIdFrom(match[1]);
    const exists = await this.dataSource.getRepository({{auth_model}}).exists({ where: { id: userId } });
    if (!exists) {
      throw ApiError.unauthorized('Token user no longer exists.');
    }

    request.userId = userId;
    return true;
  }
}
