import { Column, Entity, Index, PrimaryGeneratedColumn } from 'typeorm';
import { columnType } from '../../database/column-types';

/** Server-side sessions; only SHA-256 hashes of the session and CSRF tokens are stored. */
@Entity({ name: '{{table}}' })
export class UserSession {
  @PrimaryGeneratedColumn({ type: 'integer' })
  id!: number;

  @Column({ type: columnType('STRING'), length: 255, unique: true })
  token_hash!: string;

  @Column({ type: columnType('STRING'), length: 255 })
  csrf_hash!: string;

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
