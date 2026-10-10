"""Check public maintenance scope, source integrity, links and framework pointers."""
from pathlib import Path
from urllib.parse import unquote
import difflib
import hashlib
import json
import re
import sys
import zipfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SUITE = ROOT / "personal-learning-suite"
COURSE = ROOT / "learning/embodied-intelligence"
REPORT = ROOT / "docs/implementation/AI个人学习系统_单元收束与调用核查修复_2026-10-07.md"
ALLOWED = {
 "personal-learning-suite/src/skills/learning-teaching/references/design-whole.md",
 "personal-learning-suite/src/skills/learning-teaching/references/post-encoding.md",
 "personal-learning-suite/src/skills/learning-planning/references/recovery.md",
 "personal-learning-suite/src/skills/learning-assessment/SKILL.md",
 "personal-learning-suite/src/agents/AG0-coach.md",
 "personal-learning-suite/src/agents/AG1-design-planning.md",
 "personal-learning-suite/src/agents/AG3-assessment.md",
 "personal-learning-suite/src/README.md", "docs/README.md",
 "learning/embodied-intelligence/MODEL_ENTRY.md", "learning/embodied-intelligence/FRAMEWORK.md",
 "learning/embodied-intelligence/START_PROMPT.md", "learning/embodied-intelligence/framework-manifest.json"
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    baseline = json.loads((OUT / "baseline.json").read_text(encoding="utf-8"))
    changed = [name for name,value in baseline["files"].items()
               if not (ROOT / name).is_file() or sha(ROOT / name) != value]
    unexpected = sorted(set(changed) - ALLOWED)
    source_errors = [name for name in baseline["sources"] if not (ROOT / name).is_file() or sha(ROOT / name) != baseline["files"][name]]
    manifest_file=COURSE / "framework-manifest.json"
    manifest=json.loads(manifest_file.read_text(encoding="utf-8-sig"))
    errors=[]
    if manifest["mode"] != "manual_files" or any(manifest[k] is not False for k in ["native_skill_installation","real_runtime_binding","independent_agents_started"]):
        errors.append("capability_claims")
    if "--refresh" in sys.argv:
        if unexpected or source_errors or errors:
            raise ValueError("Refuse refresh while scope/source/capability errors exist")
        for item in manifest["entries"]:
            item["sha256"]=sha((COURSE / item["path"]).resolve())
        manifest["generated_at"]="2026-10-07"
        manifest_file.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for item in manifest["entries"]:
        p=(COURSE / item["path"]).resolve()
        if not p.is_file() or sha(p)!=item["sha256"]:errors.append(item["path"])
    active=set((SUITE / "src/skills").rglob("*.md")) | set((SUITE / "src/agents").glob("*.md"))
    docs=active | set(COURSE.glob("*.md")) | {ROOT / name for name in ALLOWED if name.endswith('.md')} | {REPORT}
    docs |= {COURSE / p for p in [
     "state/current.md","plan/current.md","plan/needs.md","sessions/2026-10-06-02/checkpoint.md","sessions/2026-10-06-02/session.md",
     "artifacts/M0-video-interface-working-view-20261007.md","questions/visible/M0-video-feature-sequence-20261007-v1.md",
     "questions/teacher-reference/M0-video-feature-sequence-20261007-v1.md","materials/M0-video-feature-sequence-20261007-sources.md",
     "assessment/M0-video-interface-closure-review-20261007.md","reviews/2026-10-07-skill-agent-call-audit.md",
     "reviews/2026-10-07-closure-execution-check.md"]}
    links=0;broken=[]
    for p in sorted(docs):
        if not p.is_file():continue
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)",p.read_text(encoding='utf-8-sig')):
            target=target.strip('<>').split('#')[0]
            if not target or '://' in target:continue
            target=re.sub(r':\d+$','',unquote(target));links+=1
            if not (p.parent/target).resolve().is_file():broken.append({'file':p.relative_to(ROOT).as_posix(),'target':target})
    diff=[]
    with zipfile.ZipFile(OUT / 'before-files.zip') as z:
        for name in sorted(changed):
            if name.endswith('.md') and name in z.namelist():
                before=z.read(name).decode('utf-8-sig').replace('\r\n','\n').splitlines(True)
                after=(ROOT/name).read_text(encoding='utf-8-sig').splitlines(True)
                diff.extend(difflib.unified_diff(before,after,fromfile='before/'+name,tofile='after/'+name))
    (OUT/'public-changes.diff').write_text(''.join(diff),encoding='utf-8')
    result={'status':'pass' if not(unexpected or source_errors or errors or broken) else 'fail',
            'changed_public_files':sorted(changed),'unexpected_changes':unexpected,'registered_sources_checked':len(baseline['sources']),
            'source_errors':source_errors,'links_checked':links,'broken_links':broken,'manifest_entries':len(manifest['entries']),
            'manifest_errors':errors,'limits':['Only public baseline/diff retained here; private snapshot remains inside the course',
                                            'Links and hashes are not learning-effect or independent-Agent proof']}
    (OUT/'integrity-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['status','unexpected_changes','registered_sources_checked','source_errors','links_checked','broken_links','manifest_entries','manifest_errors']},ensure_ascii=False))
    return 0 if result['status']=='pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
