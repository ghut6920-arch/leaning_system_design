"""Check public instruction links, exact manifest, and frozen/protected public files."""
from pathlib import Path
import hashlib
import json
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SUITE = ROOT/'personal-learning-suite'
LEARNING = ROOT/'learning/embodied-intelligence'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
active = sorted(set([* (SUITE/'src/agents').glob('*.md'),
                     * (SUITE/'src/skills').rglob('*.md')]))
expected = set(active+[SUITE/'contracts/shared-contracts.md'])
manifest = json.loads((LEARNING/'framework-manifest.json').read_text(encoding='utf-8-sig'))
seen = set()
manifest_errors = []
for entry in manifest['entries']:
    path = (LEARNING/entry['path']).resolve()
    if path in seen or not path.is_file() or sha(path) != entry['sha256']:
        manifest_errors.append(entry['path'])
    seen.add(path)
if seen != {p.resolve() for p in expected}:
    manifest_errors.append('manifest_scope_mismatch')
assert manifest['mode'] == 'manual_files'
assert all(manifest[k] is False for k in ('native_skill_installation','real_runtime_binding','independent_agents_started'))

docs = active+[LEARNING/p for p in ('MODEL_ENTRY.md','FRAMEWORK.md','START_PROMPT.md','README.md','AGENTS.md','INTERACTION.md')]
docs += [ROOT/'README.md', SUITE/'README.md', SUITE/'src/README.md']
docs += [ROOT/'docs/implementation'/n for n in (
    'AI个人学习系统_教学内容重构执行路线_v1.md',
    'AI个人学习系统_第三阶段入口与角色历史迁出_2026-10-05.md',
    'AI个人学习系统_教学内容重构_第三阶段实施与验证_2026-10-05.md')]
docs += [ROOT/'docs/audits/AI个人学习系统_第三阶段修订_研究与设计逐项复核_2026-10-05.md', OUT/'content-walkthrough.md']
broken = []
count = 0
for doc in docs:
    content = re.sub(r'```.*?```', '', doc.read_text(encoding='utf-8-sig'), flags=re.S)
    for match in re.finditer(r'\[[^\]]*\]\((<[^>]+>|[^)]+)\)', content):
        target = match.group(1).strip().strip('<>')
        if target.startswith(('http:', 'https:', 'codex:', 'plugin:', 'app:', 'mailto:', '#')):
            continue
        target = unquote(target.split('#',1)[0])
        target = re.sub(r':\d+$', '', target)
        path = Path(target)
        if not path.is_absolute():
            path = doc.parent/path
        count += 1
        if not path.exists():
            broken.append({'document': str(doc.relative_to(ROOT)), 'target': target})

before = json.loads((OUT/'before-phase3.json').read_text(encoding='utf-8'))
changed = [p for p,h in before['protected_public_files'].items() if not (ROOT/p).is_file() or sha(ROOT/p) != h]
registry = json.loads((SUITE/'resources/source-registry.json').read_text(encoding='utf-8-sig'))
source_errors = [s['source_id'] for s in registry['sources'] if sha((SUITE/s['project_relative_path']).resolve()) != s['sha256']]
result = {'status': 'pass' if not (broken or changed or source_errors or manifest_errors) else 'fail',
          'active_instruction_files': len(active), 'framework_entries': len(manifest['entries']),
          'documents_checked': len(docs), 'local_links_checked': count, 'broken_links': broken,
          'manifest_errors': manifest_errors, 'frozen_sources_checked': len(registry['sources']),
          'frozen_source_errors': source_errors, 'protected_public_files_checked': len(before['protected_public_files']),
          'protected_public_files_changed': changed,
          'personal_files_hashed_or_read_by_this_probe': False,
          'limits': ['Paths, public fingerprints and manifest integrity only.', 'No semantic teaching or learning efficacy guarantee.']}
(OUT/'integrity-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
raise SystemExit(0 if result['status']=='pass' else 1)
