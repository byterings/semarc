import { CanActivate, ExecutionContext, Injectable, Logger } from '@nestjs/common';
import { createHash } from 'crypto';
import { Request } from 'express';
import { BlockList, isIP } from 'net';
import { settings } from '../config/settings';
import { ApiError } from './api-error';

interface RedisLike {
  multi(): {
    set(key: string, value: string, ...options: (string | number)[]): unknown;
    incr(key: string): unknown;
    ttl(key: string): unknown;
    exec(): Promise<[Error | null, unknown][] | null>;
  };
}

const windows = new Map<string, { count: number; reset: number }>();
const logger = new Logger('RateLimit');
let redis: RedisLike | undefined;

function normalize(address: string): string {
  const mapped = /^::ffff:(\d+\.\d+\.\d+\.\d+)$/i.exec(address);
  return mapped ? mapped[1] : address;
}

function trustedProxies(): BlockList | undefined {
  const entries = (process.env.TRUSTED_PROXIES ?? '').split(',').map((entry) => entry.trim()).filter(Boolean);
  if (entries.length === 0) {
    return undefined;
  }
  const list = new BlockList();
  for (const entry of entries) {
    const [address, bits] = entry.split('/');
    const family = isIP(address) === 6 ? 'ipv6' : 'ipv4';
    if (isIP(address) === 0) {
      logger.warn(`Ignoring invalid TRUSTED_PROXIES entry: ${entry}`);
    } else if (bits === undefined) {
      list.addAddress(address, family);
    } else {
      list.addSubnet(address, Number(bits), family);
    }
  }
  return list;
}

function isTrusted(list: BlockList, address: string): boolean {
  const family = isIP(address);
  return family !== 0 && list.check(address, family === 6 ? 'ipv6' : 'ipv4');
}

/**
 * X-Forwarded-For is believed only when the direct peer is listed in TRUSTED_PROXIES; then
 * the client is the rightmost forwarded address that is not itself a trusted proxy.
 */
export function clientIp(request: Request): string {
  const peer = normalize(request.socket.remoteAddress ?? 'unknown');
  const forwarded = request.headers['x-forwarded-for'];
  const list = trustedProxies();
  if (!forwarded || !list || !isTrusted(list, peer)) {
    return peer;
  }
  const hops = String(forwarded).split(',').map((hop) => normalize(hop.trim())).filter(Boolean);
  for (let index = hops.length - 1; index >= 0; index -= 1) {
    if (index === 0 || !isTrusted(list, hops[index])) {
      return hops[index];
    }
  }
  return peer;
}

async function countInRedis(key: string): Promise<[number, number]> {
  if (!redis) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const loaded = require('ioredis') as { default?: unknown };
    const Redis = (loaded.default ?? loaded) as new (url: string, options: object) => RedisLike;
    redis = new Redis(process.env.REDIS_URL || 'redis://127.0.0.1:6379/0', {
      connectTimeout: 2000,
      maxRetriesPerRequest: 1,
    });
  }
  const name = `semarc:rate-limit:${createHash('sha1').update(key).digest('hex')}`;
  const transaction = redis.multi();
  transaction.set(name, '0', 'EX', settings.authRateWindow, 'NX');
  transaction.incr(name);
  transaction.ttl(name);
  const results = await transaction.exec();
  if (!results || results.some(([error]) => error)) {
    throw new Error('Redis transaction failed');
  }
  return [Number(results[1][1]), Number(results[2][1])];
}

function countLocally(key: string): [number, number] {
  const now = Date.now();
  let window = windows.get(key);
  if (!window || window.reset <= now) {
    window = { count: 0, reset: now + settings.authRateWindow * 1000 };
    windows.set(key, window);
  }
  window.count += 1;
  return [window.count, Math.ceil((window.reset - now) / 1000)];
}

/**
 * Fixed-window rate limiting for authentication endpoints. With RATE_LIMIT_STORE=redis the
 * counters live in Redis (shared by every process and server); otherwise, or when Redis
 * cannot be reached, in this process.
 */
@Injectable()
export class AuthRateLimitGuard implements CanActivate {
  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest<Request>();
    const key = `${request.path}|${clientIp(request)}`;
    let count: number;
    let retry: number;
    if (process.env.RATE_LIMIT_STORE === 'redis') {
      try {
        [count, retry] = await countInRedis(key);
      } catch (error) {
        logger.error(`Rate limiting falls back to local storage: ${String(error)}`);
        [count, retry] = countLocally(key);
      }
    } else {
      [count, retry] = countLocally(key);
    }

    if (count > settings.authRateLimit) {
      const seconds = Math.max(1, retry);
      throw new ApiError(429, 'too_many_requests', `Too many attempts. Try again in ${seconds} seconds.`, {}, {
        'Retry-After': String(seconds),
      });
    }
    return true;
  }
}
