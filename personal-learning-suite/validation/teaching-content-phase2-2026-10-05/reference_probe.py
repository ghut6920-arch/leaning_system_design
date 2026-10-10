"""Finite content checks and real read-only catalog calls; no learner records.

This validates specific references, not an AI tutor's routing or learning effect.
"""
from fractions import Fraction as F
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
SUITE = ROOT / "personal-learning-suite"
sys.path.insert(0, str(SUITE / "src"))
from runtime.learning_strategies import StrategyCatalog


def rank(rows):
    rows = [[F(v) for v in row] for row in rows]
    pivot = 0
    for col in range(len(rows[0])):
        found = next((i for i in range(pivot, len(rows)) if rows[i][col]), None)
        if found is None:
            continue
        rows[pivot], rows[found] = rows[found], rows[pivot]
        scale = rows[pivot][col]
        rows[pivot] = [v / scale for v in rows[pivot]]
        for i in range(len(rows)):
            if i != pivot:
                factor = rows[i][col]
                rows[i] = [a - factor * b for a, b in zip(rows[i], rows[pivot])]
        pivot += 1
        if pivot == len(rows):
            break
    return pivot


def matvec(rows, vector):
    return [sum(F(a) * F(b) for a, b in zip(row, vector)) for row in rows]


def main():
    catalog = StrategyCatalog()
    index = catalog.index()
    assert index["status"] == "ok" and len(index["entries"]) == 64
    loaded = []
    for entry in index["entries"]:
        if not entry["resource_key"].startswith("post/"):
            continue
        result = catalog.load(entry["resource_key"])
        file_body = json.loads((SUITE / "resources/strategies" / entry["bundle_path"]).read_text(encoding="utf-8"))
        assert result["status"] == "ok" and result["resource"] == file_body
        assert not result["executable"] and not result["mutated"]
        for part in file_body["source_excerpts"] + file_body["evidence_refs"]:
            content = part["content_markdown"]
            assert hashlib.sha256(content.encode()).hexdigest() == part["body_sha256"]
            ref = part["source_ref"]
            loc = ref["locator"]
            lines = (ROOT / ref["workspace_relative_path"]).read_text(encoding="utf-8").splitlines(keepends=True)
            source_body = "".join(lines[loc["start_line"] - 1:loc["end_line"]])
            assert content == source_body, (entry["resource_key"], loc["heading"])
        loaded.append({"key": entry["resource_key"], "returned_complete_file": True,
                       "source_excerpts": len(file_body["source_excerpts"]),
                       "literature_entries": len(file_body["evidence_refs"])})
    fallback = []
    for key in ["encoding/S05", "encoding/D09", "encoding/R06", "encoding/R07", "encoding/R10"]:
        result = catalog.load(key)
        assert result["status"] == "needs_source_review" and not result["executable"]
        card_id = key.split("/")[1]
        for ref in result["source_refs"]:
            path = ROOT / ref["workspace_relative_path"]
            loc = ref["locator"]
            if loc["kind"] == "json_pointer":
                value = json.loads(path.read_text(encoding="utf-8"))
                for token in loc["pointer"].strip("/").split("/"):
                    value = value[int(token)] if isinstance(value, list) else value[token]
                assert value["id"] == card_id and value["content_markdown"].strip()
            else:
                lines = path.read_text(encoding="utf-8").splitlines()
                assert lines[loc["start_line"] - 1] == loc["heading"]
                assert lines[loc["start_line"] - 1:loc["end_line"]][-1] == ""
        fallback.append({"key": key, "status": result["status"], "original_locations_resolve": True})

    # Execute the actual Python example and compare to the analytic closed form.
    example = (SUITE / "src/skills/learning-teaching/references/method-post-examples.md").read_text(encoding="utf-8")
    code = re.findall(r"```python\n(.*?)```", example, re.S)[0]
    tree = ast.parse(code)
    assert len(tree.body) == 1 and isinstance(tree.body[0], ast.FunctionDef)
    namespace = {}
    exec(compile(tree, "phase2-example", "exec"), namespace)
    dynamic_checks = []
    for q in [0.0, 0.2, 1.0, 1.2, 2.0, 2.2]:
        rows = namespace["trajectory"](q)
        for t, x, error in rows:
            expected = (1 - q) ** t
            assert abs(error - expected) < 1e-10 and abs(x + error - 1) < 1e-10
        dynamic_checks.append({"q": q, "states_checked": len(rows), "final_error": rows[-1][2]})
    delayed = [1.0, 1.0]
    for _ in range(16):
        delayed.append(delayed[-1] - 1.2 * delayed[-2])
    assert abs(delayed[-1]) > abs(delayed[0])

    # Exact arithmetic checks for weighted means and the stated equality condition.
    assert F(20 * 90 + 60 * 70, 80) == 75
    assert F(10 * 80 + 30 * 60, 40) == 65
    assert F(80 + 60, 2) == 70
    mean_conditions = 0
    for n1 in [1, 2, 5]:
        for n2 in [1, 2, 5]:
            for m1 in [0, 3, 7]:
                for m2 in [0, 3, 7]:
                    weighted = F(n1 * m1 + n2 * m2, n1 + n2)
                    plain = F(m1 + m2, 2)
                    assert (weighted == plain) == ((n1 - n2) * (m1 - m2) == 0)
                    mean_conditions += 1
    speed1, speed2 = F(20), F(40)
    time1 = time2 = F(1)
    equal_time_speed = (speed1 * time1 + speed2 * time2) / (time1 + time2)
    distance1 = distance2 = F(1)
    equal_distance_speed = (distance1 + distance2) / (distance1 / speed1 + distance2 / speed2)
    assert equal_time_speed == F(30) and equal_distance_speed == F(80, 3)
    assert equal_distance_speed != (speed1 + speed2) / 2

    # Check concrete rank-one constructions, including a same-rank invalid one.
    A = [[1, 1, 0], [0, 1, 1]]
    n = [1, -1, 1]
    u = [1, 1, 0]
    Qn = [[F(a * b, 3) for b in n] for a in n]
    Qdiag = [[1, 0, 0], [0, 0, 0], [0, 0, 0]]
    Qbad = [[a * b for b in u] for a in u]
    assert matvec(A, n) == [0, 0]
    matrix_checks = []
    for name, Q, expected_rank in [("projector", Qn, 3), ("diagonal", Qdiag, 3), ("wrong_direction", Qbad, 2)]:
        assert rank(Q) == 1 and rank(A + Q) == expected_rank
        matrix_checks.append({"construction": name, "rank_Q": rank(Q), "stacked_rank": rank(A + Q)})
    for lam in [F(1, 2), F(1), F(3)]:
        x1 = F(2) / (1 + lam)
        assert 2 * (x1 - 2) + 2 * lam * x1 == 0
        assert 2 + 2 * lam > 0
    full_rank = [[1, 0], [0, 1]]
    assert rank(full_rank) == 2 and rank([[0, 0], [0, 0]]) == 0

    # Closed hypothetical interface spec, not a claim about any real API.
    def mean(values, version):
        if version not in {"v1", "v2"}:
            raise ValueError("version required")
        if not values:
            return 0 if version == "v1" else None
        return F(sum(values), len(values))
    assert mean([], "v1") == 0 and mean([], "v2") is None
    assert mean([2, 4], "v1") == mean([2, 4], "v2") == 3
    try:
        mean([], None)
    except ValueError:
        pass
    else:
        raise AssertionError("unknown version must not silently select the latest")
    report = {
        "status": "pass", "date": "2026-10-05", "synthetic_content_only": True,
        "post_full_loads": loaded, "uncompiled_fallbacks": fallback,
        "literal_index_limits": {"ranking": index["ranking"], "executable": index["executable"]},
        "dynamic_closed_form_checks": dynamic_checks,
        "delayed_counterexample_q": 1.2, "delayed_final_error": delayed[-1],
        "mean_equality_finite_cases": mean_conditions, "rank_examples": matrix_checks,
        "affine_lambda_cases": 3, "version_reference_checked": True,
        "limitations": ["数值与代数算例不是一般定理证明", "目录行为不证明模型会自主发现方法",
                        "没有独立模型执行或真实用户学习试验", "本次没有重新核验外部论文"]}
    output = Path(__file__).with_name("reference-probe-result.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
