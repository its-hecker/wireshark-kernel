import hashlib
import shutil
from pathlib import Path
import sys

root, output = map(Path, sys.argv[1:3])
references = Path(sys.argv[3]) if len(sys.argv) > 3 else None
if references:
    references.mkdir(parents=True, exist_ok=True)
modules = {}
for path in sorted(root.rglob('*.ko')):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if path.name in modules and modules[path.name] != digest:
        raise SystemExit(f'Conflicting module basename: {path.name}')
    modules[path.name] = digest
    if references:
        shutil.copyfile(path, references / path.name)
if 'wlan.ko' not in modules:
    raise SystemExit('No built wlan.ko: refusing kernel-only packaging')
output.write_text(''.join(f'{digest} {name}\n' for name, digest in sorted(modules.items())))

