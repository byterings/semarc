import { Injectable } from '@nestjs/common';

@Injectable()
export class AuthService {
    login(): { token: string } {
        return { token: 'demo-token' };
    }
}
