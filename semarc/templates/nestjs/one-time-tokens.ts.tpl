import { createHash, randomBytes } from 'crypto';
import { DataSource, EntityTarget, IsNull, ObjectLiteral } from 'typeorm';
import { nowUtc } from '../../database/column-types';

const hash = (token: string): string => createHash('sha256').update(token).digest('hex');

/** Single-use, expiring tokens; only a SHA-256 hash of each token is stored. */
export class OneTimeTokens<T extends ObjectLiteral> {
  constructor(
    private readonly dataSource: DataSource,
    private readonly entity: EntityTarget<T>,
  ) {}

  async issue(userId: number, ttlSeconds: number): Promise<string> {
    const token = randomBytes(32).toString('hex');
    const now = nowUtc();
    await this.dataSource.getRepository(this.entity).insert({
      user_id: userId,
      token_hash: hash(token),
      expires_at: new Date(now.getTime() + ttlSeconds * 1000),
      used_at: null,
      created_at: now,
      updated_at: now,
    } as never);
    return token;
  }

  /** Marks a valid token as used and returns its user id, or undefined when invalid, used or expired. */
  async consume(token: string): Promise<number | undefined> {
    const repository = this.dataSource.getRepository(this.entity);
    const record = (await repository.findOne({ where: { token_hash: hash(token) } as never })) as
      | { id: number; user_id: number; used_at: Date | null; expires_at: Date }
      | null;
    if (!record || record.used_at !== null || record.expires_at.getTime() <= Date.now()) {
      return undefined;
    }
    const result = await repository.update({ id: record.id, used_at: IsNull() } as never, { used_at: nowUtc(), updated_at: nowUtc() } as never);
    return result.affected === 1 ? record.user_id : undefined;
  }
}
