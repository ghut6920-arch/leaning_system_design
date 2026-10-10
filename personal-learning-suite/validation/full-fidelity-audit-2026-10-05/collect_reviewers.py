"""Copy explicitly scoped fictional/public reviews; never scan learner folders."""
from pathlib import Path
import hashlib
import json
import os
import shutil

OUT = Path(__file__).resolve().parent
SOURCE = Path(os.environ['TEMP'])/'learning-suite-audit-20261005'
groups = ['entry-continuity-fresh', 'design-assessment-fresh', 'teaching-forward-fresh']
records = []
for group in groups:
    source = (SOURCE/group).resolve()
    target = (OUT/'reviewers'/group).resolve()
    if not source.is_relative_to(SOURCE.resolve()) or not target.is_relative_to(OUT):
        raise ValueError('Review copy escaped its explicitly scoped directory.')
    required = {'entry-continuity-fresh':['audit-report.md','source-coverage.md','source-completion.md'],
        'design-assessment-fresh':['audit.md','coverage.md'],
        'teaching-forward-fresh':['fresh-validation-report.md','coverage.json','source-completion.md']}
    if not source.is_dir() or any(not (source/name).is_file() for name in required[group]):
        raise FileNotFoundError(f'No completed public review: {group}')
    if target.exists():
        raise FileExistsError(f'Preserve existing review copy: {target}')
    files = [p for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    if any(p.is_symlink() or not p.resolve().is_relative_to(source) for p in files):
        raise ValueError('Review copy includes a symlink or escaped file.')
    for path in files:
        destination = target/path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        records.append({'reviewer':group, 'path':destination.relative_to(OUT).as_posix(),
            'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()})
request = SOURCE/'teaching/forward-requests.json'
destination = OUT/'teaching-forward-requests.json'
if destination.exists():
    raise FileExistsError('Preserve existing copied raw requests.')
shutil.copy2(request, destination)
records.append({'reviewer':'teaching-forward-fresh-original-requests',
    'path':destination.relative_to(OUT).as_posix(),
    'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()})
(OUT/'review-artifacts.json').write_text(json.dumps({
    'kind':'public original-source review and fictional first responses',
    'copied_from_explicit_temporary_review_folders':True,
    'real_learner_records_copied':False, 'artifacts':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'reviewer_groups':len(groups),'public_artifacts':len(records),
                  'real_learner_records_copied':False},ensure_ascii=False))
