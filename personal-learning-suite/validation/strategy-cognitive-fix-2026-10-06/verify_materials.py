"""Verify fictional interface mathematics and read actual compiled method bodies."""
from fractions import Fraction as F
from pathlib import Path
import hashlib
import json
import sys

OUT = Path(__file__).resolve().parent
SUITE = OUT.parents[1]
sys.path.insert(0, str(SUITE / "src"))
from runtime.learning_strategies import StrategyCatalog
sys.path.insert(0, str(OUT / "example"))
from interface import pipeline


def main():
    raw = [[[F(2), F(4)], [F(6), F(8)]], [[F(1), F(3)], [F(5), F(7)]]]
    v, g, f = pipeline(raw)
    checks = []
    def check(name, passed):
        if not passed:
            raise AssertionError(name)
        checks.append({"case": name, "pass": True})
    for n in range(2):
        for t in range(2):
            for c in range(2):
                check(f"coordinate/{n}/{t}/{c}", v[n][c][t] == raw[n][t][c] / 10)
            check(f"whole-formula/{n}/{t}", f[n][t] == (raw[n][t][0] + 2 * raw[n][t][1]) / 10)
    check("exact-output", f == [[F(1), F(11, 5)], [F(7, 10), F(19, 10)]])
    check("shape-equality-does-not-identify-roles", [v[0][0][0], v[0][0][1]] != [raw[0][0][0] / 10, raw[0][0][1] / 10])
    changed = [[list(row) for row in batch] for batch in raw]
    changed[0][1][1] += 1
    _, _, f2 = pipeline(changed)
    check("raw-channel-change-retains-scaling", f2[0][1] - f[0][1] == F(1, 5))
    check("other-output-unchanged", f2[0][0] == f[0][0] and f2[1] == f[1])
    check("combination-not-invertible-from-one-feature", (F(2) + 2 * F(4)) / 10 == (F(4) + 2 * F(3)) / 10)
    a = [[v[n][0][t] + 2 * v[n][1][t] for t in range(2)] for n in range(2)]
    check("A-no-repeat-scaling-or-permutation", a == f)
    b = [[[value / 10 for value in row] for row in batch] for batch in raw]
    check("B-keeps-original-role-order", b == [[[F(1,5),F(2,5)],[F(3,5),F(4,5)]],[[F(1,10),F(3,10)],[F(1,2),F(7,10)]]])

    catalog = StrategyCatalog()
    reads = []
    keys = ["encoding/S05", "encoding/D02", "encoding/X05", "encoding/S09",
            "post/retrieve-relation", "post/select-method"]
    for key in keys:
        loaded = catalog.load(key)
        check("complete-resource-load/" + key, loaded["status"] == "ok")
        resource = loaded["resource"]
        # Reading/deserializing is recorded; the report does not imply independent semantic judgment.
        entry = next(x for x in catalog.index()["entries"] if x["resource_key"] == key)
        path = catalog.root / entry["bundle_path"]
        reads.append({"resource_key": key, "resource_revision": resource["resource_revision"],
                      "bundle_path": entry["bundle_path"], "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "full_carriers": list(resource.get("full_carriers", {})),
                      "post_source_excerpts": len(resource.get("source_excerpts", [])),
                      "scope": "Whole JSON fetched and parsed; author separately reviewed operating bodies/source excerpts"})
    result = {"status": "pass", "mathematical_checks": len(checks) - len(keys),
              "resource_load_checks": len(keys), "checks": checks, "actual_resource_reads": reads,
              "limitations": ["Self-contained hypothetical specifications; no personal learner facts",
                             "Numerical checks supplement stated algebra; not a learning-effect test",
                             "Current model authored and self-reviewed classroom; no independent forward test"]}
    (OUT / "material-checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ["status", "mathematical_checks", "resource_load_checks"]}))


if __name__ == "__main__":
    main()
