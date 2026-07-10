import sys
sys.path.insert(0, '.')
from app.main import app

print('ROUTES (non-None paths):')
for route in app.routes:
    path = getattr(route, 'path', None)
    if path:
        fn = getattr(getattr(route, 'endpoint', None), '__name__', '?')
        module = getattr(getattr(route, 'endpoint', None), '__module__', '?')
        if 'customer' in path or 'customer' in module:
            print(f'  {path} -> {module}.{fn}')
