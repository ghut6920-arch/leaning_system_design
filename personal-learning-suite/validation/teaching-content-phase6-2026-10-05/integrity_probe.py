"""Verify public project layout; never open/list private learner records.

This does not assert teaching behavior, installer independence or learning gain.
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
    if not path.is_relative_to(ROOT):
        manifest_errors.append('public_dependency_outside_project')
    seen.add(path)
if seen != expected:
    manifest_errors.append('manifest_scope_mismatch')
if manifest['mode'] != 'manual_files' or any(manifest[k] is not False for k in (
        'native_skill_installation', 'real_runtime_binding', 'independent_agents_started')):
    manifest_errors.append('misstated_capability_flags')

docs = set(active)
docs.update([ROOT/'README.md', ROOT/'docs/README.md', SUITE/'README.md', SUITE/'src/README.md'])
# Only these six public protocols are read; no course state/originals are scanned.
docs.update(COURSE/name for name in ['MODEL_ENTRY.md', 'FRAMEWORK.md', 'START_PROMPT.md',
                                    'README.md', 'AGENTS.md', 'INTERACTION.md'])
docs.add(ROOT/'docs/implementation/AI个人学习系统_教学内容重构执行路线_v1.md')
docs.update((ROOT/'docs').glob('*/AI个人学习系统_*第六阶段*2026-10-05.md'))
docs.update(OUT.glob('*.md'))
docs.update((OUT/'forward-inputs').glob('*.md'))
broken, outside, count = [], [], 0
for doc in sorted(docs):
    body = re.sub(r'```.*?```', '', doc.read_text(encoding='utf-8-sig'), flags=re.S)
    for match in re.finditer(r'\[[^\]]*\]\((<[^>]+>|[^)]+)\)', body):
        target = match.group(1).strip().strip('<>')
        if target.startswith(('http:', 'https:', 'codex:', 'app:', 'plugin:', 'mailto:', '#')):
            continue
        target = re.sub(r':\d+$', '', unquote(target.split('#', 1)[0]))
        path = Path(target)
        if not path.is_absolute():
            path = doc.parent/path
        path = path.resolve()
        count += 1
        if not path.exists():
            broken.append({'document': doc.relative_to(ROOT).as_posix(), 'target': target})
        if not path.is_relative_to(ROOT):
            outside.append({'document': doc.relative_to(ROOT).as_posix(), 'target': target})

baseline = json.loads((OUT/'before.json').read_text(encoding='utf-8'))
protected_changed = [p for p, h in baseline['protected_public_files'].items()
                     if not (ROOT/p).is_file() or sha(ROOT/p) != h]
registry = json.loads((SUITE/'resources/source-registry.json').read_text(encoding='utf-8-sig'))
source_errors = [s['source_id'] for s in registry['sources']
                 if sha((SUITE/s['project_relative_path']).resolve()) != s['sha256']]
changes, diff = [], []
with zipfile.ZipFile(OUT/'before.zip') as archive:
    for name in baseline['allowed_existing_changes']:
        old = archive.read(name)
        new = (ROOT/name).read_bytes()
        if old != new:
            changes.append(name)
            diff.extend(difflib.unified_diff(old.decode('utf-8-sig').splitlines(True),
                new.decode('utf-8-sig').splitlines(True), fromfile='before/'+name, tofile='after/'+name))
(OUT/'public-changes.diff').write_text(''.join(diff), encoding='utf-8')
(OUT/'changed-public-files.json').write_text(json.dumps({
    'existing_public_files_changed': changes,
    'new_instruction_reference': 'personal-learning-suite/src/skills/personal-learning/references/verification.md',
    'private_files_copied_or_persistently_fingerprinted': False,
    'baseline_archive_public_files': len(baseline['allowed_existing_changes'])}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
result = {'status': 'pass' if not (manifest_errors or broken or outside or source_errors or protected_changed) else 'fail',
          'active_instruction_files': len(active), 'public_assets': len(assets),
          'framework_entries': len(manifest['entries']), 'documents_checked': len(docs),
          'local_links_checked': count, 'broken_links': broken, 'links_outside_project': outside,
          'manifest_errors': manifest_errors, 'frozen_sources_checked': len(registry['sources']),
          'frozen_source_errors': source_errors,
          'protected_public_files_checked': len(baseline['protected_public_files']),
          'protected_public_files_changed': protected_changed,
          'existing_public_files_changed': len(changes),
          'private_learner_files_read_or_hashed_by_this_probe': False,
          'scope': 'Current whole-project public relative layout and exact manifest; not standalone installation.',
          'limitations': ['No behavior/learning-efficacy assertion.',
              'Frozen original research excerpts may retain historical absolute source paths; registry provides current project-relative lookup.',
              'No private originals, state, learner code or experiments are scanned.']}
(OUT/'integrity-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
raise SystemExit(0 if result['status'] == 'pass' else 1)
