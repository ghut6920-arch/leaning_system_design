"""Check public source/layout integrity and preserve exact audit diffs.

Link and fingerprint checks establish no pedagogical or scientific validity.
"""
from pathlib import Path
from urllib.parse import unquote
import difflib
import hashlib
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SUITE = ROOT/'personal-learning-suite'
COURSE = ROOT/'learning/embodied-intelligence'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
active = sorted([*(SUITE/'src/agents').glob('*.md'), *(SUITE/'src/skills').rglob('*.md')])
assets = sorted((SUITE/'src/skills/learning-materials/assets').glob('*.png'))
expected = {p.resolve() for p in active+assets+[SUITE/'contracts/shared-contracts.md']}
manifest = json.loads((COURSE/'framework-manifest.json').read_text(encoding='utf-8-sig'))
seen, manifest_errors = set(), []
for entry in manifest['entries']:
    path = (COURSE/entry['path']).resolve()
    if path in seen or path not in expected or not path.is_file() or sha(path) != entry['sha256']:
        manifest_errors.append(entry['path'])
    seen.add(path)
if seen != expected:
    manifest_errors.append('manifest_scope_mismatch')
if manifest['mode'] != 'manual_files' or any(manifest[k] is not False for k in (
        'native_skill_installation', 'real_runtime_binding', 'independent_agents_started')):
    manifest_errors.append('misstated_runtime_capabilities')

docs = set(active)
docs.update([ROOT/'README.md', ROOT/'docs/README.md', SUITE/'README.md', SUITE/'src/README.md'])
docs.update(COURSE/name for name in ['MODEL_ENTRY.md','FRAMEWORK.md','START_PROMPT.md','README.md','AGENTS.md','INTERACTION.md'])
docs.add(ROOT/'docs/implementation/AI个人学习系统_教学内容重构执行路线_v1.md')
docs.update((ROOT/'docs').glob('*/AI个人学习系统_全套*原意*2026-10-05.md'))
docs.update(OUT.glob('*.md'))
docs.update((OUT/'reviewers').rglob('*.md'))
broken, links = [], 0
# These three exact files are materialized by this run before it returns.
generated_outputs = {OUT/name for name in ['integrity-result.json','public-changes.diff',
                                         'changed-public-files.json']}
for doc in sorted(docs):
    body = re.sub(r'```.*?```', '', doc.read_text(encoding='utf-8-sig'), flags=re.S)
    for match in re.finditer(r'\[[^\]]*\]\((<[^>]+>|[^)]+)\)', body):
        target = match.group(1).strip().strip('<>')
        if target.startswith(('http:', 'https:', 'codex:', 'app:', 'plugin:', 'mailto:', '#')):
            continue
        target = re.sub(r':\d+$', '', unquote(target.split('#',1)[0]))
        path = Path(target)
        if not path.is_absolute():
            path = doc.parent/path
        links += 1
        if not path.exists() and path.resolve() not in generated_outputs:
            broken.append({'document': doc.relative_to(ROOT).as_posix(), 'target': target})

baseline = json.loads((OUT/'before.json').read_text(encoding='utf-8'))
protected_changed = [p for p,h in baseline['protected_public_files'].items()
                     if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
registry = json.loads((SUITE/'resources/source-registry.json').read_text(encoding='utf-8-sig'))
source_errors = [s['source_id'] for s in registry['sources']
                 if sha((SUITE/s['project_relative_path']).resolve())!=s['sha256']]
changes, diff = [], []
with zipfile.ZipFile(OUT/'before.zip') as archive:
    for name in baseline['allowed_existing_changes']:
        old = archive.read(name)
        new = (ROOT/name).read_bytes()
        if old!=new:
            changes.append(name)
            diff.extend(difflib.unified_diff(old.decode('utf-8-sig').splitlines(True),
                new.decode('utf-8-sig').splitlines(True), fromfile='before/'+name, tofile='after/'+name))
(OUT/'public-changes.diff').write_text(''.join(diff), encoding='utf-8')
(OUT/'changed-public-files.json').write_text(json.dumps({'changed_existing_public_files':changes,
    'baseline_public_files':len(baseline['allowed_existing_changes']),
    'private_content_copied':False}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
result = {'status':'pass' if not (manifest_errors or broken or source_errors or protected_changed) else 'fail',
          'instruction_files':len(active), 'public_assets':len(assets),'manifest_entries':len(manifest['entries']),
          'public_documents_checked':len(docs),'local_links_checked':links,'broken_links':broken,
          'manifest_errors':manifest_errors,'frozen_sources_checked':len(registry['sources']),
          'frozen_source_errors':source_errors,'protected_public_files':len(baseline['protected_public_files']),
          'protected_public_changes':protected_changed,'changed_existing_public_files':len(changes),
          'private_records_read_or_hashed_by_this_probe':False,
          'limits':['Public layout/fingerprints only; not pedagogy, learning efficacy or native deployment.']}
(OUT/'integrity-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
raise SystemExit(0 if result['status']=='pass' else 1)
