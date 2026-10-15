"""Complete obligations, literal evidence boundaries and source-bound runtime views."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "src"))
sys.path.insert(0, str(SUITE / "scripts"))
from build_b3c_resources import Sources, build_files, json_bytes
from coordinator.delivery import bounded_output, verify_delivery
from runtime.learning_strategies import StrategyCatalog
from runtime.strategy_layers import DIRECT, compile_contract, digest, pointer_value
from read_learning_resource import layer_document, layer_payload, shared_layer_payload, strategy_document


class RuntimeLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(dir=SUITE / "tests", prefix="strategy-layer-test-")
        cls.root = Path(cls.temporary.name)
        cls.files = build_files()
        for name, raw in cls.files.items():
            p = cls.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
        cls.catalog = StrategyCatalog(cls.root)
        cls.texts = Sources().texts

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_every_direct_obligation_and_source_field_is_accounted_for_in_all_64(self):
        entries = self.catalog.index()["entries"]
        self.assertEqual(len(entries), 64)
        for entry in entries:
            with self.subTest(key=entry["resource_key"]):
                original = self.catalog.load(entry["resource_key"])["resource"]
                loaded = self.catalog.load_runtime(entry["resource_key"])
                self.assertEqual(loaded["status"], "ok", loaded)
                contract = loaded["runtime"]
                self.assertEqual(set(contract["field_disposition"]), {"/" + k for k in original})
                for key in DIRECT & original.keys():
                    self.assertEqual(contract["mandatory"][key], original[key])
                self.assertFalse(contract["mandatory"]["review_status"]["external_references_verified"])
                self.assertFalse(loaded["executable"])

    def test_full_card_and_shared_rules_preserved_including_noncontiguous_examples(self):
        for entry in self.catalog.index()["entries"]:
            if not entry["resource_key"].startswith("encoding/"): continue
            original = self.catalog.load(entry["resource_key"])["resource"]
            mandatory = self.catalog.load_runtime(entry["resource_key"])["runtime"]["mandatory"]
            body = original["full_carriers"]["R03"]["content_markdown"]
            self.assertEqual(mandatory["canonical_card_body"], body)
            for key, value in original["source_body_sections"].items():
                self.assertTrue(value.strip() in body or mandatory["additional_card_sections"][key] == value)
            for key in ("opening", "closing"):
                self.assertEqual(mandatory["common_rules"][key], original["common_rules"][key]["content_markdown"])
            self.assertEqual(mandatory["common_rules"]["governing_overrides"], original["common_rules"]["governing_overrides"])

    def test_post_mixed_passages_and_all_research_narrative_remain_literal(self):
        for entry in self.catalog.index()["entries"]:
            if not entry["resource_key"].startswith("post/"): continue
            original = self.catalog.load(entry["resource_key"])["resource"]
            contract = self.catalog.load_runtime(entry["resource_key"])["runtime"]
            self.assertEqual([p["text"] for p in contract["mandatory"]["source_passages"]],
                             [p["content_markdown"] for p in original["source_excerpts"]])
            for span, evidence in zip(contract["evidence_spans"], contract["mandatory"]["evidence_boundaries"]):
                text = pointer_value(original, span["pointer"])
                self.assertEqual(evidence["study_and_limits"], text[span["mandatory_start"]:span["end"]])
                self.assertFalse(evidence["externally_reverified_in_b3c"])

    def test_table_fields_keep_original_column_roles_and_every_nonbibliographic_cell(self):
        for entry in self.catalog.index()["entries"]:
            if not entry["resource_key"].startswith("encoding/"): continue
            original = self.catalog.load(entry["resource_key"])["resource"]
            contract = self.catalog.load_runtime(entry["resource_key"])["runtime"]
            for i, evidence in enumerate(contract["mandatory"]["evidence_boundaries"]):
                text = original["research_excerpts"][i]["content_markdown"]
                span = contract["evidence_spans"][i]
                values = [x["value"] for x in evidence["grade_population_outcome_limits"]]
                if span["mandatory_start"] == 0: self.assertEqual(values, [text])
                else:
                    self.assertEqual(values, text.split("|")[3:-1])
                    self.assertTrue(all(x["role"] for x in evidence["grade_population_outcome_limits"]))
        u02 = next(e for e in self.catalog.load_runtime("encoding/I04")["runtime"]["mandatory"]["evidence_boundaries"] if e["evidence_id"] == "U02")
        self.assertEqual(u02["grade_population_outcome_limits"][-1]["role"], "不能据此宣称")

    def test_unknown_fields_missing_obligations_or_carrier_conflicts_block_compilation(self):
        original = self.catalog.load("encoding/S05")["resource"]
        changed = deepcopy(original); changed["new_required_constraint"] = "must not disappear"
        with self.assertRaisesRegex(ValueError, "unknown_strategy_field"):
            compile_contract(changed, bundle_path="encoding/S05.json", bundle_sha256="0" * 64, source_texts=self.texts)
        changed = deepcopy(original); changed.pop("time_constraints")
        with self.assertRaisesRegex(ValueError, "incomplete_runtime_obligations"):
            compile_contract(changed, bundle_path="encoding/S05.json", bundle_sha256="0" * 64, source_texts=self.texts)
        changed = deepcopy(original)
        carrier = changed["full_carriers"]["R02"]
        carrier["content_markdown"] += "新增实质规则。"
        carrier["body_sha256"] = digest(carrier["content_markdown"].encode())
        with self.assertRaisesRegex(ValueError, "carrier_substantive_conflict"):
            compile_contract(changed, bundle_path="encoding/S05.json", bundle_sha256="0" * 64, source_texts=self.texts)

    def test_r09_h_empty_evidence_time_and_help_boundaries_are_not_promoted(self):
        m = self.catalog.load_runtime("encoding/R09")["runtime"]["mandatory"]
        self.assertEqual(m["evidence_ids"], [])
        self.assertFalse(m["original_claim_status"]["per_template_experimentally_verified"])
        self.assertFalse(m["time_constraints"]["fixed_retrieval_first"])
        self.assertIsNone(m["time_constraints"]["fixed_spacing_interval"])
        self.assertTrue(any("用户请求" in x for x in m["help_and_feedback_constraints"]))
        self.assertTrue(any("未知接触" in x for x in m["evidence_limits"]))

    def test_shared_display_is_reversible_without_losing_types_or_constraints(self):
        paths = [self.root / p for p in ("encoding/S05.json", "encoding/R04.json", "post/retrieve-relation.json", "post/select-method.json")]
        original, _ = layer_payload(paths)
        mapped, blocks = shared_layer_payload(original)
        def restore(value):
            if isinstance(value, dict):
                if set(value) == {"$shared"}: return restore(blocks[value["$shared"]]["value"])
                return {k: restore(v) for k, v in value.items()}
            if isinstance(value, list): return [restore(v) for v in value]
            return value
        self.assertEqual(restore(mapped), original)
        full, _ = strategy_document(paths); runtime, _ = layer_document(paths)
        self.assertLess(len(runtime), len(full))

    def test_original_research_expansion_is_exact_and_requires_an_explicit_section(self):
        path = self.root / "post/select-method.json"
        original = self.catalog.load("post/select-method")["resource"]
        expanded, _ = layer_payload([path], research_sections=["/evidence_refs/0"])
        self.assertEqual(expanded[0]["original_value"], original["evidence_refs"][0])
        prefix = [sys.executable, "-B", str(SUITE / "scripts/read_learning_resource.py"), "--file", str(path), "--view", "strategy-research", "--format", "json"]
        process = subprocess.run(prefix, capture_output=True, timeout=20)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(verify_delivery(process.stdout)["problem"], "one_archive_and_explicit_sections_required")
        process = subprocess.run(prefix + ["--section", "/evidence_refs/9999"], capture_output=True, timeout=20)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(verify_delivery(process.stdout)["status"], "rejected")

    def test_rehashing_a_truncated_contract_in_manifest_does_not_bypass_rederivation(self):
        path = self.root / "runtime/post/select-method.json"
        manifest_path = self.root / "manifest.json"
        before, before_manifest = path.read_bytes(), manifest_path.read_bytes()
        try:
            altered = json.loads(before); altered["mandatory"]["source_passages"].pop()
            path.write_bytes(json_bytes(altered))
            manifest = json.loads(before_manifest)
            for item in manifest["resources"]:
                if item["path"] == "runtime/post/select-method.json": item["sha256"] = digest(path.read_bytes())
            manifest_path.write_bytes(json_bytes(manifest))
            self.assertEqual(self.catalog.load_runtime("post/select-method")["status"], "blocked")
        finally:
            path.write_bytes(before); manifest_path.write_bytes(before_manifest)


if __name__ == "__main__":
    unittest.main()
