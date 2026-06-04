import { Injectable } from '@nestjs/common';
import { {{model_name}} } from './{{model_file}}.model';
import { {{repository_name}} } from './{{repository_file}}.repository';

@Injectable()
export class {{service_name}} {
    private readonly repository = new {{repository_name}}();

    findAll(): {{model_name}}[] {
        return this.repository.findAll();
    }

    create(payload: Partial<{{model_name}}>): {{model_name}} {
        return this.repository.create(payload);
    }
}
