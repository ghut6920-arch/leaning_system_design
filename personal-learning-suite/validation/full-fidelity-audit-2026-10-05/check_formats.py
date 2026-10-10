"""Actually invoke the installed format checker on all seven Skill entries."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
validator = Path('C:/Users/15006/.codex/skills/.system/skill-creator/scripts/quick_validate.py')
results = []
for entry in sorted((ROOT/'personal-learning-suite/src/skills').glob('*/SKILL.md')):
    completed = subprocess.run([sys.executable,'-X','utf8',str(validator),str(entry.parent)],
        capture_output=True, text=True, encoding='utf-8')
    results.append({'skill':entry.parent.name,'exit_code':completed.returncode,
                    'stdout':completed.stdout,'stderr':completed.stderr})
okay = len(results)==7 and all(row['exit_code']==0 for row in results)
(OUT/'skill-format-results.json').write_text(json.dumps({'status':'pass' if okay else 'fail',
    'execution_date_in_user_context':'2026-10-05','python':sys.version,
    'validator':str(validator),'results':results,
    'limits':['Frontmatter and unfinished-scaffold checks; no semantic pedagogy assertion.']}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(f'Skill formats: {len(results)} checked; status {"pass" if okay else "fail"}.')
raise SystemExit(0 if okay else 1)
