import { Injectable } from '@nestjs/common';
import { PasswordHasher } from '../../common/password-hasher';
import { ResourceService } from '../../common/resource.service';
import { User } from './user.entity';
import { UserRepository } from './users.repository';

@Injectable()
export class UserService extends ResourceService<User> {
  protected readonly name = 'User';
  protected readonly output = ['id', 'email', 'name', 'created_at', 'updated_at'];
  protected readonly unique = ['email'];

  constructor(
    repository: UserRepository,
    private readonly hasher: PasswordHasher,
  ) {
    super(repository);
  }

  protected async beforeWrite(data: Record<string, unknown>): Promise<Record<string, unknown>> {
    if (typeof data.password === 'string') {
      data.password = await this.hasher.hash(data.password);
    }
    return data;
  }
}
