import { {{decorator_imports}} } from '@nestjs/common';
import { {{service_name}} } from './{{service_file}}.service';

@Controller('{{route_prefix}}')
export class {{controller_name}} {
    constructor(private readonly {{service_property}}: {{service_name}}) {}

{{methods}}
}
