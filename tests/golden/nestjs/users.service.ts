import { Injectable } from '@nestjs/common';
import { User } from './user.model';

@Injectable()
export class UserService {
    findAll(): User[] {
        return [];
    }

    create(payload: Partial<User>): User {
        return payload as User;
    }
}
