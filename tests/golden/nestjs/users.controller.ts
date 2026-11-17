import { Controller, Get, Query, UseGuards } from '@nestjs/common';
import { pageParams } from '../../common/resource.service';
import { AuthGuard } from '../../guards/auth.guard';
import { UserService } from './users.service';

@Controller()
export class UserController {
  constructor(private readonly userService: UserService) {}

  @Get('users')
  @UseGuards(AuthGuard)
  list(@Query('limit') limit?: string, @Query('offset') offset?: string) {
    return this.userService.list(...pageParams(limit, offset));
  }
}
