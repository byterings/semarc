import { Logger } from '@nestjs/common';
import * as nodemailer from 'nodemailer';
import { settings } from '../config/settings';

export interface MailMessage {
  to: string;
  subject: string;
  body: string;
}

/**
 * Plain-text email. MAIL_DRIVER selects smtp, log or memory (kept in Mailer.outbox for
 * tests). Delivery failures are logged, not thrown, so a mail outage never breaks
 * registration or password reset requests.
 */
export class Mailer {
  static readonly outbox: MailMessage[] = [];
  private static readonly logger = new Logger('Mailer');

  static async send(to: string, subject: string, body: string): Promise<void> {
    try {
      if (settings.mailDriver === 'memory') {
        Mailer.outbox.push({ to, subject, body });
      } else if (settings.mailDriver === 'smtp') {
        await nodemailer
          .createTransport({
            host: settings.mailHost,
            port: settings.mailPort,
            secure: settings.mailEncryption === 'ssl',
            requireTLS: settings.mailEncryption === 'tls',
            auth: settings.mailUsername ? { user: settings.mailUsername, pass: settings.mailPassword } : undefined,
          })
          .sendMail({ from: settings.mailFrom, to, subject, text: body });
      } else {
        Mailer.logger.log(`[mail] To: ${to}\nSubject: ${subject}\n\n${body}`);
      }
    } catch (error) {
      Mailer.logger.error(`Mail delivery failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  static body(intro: string, token: string, page: string, footer: string): string {
    const lines = [intro, '', `Token: ${token}`];
    if (settings.appUrl) {
      lines.push(`Link: ${settings.appUrl.replace(/\/$/, '')}/${page}?token=${token}`);
    }
    return [...lines, '', footer].join('\n') + '\n';
  }
}
