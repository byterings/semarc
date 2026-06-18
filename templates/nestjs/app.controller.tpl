import { Controller, Get } from '@nestjs/common';

@Controller()
export class AppController {
    @Get()
    home() {
        return {
            title: 'SEMARC Generated Project',
            project: '{{project_name}}',
            target: 'NestJS',
            semarc_version: '{{semarc_version}}',
            models: {{models}},
            routes: {{routes}},
            profiles: {{profiles}},
            modules: {{modules}},
            status: 'Running',
        };
    }

    @Get('health')
    health() {
        return {
            status: 'ok',
            project: '{{project_name}}',
        };
    }

    @Get('routes')
    routes() {
        return {
            routes: {{routes}},
        };
    }
}
