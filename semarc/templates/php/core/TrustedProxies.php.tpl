<?php

declare(strict_types=1);

/**
 * Client address behind reverse proxies. X-Forwarded-For is believed only when the direct
 * peer is listed in TRUSTED_PROXIES (addresses or CIDR ranges, comma separated); then the
 * client is the rightmost forwarded address that is not itself a trusted proxy.
 */
final class TrustedProxies
{
    public static function clientIp(string $peer, ?string $forwarded): string
    {
        $peer = self::normalize($peer);
        $ranges = array_values(array_filter(array_map('trim', explode(',', (string) Env::get('TRUSTED_PROXIES', '')))));
        if ($forwarded === null || $ranges === [] || !self::trusted($peer, $ranges)) {
            return $peer;
        }

        $hops = array_values(array_filter(array_map('trim', explode(',', $forwarded))));
        for ($index = count($hops) - 1; $index >= 0; $index--) {
            $hop = self::normalize($hops[$index]);
            if ($index === 0 || !self::trusted($hop, $ranges)) {
                return $hop;
            }
        }

        return $peer;
    }

    private static function normalize(string $address): string
    {
        return preg_match('/^::ffff:(\d+\.\d+\.\d+\.\d+)$/i', $address, $matches) === 1 ? $matches[1] : $address;
    }

    /**
     * @param list<string> $ranges
     */
    private static function trusted(string $address, array $ranges): bool
    {
        $binary = @inet_pton($address);
        if ($binary === false) {
            return false;
        }
        foreach ($ranges as $range) {
            [$subnet, $bits] = str_contains($range, '/') ? explode('/', $range, 2) : [$range, null];
            $network = @inet_pton($subnet);
            if ($network === false || strlen($network) !== strlen($binary)) {
                continue;
            }
            $bits = $bits === null ? strlen($binary) * 8 : max(0, min((int) $bits, strlen($binary) * 8));
            $bytes = intdiv($bits, 8);
            $remainder = $bits % 8;
            if (substr($binary, 0, $bytes) !== substr($network, 0, $bytes)) {
                continue;
            }
            if ($remainder === 0) {
                return true;
            }
            $mask = (0xFF << (8 - $remainder)) & 0xFF;
            if ((ord($binary[$bytes]) & $mask) === (ord($network[$bytes]) & $mask)) {
                return true;
            }
        }

        return false;
    }
}
