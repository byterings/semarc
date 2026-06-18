import { Injectable } from '@nestjs/common';
import { User } from './user.model';
import { UserRepository } from './users.repository';

@Injectable()
export class UserService {
    private readonly repository = new UserRepository();

    findAll(): User[] {
        return this.repository.findAll();
    }

    create(payload: Partial<User>): User {
        return this.repository.create(payload);
    }
}
