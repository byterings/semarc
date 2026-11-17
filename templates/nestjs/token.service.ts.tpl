import { Injectable } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { ApiError } from '../../common/api-error';
import { settings } from '../../config/settings';

const MIN_SECRET_LENGTH = 32;

export interface TokenResult {
  access_token: string;
  token_type: string;
  expires_in: number;
}

/** Issues and verifies HS256 JSON Web Tokens. */
@Injectable()
export class TokenService {
  constructor(private readonly jwt: JwtService) {}

  async issue(userId: number): Promise<TokenResult> {
    const token = await this.jwt.signAsync(
      { sub: String(userId) },
      { secret: this.secret(), algorithm: 'HS256', expiresIn: settings.jwtTtl },
    );
    return { access_token: token, token_type: 'Bearer', expires_in: settings.jwtTtl };
  }

  async userIdFrom(token: string): Promise<number> {
    let claims: { sub?: unknown };
    try {
      claims = await this.jwt.verifyAsync(token, { secret: this.secret(), algorithms: ['HS256'] });
    } catch (error) {
      const expired = error instanceof Error && error.name === 'TokenExpiredError';
      throw ApiError.unauthorized(expired ? 'Token has expired.' : 'Invalid token.');
    }
    if (typeof claims.sub !== 'string' || !/^[1-9]\d*$/.test(claims.sub)) {
      throw ApiError.unauthorized('Invalid token subject.');
    }
    return Number(claims.sub);
  }

  private secret(): string {
    if (settings.jwtSecret.length < MIN_SECRET_LENGTH) {
      throw new Error(`JWT_SECRET must be set to at least ${MIN_SECRET_LENGTH} characters.`);
    }
    return settings.jwtSecret;
  }
}
