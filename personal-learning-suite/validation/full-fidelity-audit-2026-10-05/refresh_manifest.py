"""Refresh existing public framework entries without asserting runtime deployment."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
COURSE = ROOT/'learning/embodied-intelligence'
FILE = COURSE/'framework-manifest.json'
data = json.loads(FILE.read_text(encoding='utf-8-sig'))
for entry in data['entries']:
    path = (COURSE/entry['path']).resolve()
    if not path.is_relative_to(ROOT/'personal-learning-suite'):
        raise ValueError('Unexpected manifest scope')
    entry['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
data['generated_at'] = '2026-10-05'
assert data['mode'] == 'manual_files'
assert all(data[k] is False for k in ['native_skill_installation',
    'real_runtime_binding','independent_agents_started'])
FILE.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'public_entries_refreshed':len(data['entries']),
    'native_skill_installation':False,'real_runtime_binding':False,
    'course_independent_agents_started':False},ensure_ascii=False))
