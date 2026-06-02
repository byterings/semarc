import { Module } from '@nestjs/common';
import { {{controller_name}} } from './{{module_file}}.controller';
import { {{service_name}} } from './{{module_file}}.service';

@Module({
    controllers: [{{controller_name}}],
    providers: [{{service_name}}],
    exports: [{{service_name}}],
})
export class {{module_name}} {}
