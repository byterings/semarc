import { Column, Entity, Index, PrimaryGeneratedColumn } from 'typeorm';
import { columnType } from '../../database/column-types';

/** Opaque, rotating refresh tokens; only a SHA-256 hash of each token is stored. */
@Entity({ name: '{{table}}' })
export class RefreshToken {
  @PrimaryGeneratedColumn({ type: 'integer' })
  id!: number;

  @Column({ type: columnType('STRING'), length: 255, unique: true })
  token_hash!: string;

  @Column({ type: columnType('DATETIME') })
  expires_at!: Date;

  @Column({ type: columnType('DATETIME'), nullable: true })
  revoked_at!: Date | null;

  @Index()
  @Column({ type: columnType('INTEGER') })
  user_id!: number;

  @Column({ type: columnType('DATETIME') })
  created_at!: Date;

  @Column({ type: columnType('DATETIME') })
  updated_at!: Date;
}
