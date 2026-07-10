import sys
sys.path.insert(0, '.')
from app.engines.customer_flow.router import router

for route in router.routes:
    path = getattr(route, 'path', '') or ''
    methods = getattr(route, 'methods', None)
    fn_name = getattr(getattr(route, 'endpoint', None), '__name__', '?')
    print(f'{methods} {router.prefix}{path} -> {fn_name}')
