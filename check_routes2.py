import sys
sys.path.insert(0, '.')
from app.main import app
print('Total routes:', len(app.routes))
for route in app.routes:
    path = getattr(route, 'path', '') or ''
    methods = getattr(route, 'methods', None)
    endpoint = getattr(route, 'endpoint', None)
    fn_name = getattr(endpoint, '__name__', '?') if endpoint else '?'
    print(f'{path} {fn_name}')
