import { Module } from '@nestjs/common';
{{module_imports}}

@Module({
    imports: {{modules}},
})
export class AppModule {}
