import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
{{module_imports}}

@Module({
    imports: {{modules}},
    controllers: [AppController],
})
export class AppModule {}
