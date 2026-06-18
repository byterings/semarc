from fastapi import APIRouter

from services.{{service_module}} import {{service_name}}

router = APIRouter(prefix="{{router_prefix}}")
{{service_variable}} = {{service_name}}()


{{methods}}
