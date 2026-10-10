"""AI-authored teacher check, revision1; no learner run or progress update.

Checks the exact classroom data and conditional examples against explicit
coordinate contracts. Reuses the existing standard-library teacher reference.
No installs, training, PyTorch execution, or real camera/robot operations.
All output is confined to the requested candidate preparation package.
"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import platform
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
PACK = ROOT / "artifacts/preparation-tests/2026-10-08-video-interface-single-model"
REFERENCE = ROOT / "code/M0/video_interface_sequence_reference.py"
module_spec = importlib.util.spec_from_file_location("prep_video_reference", REFERENCE)
ref = importlib.util.module_from_spec(module_spec)
sys.modules[module_spec.name] = ref
module_spec.loader.exec_module(ref)


def flatten(value):
    if isinstance(value, list):
        return [item for part in value for item in flatten(part)]
    return [value]


def reshape_logical(value, dimensions):
    source = iter(flatten(value))

    def build(depth):
        if depth == len(dimensions):
            return next(source)
        return [build(depth + 1) for _ in range(dimensions[depth])]

    result = build(0)
    if next(source, None) is not None:
        raise ValueError("Element count does not fit")
    return result


def expect_value_error(operation):
    try:
        operation()
    except ValueError:
        return True
    return False


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = json.loads((PACK / "data.json").read_text(encoding="utf-8-sig"))
    spec = ref.Spec(**data["spec"])
    x = data["camera"]
    B, T, H, W, C = spec.batch, spec.time, spec.height, spec.width, spec.channels
    checks = []

    def check(name, condition, scope):
        checks.append({"name": name, "passed": bool(condition), "scope": scope})

    valid_shape = (len(x) == B and all(len(v) == T for v in x)
                   and all(len(frame) == H for v in x for frame in v)
                   and all(len(row) == W for v in x for frame in v for row in frame)
                   and all(len(pixel) == C for v in x for frame in v for row in frame for pixel in row))
    check("exact_input_shape", valid_shape and len(flatten(x)) == 96, "Complete 2x4x2x2x3 teaching input")
    y = ref.to_video(x, spec)
    z, ids = ref.to_frames(x, spec)
    check("all_video_pixel_coordinates", all(y[b][c][t][h][w] == x[b][t][h][w][c]
          for b in range(B) for t in range(T) for h in range(H) for w in range(W) for c in range(C)),
          "All 96 positions; y[b,c,t,h,w]=x[b,t,h,w,c]")
    check("all_frame_pixel_coordinates", all(z[b*T+t][c][h][w] == x[b][t][h][w][c]
          for b in range(B) for t in range(T) for h in range(H) for w in range(W) for c in range(C)),
          "All 96 positions; z[b*T+t,c,h,w]=x[b,t,h,w,c]")

    nhwc = reshape_logical(x, [B*T, H, W, C])
    alternative = [[[[nhwc[k][h][w][c] for w in range(W)] for h in range(H)]
                    for c in range(C)] for k in range(B*T)]
    btchw = [[y[b][c][t] for c in range(C)] for b in range(B) for t in range(T)]
    check("legal_alternative_routes", alternative == z and btchw == z,
          "Merge B/T before moving C, or move T before C from y then merge")

    wrong = reshape_logical(y, [B*T, C, H, W])
    check("direct_y_reshape_counterexample", wrong[0][1][0][0] == 21
          and z[0][1][0][0] == 12 and wrong != z,
          "Wrong logical reshape preserves count but fails specific identity")
    check("specified_pixel_trace", x[1][2][0][0][2] == y[1][2][2][0][0] == z[6][2][0][0] == 99,
          "乙3 top-left blue through both input paths")

    f = ref.toy_encode(z)
    check("all_eight_feature_rows", f == data["expected_features"], "Specified selection e, no row reorder")
    s = ref.restore_sequence(f, B, T, order_confirmed=True)
    check("preserved_order_restore", s == [f[:4], f[4:]] and s[1][2] == [11,12],
          "B/T and confirmed order suffice without explicit IDs")
    check("feature_collision_and_distinct_images", z[0] != z[6] and f[0] == f[6] == [11,12],
          "Different images/sources have same vector; no intrinsic unique source ID")
    altered = copy.deepcopy(z)
    altered[0][2][0][0] = 99
    altered[0][0][1][1] = 200
    check("unselected_content_not_recoverable", ref.toy_encode(altered) == f and altered != z,
          "Blue and another pixel changed with identical output; exact image inversion impossible from f alone")

    permutation = data["extra_permutation"]
    fp = [f[k] for k in permutation]
    idp = [ids[k] for k in permutation]
    tagged = ref.restore_sequence(fp, B, T, frame_ids=idp)
    check("paired_metadata_restore", tagged == s and idp[0] == (1,2)
          and [permutation.index(k) for k in range(B*T)] == data["expected_inverse_permutation"],
          "Entire paired row permutation restores original sequence")
    check("unknown_order_rejected", expect_value_error(lambda: ref.restore_sequence(fp, B, T)),
          "Known B/T and shape alone do not supply row provenance")
    duplicate = list(idp)
    duplicate[1] = duplicate[0]
    check("duplicate_labels_rejected", expect_value_error(lambda: ref.restore_sequence(fp, B, T, frame_ids=duplicate)),
          "Every source slot must occur once")
    check("missing_labels_rejected", expect_value_error(lambda: ref.restore_sequence(fp, B, T, frame_ids=idp[:-1])),
          "Complete fixed-length consumer requires complete metadata")
    out_of_range = list(idp)
    out_of_range[0] = (2,2)
    check("out_of_range_labels_rejected", expect_value_error(lambda: ref.restore_sequence(fp, B, T, frame_ids=out_of_range)),
          "Trusted labels must match declared domain")
    e2 = [[row[0]+row[1], row[0]-row[1]] for row in f]
    check("new_values_without_reorder", e2[0] == [23,-1] and e2[6] == [23,-1] and len(e2) == 8,
          "Alternative per-frame function changes values, not ordering/provenance")
    g = s[0][1][0] - s[0][0][0]
    swapped = s[0][0][0] - s[0][1][0]
    check("specified_order_sensitive_consumer", g == 10 and swapped == -10,
          "Only specified toy G; no learned dynamics claim")

    baseline = json.loads((PACK / "protected-baseline.json").read_text(encoding="utf-8"))
    changed = [name for name, digest in baseline["files"].items()
               if not (ROOT / name).is_file() or sha(ROOT / name) != digest]
    check("preexisting_workspace_files_unchanged", not changed,
          f"All {len(baseline['files'])} baseline files; no real record/progress changes")
    framework = json.loads((ROOT / "framework-manifest.json").read_text(encoding="utf-8-sig"))
    mismatches = [entry["path"] for entry in framework["entries"]
                  if not (ROOT / entry["path"]).is_file() or sha(ROOT / entry["path"]) != entry["sha256"]]
    check("framework_manifest_matches", not mismatches, f"All {len(framework['entries'])} registered files")

    broken = []
    for path in PACK.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^\s)]+)\)", text):
            if target.startswith(("https://", "http://", "#")):
                continue
            resolved = path.parent / target.split("#", 1)[0]
            if not resolved.exists():
                broken.append({"file": path.name, "target": target})
    check("local_artifact_links_resolve", not broken, "All local Markdown link destinations in candidate package")
    report = {
        "revision": 1, "date": "2026-10-08", "timezone": "Asia/Shanghai",
        "purpose": "candidate_material_verification", "single_model_self_check": True,
        "teacher_execution": True, "learner_execution": "not_executed",
        "formal_teaching": "not_executed", "learning_effect": "not_verified",
        "comparative_benefit": "not_verified", "pytorch_execution": "not_executed",
        "environment": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                        "executable": sys.executable},
        "data_sha256": sha(PACK / "data.json"), "reference_sha256": sha(REFERENCE),
        "checks": checks, "passed": sum(item["passed"] for item in checks),
        "total": len(checks), "changed_preexisting_files": changed,
        "framework_mismatches": mismatches, "broken_local_links": broken,
        "cost": {"user_active_time": "not_executed", "system_effort": "unknown", "blocked_wait": "unknown"},
        "limitations": ["Finite checks on explicit teaching data, not general proof",
                        "No learner response, independent review, PyTorch runtime, training or robot test"]
    }
    (PACK / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "total": report["total"],
                      "failures": [x for x in checks if not x["passed"]], "changed": changed,
                      "broken_links": broken}, ensure_ascii=False))
    return 0 if all(item["passed"] for item in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
