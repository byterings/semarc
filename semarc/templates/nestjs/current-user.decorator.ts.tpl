import { createParamDecorator, ExecutionContext } from '@nestjs/common';
import { AuthenticatedRequest } from '../guards/auth.guard';

/** The authenticated user id set by AuthGuard (undefined on public routes). */
export const CurrentUserId = createParamDecorator(
  (_data: unknown, context: ExecutionContext): number | undefined =>
    context.switchToHttp().getRequest<AuthenticatedRequest>().userId,
);

/** The authenticated user's role set by AuthGuard (undefined without USE auth.roles). */
export const CurrentUserRole = createParamDecorator(
  (_data: unknown, context: ExecutionContext): string | undefined =>
    context.switchToHttp().getRequest<AuthenticatedRequest>().userRole,
);
