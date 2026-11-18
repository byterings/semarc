import { Injectable } from '@nestjs/common';
import { createHash, randomBytes } from 'crypto';
import { DataSource, IsNull } from 'typeorm';
import { ApiError } from '../../common/api-error';
import { settings } from '../../config/settings';
import { nowUtc } from '../../database/column-types';
import { RefreshToken } from './refresh-token.entity';

const hash = (token: string): string => createHash('sha256').update(token).digest('hex');

@Injectable()
export class RefreshTokenStore {
  constructor(private readonly dataSource: DataSource) {}

  async issue(userId: number): Promise<{ refresh_token: string; refresh_expires_in: number }> {
    const token = randomBytes(32).toString('hex');
    const now = nowUtc();
    await this.dataSource.getRepository(RefreshToken).insert({
      user_id: userId,
      token_hash: hash(token),
      expires_at: new Date(now.getTime() + settings.jwtRefreshTtl * 1000),
      revoked_at: null,
      created_at: now,
      updated_at: now,
    });
    return { refresh_token: token, refresh_expires_in: settings.jwtRefreshTtl };
  }

  /** Revokes a valid token and returns its user id; invalid, expired or reused tokens get 401. */
  async rotate(token: string): Promise<number> {
    const repository = this.dataSource.getRepository(RefreshToken);
    const record = await repository.findOne({ where: { token_hash: hash(token) } });
    if (!record || record.revoked_at !== null || record.expires_at.getTime() <= Date.now()) {
      throw ApiError.unauthorized('Invalid or expired refresh token.');
    }
    await repository.update({ id: record.id }, { revoked_at: nowUtc(), updated_at: nowUtc() });
    return record.user_id;
  }

  async revoke(token: string): Promise<void> {
    await this.dataSource
      .getRepository(RefreshToken)
      .update({ token_hash: hash(token), revoked_at: IsNull() }, { revoked_at: nowUtc(), updated_at: nowUtc() });
  }

  async revokeAll(userId: number): Promise<void> {
    await this.dataSource
      .getRepository(RefreshToken)
      .update({ user_id: userId, revoked_at: IsNull() }, { revoked_at: nowUtc(), updated_at: nowUtc() });
  }
}
