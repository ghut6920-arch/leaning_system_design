"""Save public review baseline; no private learner files are copied or hashed."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SUITE = ROOT/'personal-learning-suite'
allowed = [*(SUITE/'src/agents').glob('*.md'), *(SUITE/'src/skills').rglob('*.md')]
allowed += [ROOT/p for p in ['README.md', 'docs/README.md', 'personal-learning-suite/README.md',
    'personal-learning-suite/src/README.md',
    'docs/implementation/AI个人学习系统_教学内容重构执行路线_v1.md',
    'learning/embodied-intelligence/FRAMEWORK.md', 'learning/embodied-intelligence/framework-manifest.json']]
names = sorted({p.relative_to(ROOT).as_posix() for p in allowed})
protected = []
for base in [ROOT/'docs', SUITE/'src', SUITE/'contracts', SUITE/'resources', SUITE/'specs',
             SUITE/'scripts', SUITE/'tests', SUITE/'templates', SUITE/'fixtures', SUITE/'validation']:
    protected.extend(p for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts
        and not p.is_relative_to(OUT) and p.relative_to(ROOT).as_posix() not in names)
before = {'allowed_existing_changes': names,
    'protected_public_files': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(set(protected))},
    'private_records_copied_or_fingerprinted': False,
    'audit_kind': 'fresh whole-framework source comparison; independent source-first subagents'}
with zipfile.ZipFile(OUT/'before.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in names:
        archive.write(ROOT/name, name)
(OUT/'before.json').write_text(json.dumps(before, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(f'Public baseline: {len(names)} allowed files; {len(before["protected_public_files"])} protected public files.')
