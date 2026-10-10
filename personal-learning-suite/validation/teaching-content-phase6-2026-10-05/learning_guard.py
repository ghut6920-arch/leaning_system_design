"""Compare learning files in RAM; persist only aggregate results, never hashes."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PUBLIC = {'learning/embodied-intelligence/FRAMEWORK.md',
          'learning/embodied-intelligence/framework-manifest.json'}


def snapshot():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).digest()
            for p in (ROOT/'learning').rglob('*') if p.is_file()
            and str(p.relative_to(ROOT)).replace('\\', '/') not in PUBLIC}


before = snapshot()
print('Learning integrity guard ready; private digests remain in RAM.', flush=True)
input()
after = snapshot()
changed = sum(before.get(k) != after.get(k) for k in set(before) | set(after))
result = {'unchanged': changed == 0, 'guarded_files': len(before),
          'changed_count': changed, 'private_contents_paths_or_digests_saved': False,
          'excluded_public_protocols': ['FRAMEWORK.md', 'framework-manifest.json']}
(OUT/'learning-unchanged.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False), flush=True)
raise SystemExit(0 if changed == 0 else 1)
