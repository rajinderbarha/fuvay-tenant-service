import sys
sys.path.insert(0, '.')
from app.engines.customer_flow.router import router

print('Router prefix:', repr(router.prefix))
r0 = router.routes[0]
print('Route type:', type(r0).__name__)
print('Route path:', repr(r0.path))
print('Route path_regex:', repr(getattr(r0, 'path_regex', None)))
print('Route path_format:', repr(getattr(r0, 'path_format', None)))
print('Route name:', repr(getattr(r0, 'name', None)))
print('Fn name:', r0.endpoint.__name__)
