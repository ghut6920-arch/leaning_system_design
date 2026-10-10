"""Refresh public manifest or summarize actual probe artifacts. No learner input."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SUITE = ROOT/'personal-learning-suite'
COURSE = ROOT/'learning/embodied-intelligence'
def read(name):
    return json.loads((OUT/name).read_text(encoding='utf-8-sig'))

if sys.argv[1:] == ['manifest']:
    path = COURSE/'framework-manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8-sig'))
    files = sorted([SUITE/'contracts/shared-contracts.md',
                    *(SUITE/'src/agents').glob('*.md'), *(SUITE/'src/skills').rglob('*.md'),
                    *(SUITE/'src/skills/learning-materials/assets').glob('*.png')])
    manifest['generated_at'] = '2026-10-05'
    manifest['entries'] = [{'path': Path(os.path.relpath(p, COURSE)).as_posix(),
                           'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    # A link target while checks are still in progress; never a passed assertion.
    (OUT/'verification-summary.json').write_text(json.dumps({'status': 'checks_pending'}, indent=2)+'\n', encoding='utf-8')
    print(f'Public manifest refreshed: {len(files)} entries; capability flags retained.')
elif sys.argv[1:] == ['summary']:
    b0, b7 = read('b0-static-report.json'), read('b7-all-runtime-report.json')
    integrity, guard, content = read('integrity-result.json'), read('learning-unchanged.json'), read('content-probe-result.json')
    coverage, pilot = read('b10-software-slice-index.json'), read('b7-unconfigured-report.json')
    skill_format = read('skill-format-result.json')
    checks = {'b0': b0['status'], 'b7_all': b7['status'], 'integrity': integrity['status'],
              'learner_files_unchanged': 'pass' if guard['unchanged'] else 'fail', 'finite_content': content['status'],
              'b10_software_index': coverage['status'], 'changed_skill_format': skill_format['status']}
    okay = (b0['status']=='pass' and b7['status']=='passed' and integrity['status']=='pass'
            and guard['unchanged'] is True and content['status']=='pass' and coverage['status']=='indexed'
            and skill_format['status']=='pass')
    assert all(v['reported_status']=='not_executed' for v in pilot['reviews'].values())
    result = {'status': 'maintenance_scope_complete' if okay else 'checks_failed',
              'execution_date_in_user_context': '2026-10-05',
              'summary_generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'executor': 'current Codex root model; Python artifact executors',
              'checker': 'same root model with design background; automated public/software checks',
              'forward_review': {'fictional_cases': 16, 'actual_outputs_generated': True,
                    'hypothetical_learner_revisions_generated': False,
                    'independent_agent_execution': 'not_executed_no_authorization',
                    'same_model_design_background': True, 'semantic_review': 'content-review.md',
                    'failures_and_replays': 'failure-replays.md'},
              'checks': checks, 'b0_static_cases': len(b0['static_cases']),
              'b7_tests': b7['tests_run'], 'b7_failures': b7['failures'],
              'b7_errors': b7['errors'], 'b7_skipped': b7['skipped'],
              'b7_host_versions': b7['host_versions'],
              'b10_software_slices': len(coverage['cases']),
              'full_b10_scenarios': 'not_executed',
              'local_content_anchors': 'content-probe-result.json; content-review.md; actual image inspection',
              'publication_integrity': integrity,
              'learner_file_guard': guard,
              'real_validation': {'V1': 'real_pilot_not_executed; limited_public_content_checked',
                 'V2': 'real_pilot_not_executed; fictional_same_model_outputs_only',
                 'V3': 'not_executed', 'V4': 'not_executed'},
              'real_runtime_enabled': False, 'native_skill_installation': False,
              'cost_and_learning_gain_measurement': 'not_executed',
              'report_metadata_note': 'Original B0/B7 scripts retain historical date/checker constants; they are not the current execution date or independent reviewer attribution.',
              'limits': ['No claim of real learning efficacy, causal benefit or universal model capability.',
                 'No standalone skill package or authenticated/isolated multi-model teaching runtime was published.',
                 'Private file bytes hashed only inside resident guard; no private contents/path list/hashes persisted or shown to the model.',
                 'Framework repair did not start a real course or change personal learning records.']}
    (OUT/'verification-summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'checks': checks, 'b7_tests': b7['tests_run']}, ensure_ascii=False))
    raise SystemExit(0 if okay else 1)
else:
    raise SystemExit('Use manifest or summary')
