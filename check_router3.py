import sys
sys.path.insert(0, '.')
from app.main import app

# Check app.router.routes
print('app.router.routes:')
for route in app.router.routes:
    path = getattr(route, 'path', None)
    rtype = type(route).__name__
    fn = '?'
    if hasattr(route, 'endpoint'):
        fn = getattr(route.endpoint, '__name__', '?')
    if path and ('customer' in path or 'catalog' in path):
        print(f'  [{rtype}] {path} fn={fn}')
