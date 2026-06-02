import { Injectable } from '@nestjs/common';
import { {{model_name}} } from './{{model_file}}.model';

@Injectable()
export class {{service_name}} {
    findAll(): {{model_name}}[] {
        return [];
    }

    create(payload: Partial<{{model_name}}>): {{model_name}} {
        return payload as {{model_name}};
    }
}
