import { Injectable } from '@nestjs/common';

@Injectable()
export class AuthService {
    login(): never {
        throw new Error('TODO: configure a real authentication provider.');
    }
}
