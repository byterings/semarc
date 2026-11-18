<?php

declare(strict_types=1);

/**
 * Sends plain-text email. MAIL_DRIVER selects smtp, log (write to the error log) or
 * memory (kept in Mailer::$outbox for tests). Sending failures are logged, not thrown,
 * so a mail outage never breaks registration or password reset requests.
 */
final class Mailer
{
    /** @var list<array{to: string, subject: string, body: string}> */
    public static array $outbox = [];

    public function send(string $to, string $subject, string $body): void
    {
        $driver = Env::get('MAIL_DRIVER', 'log');
        try {
            match ($driver) {
                'memory' => self::$outbox[] = ['to' => $to, 'subject' => $subject, 'body' => $body],
                'smtp' => $this->smtp($to, $subject, $body),
                default => error_log("[mail] To: {$to}\nSubject: {$subject}\n\n{$body}"),
            };
        } catch (Throwable $exception) {
            error_log('Mail delivery failed: ' . $exception->getMessage());
        }
    }

    private function smtp(string $to, string $subject, string $body): void
    {
        $encryption = (string) Env::get('MAIL_ENCRYPTION', 'none');
        $scheme = $encryption === 'ssl' ? 'ssl://' : 'tcp://';
        $address = $scheme . Env::get('MAIL_HOST', '127.0.0.1') . ':' . Env::get('MAIL_PORT', '1025');
        $socket = stream_socket_client($address, $errorCode, $errorMessage, 10);
        if ($socket === false) {
            throw new RuntimeException("SMTP connection failed: {$errorMessage}");
        }
        stream_set_timeout($socket, 10);

        try {
            $hostname = gethostname() ?: 'localhost';
            $this->expect($socket, 220);
            $this->command($socket, "EHLO {$hostname}", 250);
            if ($encryption === 'tls') {
                $this->command($socket, 'STARTTLS', 220);
                stream_socket_enable_crypto($socket, true, STREAM_CRYPTO_METHOD_TLS_CLIENT);
                $this->command($socket, "EHLO {$hostname}", 250);
            }
            $username = Env::get('MAIL_USERNAME');
            if ($username !== null) {
                $this->command($socket, 'AUTH LOGIN', 334);
                $this->command($socket, base64_encode($username), 334);
                $this->command($socket, base64_encode((string) Env::get('MAIL_PASSWORD', '')), 235);
            }
            $from = (string) Env::get('MAIL_FROM', 'no-reply@localhost');
            $this->command($socket, "MAIL FROM:<{$from}>", 250);
            $this->command($socket, "RCPT TO:<{$to}>", 250);
            $this->command($socket, 'DATA', 354);

            $headers = [
                "From: {$from}",
                "To: {$to}",
                'Subject: ' . $subject,
                'Date: ' . gmdate('D, d M Y H:i:s') . ' +0000',
                'MIME-Version: 1.0',
                'Content-Type: text/plain; charset=UTF-8',
                'Content-Transfer-Encoding: 8bit',
            ];
            $text = preg_replace('/^\./m', '..', str_replace(["\r\n", "\n"], "\r\n", $body));
            $this->command($socket, implode("\r\n", $headers) . "\r\n\r\n" . $text . "\r\n.", 250);
            $this->command($socket, 'QUIT', 221);
        } finally {
            fclose($socket);
        }
    }

    /**
     * @param resource $socket
     */
    private function command($socket, string $line, int $expected): void
    {
        fwrite($socket, $line . "\r\n");
        $this->expect($socket, $expected);
    }

    /**
     * @param resource $socket
     */
    private function expect($socket, int $expected): void
    {
        do {
            $line = fgets($socket, 515);
            if ($line === false) {
                throw new RuntimeException('SMTP server closed the connection.');
            }
        } while (isset($line[3]) && $line[3] === '-');

        if ((int) substr($line, 0, 3) !== $expected) {
            throw new RuntimeException('Unexpected SMTP response: ' . trim($line));
        }
    }
}
