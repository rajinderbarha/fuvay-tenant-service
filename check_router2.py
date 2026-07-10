import sys
sys.path.insert(0, '.')
from app.engines.customer_flow.router import router

print('Router prefix:', router.prefix)
print('Routes:')
for route in router.routes:
    path = getattr(route, 'path', '') or ''
    fn_name = getattr(getattr(route, 'endpoint', None), '__name__', '?')
    print(f'  path={path!r}  fn={fn_name}')
