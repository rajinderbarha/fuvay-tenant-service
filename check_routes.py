import sys
sys.path.insert(0, '.')
from app.main import app
for route in app.routes:
    path = getattr(route, 'path', '') or ''
    if 'customer' in path.lower():
        methods = getattr(route, 'methods', None)
        endpoint = getattr(route, 'endpoint', None)
        fn_name = getattr(endpoint, '__name__', '?') if endpoint else '?'
        print(f'{methods} {path} -> {fn_name}')
