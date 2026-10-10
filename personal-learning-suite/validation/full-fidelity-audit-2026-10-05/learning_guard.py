"""Keep private digests in RAM; persist only aggregate change counts."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PUBLIC = {'learning/embodied-intelligence/FRAMEWORK.md', 'learning/embodied-intelligence/framework-manifest.json'}
def snapshot():
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).digest()
            for p in (ROOT/'learning').rglob('*') if p.is_file()
            and p.relative_to(ROOT).as_posix() not in PUBLIC}
before = snapshot()
print('Private-file guard ready; digests remain in RAM.', flush=True)
input()
after = snapshot()
changed = sum(before.get(k) != after.get(k) for k in set(before)|set(after))
result = {'unchanged': changed == 0, 'guarded_files': len(before), 'changed_count': changed,
          'guard_scope': 'final_verification_segment_only',
          'original_guard_result_available_after_turn_continuation': False,
          'whole_audit_unchanged_verified': False,
          'agent_writes_to_personal_learning_files': False,
          'private_contents_paths_or_digests_saved': False,
          'excluded_public_protocols': ['FRAMEWORK.md', 'framework-manifest.json']}
(OUT/'learning-unchanged.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False), flush=True)
raise SystemExit(0 if changed == 0 else 1)
