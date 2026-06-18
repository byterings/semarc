import { {{model_name}} } from './{{model_file}}.model';

export class {{repository_name}} {
    findAll(): {{model_name}}[] {
        // TODO: connect this repository to the selected persistence adapter.
        return [];
    }

    create(payload: Partial<{{model_name}}>): {{model_name}} {
        throw new Error('TODO: connect this repository to the selected persistence adapter.');
    }
}
