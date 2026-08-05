"""Final Phase audit: find every router-defining module under app/engines
that is NOT referenced anywhere in app/main.py's _mount_routers.
"""
import os
import re

ROUTER_DECL = re.compile(
    r"^(router|customer_router|tenant_router|admin_router|provider_router|staff_router|public_router)\s*=\s*APIRouter\(",
    re.MULTILINE,
)

files = []
for root, dirs, fnames in os.walk("app/engines"):
    if "__pycache__" in root:
        continue
    for fn in fnames:
        if fn.endswith(".py"):
            fp = os.path.join(root, fn).replace("\\", "/")
            with open(fp, encoding="utf-8") as f:
                content = f.read()
            if ROUTER_DECL.search(content):
                files.append(fp)

with open("app/main.py", encoding="utf-8") as f:
    main_content = f.read()

missing = []
for fp in files:
    mod = fp.replace("/", ".")
    if mod.endswith(".py"):
        mod = mod[:-3]
    if mod not in main_content:
        missing.append(fp)

print(len(missing), "potentially unmounted router files (out of", len(files), ")")
for m in sorted(missing):
    print(" ", m)
