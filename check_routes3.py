import sys
sys.path.insert(0, '.')
from app.main import app
for route in app.routes:
    path = getattr(route, 'path', '') or ''
    methods = getattr(route, 'methods', None)
    fn_name = getattr(getattr(route, 'endpoint', None), '__name__', '?')
    if 'customer' in path or 'catalog' in path:
        print(f'PATH: {path} METHODS: {methods} FN: {fn_name}')
