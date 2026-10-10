"""Full-library availability and source-preservation checks, not learning-effect tests."""
import copy
import json
from pathlib import Path
import sys
import unittest

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
sys.path.insert(0, str(SUITE / "scripts"))
from runtime.learning_strategies import StrategyCatalog
from build_b3c_resources import Sources, build_files, card_sections, normalize_citations, parse_cards


class FullLibraryTests(unittest.TestCase):
    def test_all_64_complete_resources_are_readable_and_keep_original_operations(self):
        catalog = StrategyCatalog()
        entries = catalog.index()["entries"]
        self.assertEqual(len(entries), 64)
        library = json.loads((SUITE.parent / "docs/research/04_Encoding策略库.json").read_text(encoding="utf-8-sig"))
        originals = {op["id"]: op for op in library["operations"]}
        for entry in entries:
            with self.subTest(key=entry["resource_key"]):
                self.assertTrue(entry["compiled"])
                result = catalog.load(entry["resource_key"])
                self.assertEqual(result["status"], "ok")
                self.assertFalse(result["executable"])
                resource = result["resource"]
                self.assertTrue(resource["required_learner_operations"])
                if resource["resource_kind"] == "encoding-card-bundle":
                    op = originals[resource["original_id"]]
                    self.assertEqual(resource["full_carriers"]["R03"]["content_markdown"], op["content_markdown"])
                    self.assertEqual(resource["source_body_sections"], card_sections(op))
                    self.assertEqual(set(resource["evidence_ids"]), {r["evidence_id"] for r in resource["evidence_refs"]})
                    self.assertEqual(len(resource["research_excerpts"]), len(op["evidence_ids"]))
                else:
                    self.assertTrue(all(x["content_markdown"] and x["source_ref"] for x in resource["source_excerpts"]))

    def test_all_generated_files_are_byte_reproducible(self):
        files = build_files()
        self.assertEqual(len(files), 68)
        for name, data in files.items():
            with self.subTest(path=name):
                self.assertEqual((SUITE / "resources/strategies" / name).read_bytes(), data)

    def test_missing_original_acceptance_is_not_silently_compiled(self):
        library = json.loads(Sources().texts["R03"])
        op = copy.deepcopy(library["operations"][0])
        op["content_markdown"] = "\n".join(ln for ln in op["content_markdown"].splitlines() if "约束与验收" not in ln)
        with self.assertRaisesRegex(ValueError, "acceptance"):
            card_sections(op)

    def test_constraint_drift_between_carriers_is_rejected(self):
        sources = Sources()
        library = json.loads(sources.texts["R03"])
        library["operations"][0]["content_markdown"] = library["operations"][0]["content_markdown"].replace("不能判定整段理解", "可以判定整段理解")
        sources.texts["R03"] = json.dumps(library, ensure_ascii=False)
        with self.assertRaisesRegex(ValueError, "body mismatch"):
            parse_cards(sources)

    def test_citation_normalization_does_not_normalize_substantive_constraints(self):
        self.assertEqual(normalize_citations("证据DI01/02/03"), "证据DI01、DI02、DI03")
        self.assertEqual(normalize_citations("OS01–03"), "OS01、OS02、OS03")
        self.assertNotEqual(normalize_citations("不要求独立解释。"), normalize_citations("要求独立解释。"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
