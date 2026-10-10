"""Read-only checks for the initialized file learning workspace."""
from pathlib import Path
from urllib.parse import unquote
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT / 'learning/embodied-intelligence'
SOURCE = Path('C:/Users/15006/Downloads/embodied_world_model_foundations_syllabus_2026-10-04 (1).md')
manifest = json.loads((WORKSPACE / 'framework-manifest.json').read_text(encoding='utf-8'))
broken_links = []
checked_links = 0
for file in [*WORKSPACE.rglob('*.md'), ROOT / 'README.md']:
    body = file.read_text(encoding='utf-8-sig')
    for match in re.finditer(r'\[[^\]\n]*\]\((<[^>]+>|[^)\n]+)\)', body):
        target = match.group(1).strip().strip('<>')
        if target.startswith(('#', 'http://', 'https://', 'mailto:', 'data:')):
            continue
        target = unquote(target.split('#')[0])
        if not target:
            continue
        checked_links += 1
        path = (file.parent / target).resolve()
        if not path.exists():
            broken_links.append({'file': file.relative_to(ROOT).as_posix(), 'target': target})

framework_changed = []
for entry in manifest['entries']:
    path = (WORKSPACE / entry['path']).resolve()
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
        framework_changed.append(entry['path'])

original = (WORKSPACE / 'course/original-syllabus.md').read_text(encoding='utf-8-sig')
source_rows = [line for line in original.splitlines() if re.match(r'^\| M[0-8]\.\d+', line)]
module_rows = []
for index in range(9):
    text = (WORKSPACE / f'modules/M{index}/README.md').read_text(encoding='utf-8')
    module_rows.extend(line for line in text.splitlines() if re.match(r'^\| M[0-8]\.\d+', line))
hours = sum(int(re.split(r'(?<!\\)\|', line)[3].strip()) for line in source_rows)
gate_count = len(re.findall(r'^### G[0-5] ', (WORKSPACE / 'goals/course-goals-draft.md').read_text(encoding='utf-8'), re.M))
report = {
    'validation_scope': 'initialization, source preservation, local links and shared rule references; no teaching effectiveness claim',
    'files_created': len([p for p in WORKSPACE.rglob('*') if p.is_file()]),
    'source_copy_byte_equal': SOURCE.read_bytes() == (WORKSPACE / 'course/original-syllabus.md').read_bytes() if SOURCE.exists() else 'not_checked_original_unavailable',
    'module_count': len(list((WORKSPACE / 'modules').glob('M*/README.md'))),
    'chapter_rows_equal': source_rows == module_rows,
    'chapter_count': len(source_rows),
    'estimated_hours_from_chapter_rows': hours,
    'gate_count': gate_count,
    'checked_local_links': checked_links,
    'broken_links': broken_links,
    'framework_reference_count': len(manifest['entries']),
    'missing_or_changed_framework_files': framework_changed,
    'real_runtime_binding': manifest['real_runtime_binding'],
    'databases_in_learning_workspace': [p.relative_to(WORKSPACE).as_posix() for p in WORKSPACE.rglob('*') if p.suffix.lower() in {'.db', '.sqlite', '.sqlite3'}],
    'actual_session_directories': [p.name for p in (WORKSPACE / 'sessions').iterdir() if p.is_dir()],
}
report['passed'] = (
    not broken_links and not framework_changed
    and report['source_copy_byte_equal'] in {True, 'not_checked_original_unavailable'}
    and report['chapter_rows_equal'] and hours == 260
    and report['module_count'] == 9 and gate_count == 6
    and report['framework_reference_count'] == 32
    and not report['databases_in_learning_workspace']
    and not report['actual_session_directories']
    and not report['real_runtime_binding']
)
(Path(__file__).parent / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report['passed'] else 1)
