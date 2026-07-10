import sys
sys.path.insert(0, '.')
from app.main import app

print('ALL app.routes:')
for route in app.routes:
    path = getattr(route, 'path', None)
    rtype = type(route).__name__
    fn = '?'
    if hasattr(route, 'endpoint'):
        fn = getattr(route.endpoint, '__name__', '?')
    print(f'  [{rtype}] {path} fn={fn}')
