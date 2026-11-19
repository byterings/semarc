import { Injectable } from '@nestjs/common';
import * as bcrypt from 'bcryptjs';

const ROUNDS = 10;

@Injectable()
export class PasswordHasher {
  hash(plain: string): Promise<string> {
    return bcrypt.hash(plain, ROUNDS);
  }

  verify(plain: string, hash: string): Promise<boolean> {
    return bcrypt.compare(plain, hash);
  }
}
