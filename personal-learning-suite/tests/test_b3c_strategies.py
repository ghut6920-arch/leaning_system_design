"""Observable B3c behavior on isolated, developer-made records and resources.

These checks exercise resource availability, declared compatibility and shared
record controls. They do not certify research, discipline truth or learning.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from runtime.learning_store import LearningStore
from runtime.learning_strategies import BINDING_FIELDS, StrategyCatalog, StrategiesService
from test_b2b_materials import fixture as material_fixture


def fact(status, value=None, reason="Artificial fixture; condition not observed."):
    return {"status": status, "value": value} if status == "known" else {"status": status, "reason": reason}


def ref(obj):
    return {"id": obj["id"], "revision": obj["revision"]}


def by_id(context):
    return {obj["id"]: obj for obj in context["objects"]}


def fixture():
    """Construct a separate AG1 strategy grant and accepted local work order."""
    snapshot, artifacts, _, _ = material_fixture()
    snapshot["synthetic_only"] = True
    snapshot["fixture_id"] = "B3c-synthetic-strategies"
    objects = by_id(snapshot)
    grant = copy.deepcopy(objects["FIX-user-grant"])
    grant.update(
        id="FIX-b3c-grant", grantee="AG1", decision_types=["strategy_configuration", "teaching_design"],
        permitted_conclusions=["Artificial conditional method configuration"], validity="Isolated B3c fixture run",
    )
    order = copy.deepcopy(objects["FIX-work-order"])
    order.update(
        id="FIX-b3c-work", operation_id="FIX-b3c-work-operation", assignee="AG1",
        decision_needed="Check the declared method configuration for the same local work",
        decision_type="strategy_configuration", scope="Artificial local reasoning work", output_contract="MethodConfig",
        authorization_refs=[ref(grant)], current_restrictions=[], event_refs=[],
        material_refs=[ref(objects["FIX-material"])], basis_revisions=[ref(objects["FIX-content-source"])],
        acceptance={"status": "accepted", "by": "AG1", "scope": "Artificial conditional configuration", "next_trigger": "New declared condition"},
        next_trigger="Explicit fixture request",
    )
    snapshot["objects"].extend([grant, order])
    return snapshot, artifacts


def configured(catalog, keys=("encoding/S07", "encoding/X02")):
    """Reviewable declarations, not generated learner facts or verified truth."""
    context = {
        "synthetic_only": True, "intended_work": "Complete the same local reasoning connection",
        "goal_refs": [{"id": "FIX-goal", "revision": 1}],
        "activity_ref": {"id": "FIX-activity", "revision": 1},
        "material_refs": [{"id": "FIX-material", "revision": 1}],
        "purpose": "teaching", "conditions": ["Artificial given premises; learner supplies the connection"],
        "allowed_resources": ["题面给定前提"], "budget_ref": {"id": "FIX-budget", "revision": 1},
        "requires_time_condition": False, "selection_needed": True,
        "existing_activity_reliable": fact("known", True),
        "material_context": copy.deepcopy(material_fixture()[3]),
    }
    packages = {}
    for key in keys:
        loaded = catalog.load(key)
        if loaded.get("status") != "ok":
            raise AssertionError(f"Fixture resource unavailable: {key}: {loaded}")
        packages[key] = loaded["resource"]
    sources = []
    for package in packages.values():
        for source in package["source_refs"]:
            if source not in sources:
                sources.append(copy.deepcopy(source))
    binding_fields = BINDING_FIELDS
    basis = context["goal_refs"] + context["material_refs"] + [context["activity_ref"], context["budget_ref"], {"id": "FIX-b3c-work", "revision": 1}]
    config = {
        "type": "MethodConfig", "id": "FIX-strategy", "revision": 1, "owner": "AG1",
        "schema_version": "pl-contracts/0.1.0", "basis_refs": copy.deepcopy(basis),
        "intended_work": context["intended_work"], "source_refs": sources, "resource_revision": "pl-strategies/0.1.0",
        "selected_parts": [{"resource_key": key, "resource_revision": "pl-strategies/0.1.0", "borrowed_parts": ["Preserve learner reasoning and conditional support"], "omitted_parts": ["Training beyond the current goal"], "non_equivalence": "Supported work does not establish unsupported independent work"} for key in keys],
        "prerequisites": [{"condition": "Reliable given premises are available", "check": fact("known", True)}],
        "exclusions": [{"condition": "No reliable correction can be delivered", "check": fact("known", False)}],
        "required_learner_operations": ["connect-P-to-Q"],
        "help_and_feedback_constraints": {"feedback": fact("known", True), "allowed_resources": copy.deepcopy(context["allowed_resources"]), "provided_operations": [], "exposure": fact("unknown"), "contact_history": fact("unknown"), "time_condition": fact("unknown")},
        "adjustable_parts": ["Change presentation while preserving the required connection"],
        "combination_and_non_equivalence": {"rationale": "The two sources address one local connection", "interference_check": fact("known", True), "single_performance": True, "alternatives": []},
        "cost": {**{phase: fact("unknown") for phase in ("preparation", "execution", "feedback", "verification", "closure")}, "budget_fit": fact("known", True)},
        "interruptibility": fact("known", "Retain the same parent artifact and return point"),
        "stop_or_return_conditions": ["Return when the local connection is sufficient; stop at the authorized budget"],
        "evidence_limits": {"resource_limits": {key: copy.deepcopy(package["evidence_limits"]) for key, package in packages.items()}, "config_limits": ["Artificial declarations do not verify effects, content truth or real exposure"]},
        "original_claim_status": {key: copy.deepcopy(package["original_claim_status"]) for key, package in packages.items()},
        "local_adaptations": [], "review_status": {"status": "reviewed", "reviewer": "AG1", "binding": {field: copy.deepcopy(context[field]) for field in binding_fields}},
        "reuse_limits": ["Recheck changed goal, material, help, source version and authorized resources"],
        "previous_config": None,
        "resource_checks": {key: {condition["key"]: fact("known", condition.get("scope") != "exclusion") for condition in package["conditions"]} for key, package in packages.items()},
        "adoption": {"status": "adopted", "by": "AG1", "scope": "Artificial local configuration", "basis_refs": [{"id": "FIX-b3c-work", "revision": 1}], "limitations": ["Fixture actor, not authenticated host"], "time": fact("not_executed")},
    }
    return config, context


class B3cCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pl-b3c-resources-")
        self.addCleanup(self.temp.cleanup)
        self.catalog = StrategyCatalog()

    def entries(self):
        result = self.catalog.index()
        self.assertEqual(result["status"], "ok", result)
        return result["entries"]

    def copied_catalog(self):
        destination = Path(self.temp.name) / "strategies"
        shutil.copytree(ROOT / "resources/strategies", destination)
        return StrategyCatalog(resource_root=destination, project_root=ROOT.parent), destination

    def test_index_keeps_sixty_distinct_original_encoding_ids_and_all_packets(self):
        entries = self.entries()
        encoding = [entry for entry in entries if entry["resource_key"].startswith("encoding/")]
        self.assertEqual({entry["resource_key"].split("/")[1] for entry in encoding}, {f"{prefix}{number:02d}" for prefix in "OSRDIX" for number in range(1, 11)})
        self.assertEqual(len(encoding), 60)
        self.assertEqual({entry["resource_key"] for entry in encoding if entry["compiled"]}, {entry["resource_key"] for entry in encoding})
        self.assertTrue(all(entry["bundle_path"] and entry["intended_work"] for entry in encoding))
        self.assertTrue(all("content_markdown" not in entry for entry in encoding))

    def test_formerly_uncompiled_entry_is_readable_but_not_automatically_executable(self):
        result = self.catalog.load("encoding/O01")
        self.assertEqual(result["status"], "ok", result)
        self.assertIn("resource", result)
        self.assertFalse(result["executable"])
        self.assertEqual(self.catalog.load("E29")["status"], "blocked")

    def test_all_compiled_packets_include_full_body_common_rules_source_and_conditions(self):
        for key in (entry["resource_key"] for entry in self.entries() if entry["resource_key"].startswith("encoding/")):
            with self.subTest(key=key):
                result = self.catalog.load(key)
                self.assertEqual(result["status"], "ok", result)
                packet = result["resource"]
                self.assertTrue(packet["conditions"])
                self.assertTrue(packet["source_refs"])
                self.assertTrue(packet["full_carriers"])
                self.assertTrue(packet["common_rules"]["opening"])
                self.assertTrue(packet["common_rules"]["closing"])
                self.assertTrue(packet["source_body_sections"]["acceptance"])
                self.assertEqual(set(packet["evidence_ids"]), {x["evidence_id"] for x in packet["evidence_refs"]})

    def test_r09_empty_evidence_stays_empty_and_design_template_is_not_experimental_proof(self):
        result = self.catalog.load("encoding/R09")
        self.assertEqual(result["status"], "ok", result)
        packet = result["resource"]
        self.assertEqual(packet["evidence_ids"], [])
        self.assertEqual(packet["evidence_refs"], [])
        self.assertTrue(packet["original_claim_status"]["status"].startswith("H"))
        self.assertFalse(packet["original_claim_status"]["per_template_experimentally_verified"])
        self.assertFalse(packet["review_status"]["external_references_verified"])
        self.assertTrue(packet["evidence_limits"])

    def test_missing_and_modified_packet_bytes_cannot_remain_available(self):
        catalog, destination = self.copied_catalog()
        packet_path = destination / "encoding/S07.json"
        packet_path.unlink()
        self.assertEqual(catalog.load("encoding/S07")["status"], "blocked")
        shutil.copy2(ROOT / "resources/strategies/encoding/S07.json", packet_path)
        with packet_path.open("a", encoding="utf-8") as output:
            output.write("\n ")
        self.assertEqual(catalog.load("encoding/S07")["status"], "blocked")

    def test_unknown_post_literature_or_coverage_ids_cannot_be_promoted_to_resource_keys(self):
        for key in ("E01", "E29", "E49", "P1", "P01", "post/E29"):
            with self.subTest(key=key):
                self.assertEqual(self.catalog.load(key)["status"], "blocked")
        for key in ("post/retrieve-relation", "post/select-method", "post/conditional-update", "post/retrieve-generate-order"):
            with self.subTest(key=key):
                result = self.catalog.load(key)
                self.assertEqual(result["status"], "ok", result)
                self.assertTrue(result["resource"]["source_refs"])

    def test_changed_source_bytes_in_a_separate_project_root_block_derived_resources(self):
        catalog, resources = self.copied_catalog()
        project = Path(self.temp.name) / "source-project"
        manifest = json.loads((resources / "manifest.json").read_text(encoding="utf-8-sig"))
        for source in manifest["source_fingerprints"]:
            relative = source["workspace_relative_path"]
            destination = project / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT.parent / relative, destination)
        catalog = StrategyCatalog(resource_root=resources, project_root=project)
        self.assertEqual(catalog.load("encoding/S07")["status"], "ok")
        source_path = project / manifest["source_fingerprints"][0]["workspace_relative_path"]
        with source_path.open("ab") as output:
            output.write(b"\nSOURCE-VERSION-CHANGE\n")
        self.assertEqual(catalog.load("encoding/S07")["status"], "blocked")

    def test_two_body_carriers_preserve_one_set_of_original_evidence_references(self):
        for key in ("encoding/S07", "encoding/X02"):
            with self.subTest(key=key):
                packet = self.catalog.load(key)["resource"]
                self.assertEqual(set(packet["full_carriers"]), {"R02", "R03"})
                ids = [entry["evidence_id"] for entry in packet["evidence_refs"]]
                self.assertEqual(set(ids), set(packet["evidence_ids"]))
                self.assertEqual(len(ids), len(set(ids)))
                self.assertTrue(all(not entry["externally_reverified_in_b3c"] for entry in packet["evidence_refs"]))

    def test_reproducible_resource_check_runs_from_another_cwd_without_rewriting_resources(self):
        before = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT / "resources/strategies").rglob("*") if path.is_file()}
        completed = subprocess.run([sys.executable, str(ROOT / "scripts/build_b3c_resources.py"), "--check"], cwd=self.temp.name, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertTrue(result["passed"])
        self.assertEqual(result["mode"], "check")
        self.assertFalse(result["external_references_verified"])
        after = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT / "resources/strategies").rglob("*") if path.is_file()}
        self.assertEqual(before, after)


class B3cConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pl-b3c-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace"
        self.snapshot, self.artifacts = fixture()
        self.store = LearningStore(self.root, entry_actor="AG1")
        self.assertEqual(self.store.init_workspace()["status"], "committed")
        seeded = self.store.import_fixture(self.snapshot, self.artifacts)
        self.assertEqual(seeded["status"], "committed", seeded)
        self.catalog = StrategyCatalog()
        self.service = StrategiesService(self.store, self.catalog)
        self.config, self.context = configured(self.catalog)

    def state(self):
        result = self.store.read_context()
        self.assertEqual(result["status"], "ok", result)
        return result

    def revision(self):
        return self.state()["state_revision"]

    def inspect(self, config=None, context=None):
        return self.service.inspect_config(config if config is not None else self.config, context if context is not None else self.context)

    def rebind(self, config, context):
        config["intended_work"] = context["intended_work"]
        config["help_and_feedback_constraints"]["allowed_resources"] = copy.deepcopy(context["allowed_resources"])
        for field in config["review_status"]["binding"]:
            config["review_status"]["binding"][field] = copy.deepcopy(context[field])

    def independent_declarations(self, config=None, context=None):
        config, context = copy.deepcopy(config or self.config), copy.deepcopy(context or self.context)
        context["purpose"] = "independent"
        config["help_and_feedback_constraints"]["exposure"] = fact("known", "Artificial declaration: only permitted premises before the answer")
        config["help_and_feedback_constraints"]["contact_history"] = fact("known", "Artificial declared prior contact; not an actual temporal qualification")
        self.rebind(config, context)
        return config, context

    def time_service(self, requirement_ids, name="time-required"):
        snapshot = copy.deepcopy(self.snapshot)
        by_id(snapshot)["FIX-goal"]["time_requirements"] = fact("known", {
            "requirement_ids": requirement_ids, "minimum_delay_seconds": 86400, "require_no_contact": False,
        })
        store = LearningStore(Path(self.temp.name) / name, entry_actor="AG1")
        self.assertEqual(store.init_workspace()["status"], "committed")
        self.assertEqual(store.import_fixture(snapshot, self.artifacts)["status"], "committed")
        return StrategiesService(store, self.catalog), store

    def submission(self, operation="FIX-b3c-submit", config=None):
        return {"expected_state_revision": self.revision(), "operation_id": operation,
                "changes": [copy.deepcopy(config if config is not None else self.config)], "context": copy.deepcopy(self.context),
                "authorization_refs": [{"id": "FIX-b3c-grant", "revision": 1}], "adoption_refs": [{"id": "FIX-b3c-work", "revision": 1}]}

    def assert_limited_without_write(self, config, context=None):
        before = self.state()
        result = self.inspect(config, context)
        self.assertIn(result["status"], {"limited", "blocked", "rejected"}, result)
        self.assertFalse(result["mutated"])
        self.assertTrue(result["reasons"], result)
        self.assertEqual(before, self.state())

    def test_reliable_activity_short_path_does_not_read_catalog_or_add_work(self):
        class UnavailableCatalog:
            def index(self, *args):
                raise AssertionError("Reliable activity must not browse a strategy index")
            def load(self, *args):
                raise AssertionError("Reliable activity must not load a new strategy")
        before = self.state()
        context = copy.deepcopy(self.context)
        context["selection_needed"] = False
        result = StrategiesService(self.store, UnavailableCatalog()).inspect_config(None, context)
        self.assertEqual(result["status"], "direct_reuse", result)
        self.assertFalse(result["catalog_loaded"])
        self.assertFalse(result["teaching_started"])
        self.assertEqual(result["new_performance_events"], 0)
        self.assertEqual(before, self.state())

    def test_same_connection_two_cards_form_one_config_without_performance_or_plan_mutation(self):
        before = self.state()
        result = self.inspect()
        self.assertEqual(result["status"], "compatible", result)
        self.assertFalse(result["adopted"])
        self.assertEqual(result["new_performance_events"], 0)
        self.assertFalse(result["plan_changed"])
        self.assertEqual(before, self.state())
        saved = self.service.submit_config(self.submission())
        self.assertEqual(saved["status"], "committed", saved)
        after = self.state()
        for kind in ("PerformanceEvent", "Judgment", "LearningNeed", "PlanCommitment"):
            self.assertEqual([obj for obj in before["objects"] if obj["type"] == kind], [obj for obj in after["objects"] if obj["type"] == kind])
        self.assertEqual(len(after["objects"]), len(before["objects"]) + 1)

    def test_changed_choice_without_its_resource_checks_cannot_pass_config_compatibility(self):
        config = copy.deepcopy(self.config)
        config["selected_parts"][0]["resource_key"] = "encoding/O01"
        self.assert_limited_without_write(config)

    def test_needed_resource_condition_unknown_and_active_exclusion_limit_the_configuration(self):
        packet = self.catalog.load("encoding/S07")["resource"]
        required = next(condition for condition in packet["conditions"] if "teaching" in condition["required_for"] and condition.get("scope") != "exclusion")
        config = copy.deepcopy(self.config)
        config["resource_checks"]["encoding/S07"][required["key"]] = fact("unknown")
        self.assert_limited_without_write(config)
        config = copy.deepcopy(self.config)
        config["exclusions"][0]["check"] = fact("known", True)
        self.assert_limited_without_write(config)

    def test_feedback_and_total_budget_are_gates_while_unmeasured_costs_stay_unknown(self):
        self.assertEqual(self.inspect()["status"], "compatible")
        for phase in ("preparation", "execution", "feedback", "verification", "closure"):
            self.assertEqual(self.config["cost"][phase]["status"], "unknown")
        for field in ("feedback", "budget_fit"):
            with self.subTest(field=field):
                config = copy.deepcopy(self.config)
                target = config["help_and_feedback_constraints"] if field == "feedback" else config["cost"]
                target[field] = fact("known", False)
                self.assert_limited_without_write(config)

    def test_title_or_help_that_supplies_target_operation_limits_independent_use(self):
        config, context = copy.deepcopy(self.config), copy.deepcopy(self.context)
        context["purpose"] = "independent"
        config["help_and_feedback_constraints"]["exposure"] = fact("known", {"operation": "connect-P-to-Q", "channel": "title"})
        config["help_and_feedback_constraints"]["contact_history"] = fact("known", "Declared actual prior contact")
        config["help_and_feedback_constraints"]["provided_operations"] = ["connect-P-to-Q"]
        self.rebind(config, context)
        self.assert_limited_without_write(config, context)

    def test_independent_use_does_not_convert_unknown_exposure_and_contact_into_no_help(self):
        config, context = copy.deepcopy(self.config), copy.deepcopy(self.context)
        context["purpose"] = "independent"
        self.rebind(config, context)
        self.assert_limited_without_write(config, context)
        self.assertEqual(config["help_and_feedback_constraints"]["exposure"]["status"], "unknown")

    def test_post_allowed_reference_and_unknown_time_do_not_force_retrieval_or_generate_schedule(self):
        config, context = configured(self.catalog, ("post/retrieve-generate-order",))
        config["selected_parts"][0]["borrowed_parts"] = ["Use permitted reference before integration when independent retrieval is not required"]
        self.rebind(config, context)
        before = self.state()
        result = self.inspect(config, context)
        self.assertEqual(result["status"], "compatible", result)
        self.assertEqual(config["help_and_feedback_constraints"]["time_condition"]["status"], "unknown")
        self.assertFalse(result["plan_changed"])
        self.assertEqual(before, self.state())
        context["requires_time_condition"] = True
        self.rebind(config, context)
        self.assert_limited_without_write(config, context)

    def test_r09_remains_a_valid_design_candidate_without_inventing_research_ids(self):
        config, context = configured(self.catalog, ("encoding/R09",))
        result = self.inspect(config, context)
        self.assertEqual(result["status"], "compatible", result)
        self.assertTrue(config["original_claim_status"]["encoding/R09"]["status"].startswith("H"))
        self.assertFalse(config["original_claim_status"]["encoding/R09"]["per_template_experimentally_verified"])
        self.assertEqual(self.catalog.load("encoding/R09")["resource"]["evidence_ids"], [])
        self.assertFalse(result["adopted"])

    def test_source_version_and_evidence_limits_cannot_be_silently_replaced(self):
        config = copy.deepcopy(self.config)
        config["source_refs"][0]["declared_revision"] = "fictional/newer-version"
        self.assert_limited_without_write(config)
        config = copy.deepcopy(self.config)
        config["evidence_limits"]["resource_limits"] = {}
        self.assert_limited_without_write(config)

    def test_r09_cannot_acquire_an_invented_paper_source_through_config_metadata(self):
        config, context = configured(self.catalog, ("encoding/R09",))
        config["source_refs"].append({"source_id": "FAKE-PAPER", "declared_revision": "invented/1", "identity_kind": "literature_entry", "locator": "PRIVATE-FAKE-RESEARCH-MARKER"})
        before = self.state()
        result = self.inspect(config, context)
        self.assertIn(result["status"], {"limited", "rejected"}, result)
        self.assertFalse(result["mutated"])
        self.assertTrue(result["reasons"])
        self.assertNotIn("PRIVATE-FAKE-RESEARCH-MARKER", json.dumps(result))
        self.assertEqual(before, self.state())

    def test_review_is_not_adoption_and_wrong_responsible_adopter_is_rejected(self):
        for adoption in (None, {"status": "candidate", "by": "AG1", "basis_refs": [{"id": "FIX-b3c-work", "revision": 1}]}, {"status": "adopted", "by": "AG0", "basis_refs": [{"id": "FIX-b3c-work", "revision": 1}]}):
            with self.subTest(adoption=adoption):
                config = copy.deepcopy(self.config)
                if adoption is None:
                    config.pop("adoption")
                else:
                    config["adoption"] = adoption
                self.assertEqual(self.inspect(config)["status"], "compatible")
                result = self.service.submit_config(self.submission(config=config))
                self.assertEqual(result["status"], "rejected", result)
                self.assertNotIn("FIX-strategy", by_id(self.state()))

    def test_grant_and_adoption_receipts_are_explicit_and_ag0_cannot_write_method_config(self):
        for field in ("authorization_refs", "adoption_refs"):
            with self.subTest(field=field):
                request = self.submission("FIX-missing-" + field)
                request[field] = []
                self.assertEqual(self.service.submit_config(request)["status"], "rejected")
                self.assertEqual(self.revision(), 1)
        other = StrategiesService(LearningStore(self.root, entry_actor="AG0"), self.catalog)
        self.assertEqual(other.submit_config(self.submission())["status"], "rejected")
        request = self.submission()
        request["authorization_refs"] = [{"id": "FIX-evidence-grant", "revision": 1}]
        self.assertEqual(self.service.submit_config(request)["status"], "rejected")

    def test_cas_does_not_replace_a_newer_state(self):
        request = self.submission()
        self.assertEqual(self.store.pause(1, "FIX-b3c-unrelated-pause", ["FIX-method"], "Artificial unrelated scope")["status"], "committed")
        result = self.service.submit_config(request)
        self.assertEqual(result["status"], "conflict", result)
        self.assertNotIn("FIX-strategy", by_id(self.state()))

    def test_same_operation_is_idempotent_changed_payload_rejected_and_reopen_preserves_config(self):
        request = self.submission()
        first = self.service.submit_config(request)
        self.assertEqual(first["status"], "committed", first)
        self.assertEqual(self.service.submit_config(copy.deepcopy(request)), first)
        changed = copy.deepcopy(request)
        changed["changes"][0]["local_adaptations"].append("CHANGED-RETRY-PAYLOAD")
        self.assertEqual(self.service.submit_config(changed)["status"], "rejected")
        reopened = LearningStore(self.root, entry_actor="AG1")
        self.assertEqual(by_id(reopened.read_context())["FIX-strategy"], self.config)
        self.assertEqual(reopened.check_integrity()["status"], "ok")

    def test_current_scope_restriction_precedes_old_success_and_user_resume_does_not_restore_use(self):
        request = self.submission()
        self.assertEqual(self.service.submit_config(request)["status"], "committed")
        control = self.store.restrict(self.revision(), "FIX-b3c-source-restrict", ["FIX-content-source"], "Artificial material recheck", ["strategy_configuration"])
        self.assertEqual(control["status"], "committed", control)
        self.assertEqual(self.inspect()["status"], "blocked")
        self.assertEqual(self.service.submit_config(request)["status"], "rejected")
        self.assertEqual(self.store.resume(self.revision(), "FIX-b3c-resume", ["FIX-content-source"])["status"], "committed")
        self.assertEqual(self.inspect()["status"], "blocked")

    def test_pause_blocks_current_configuration_and_direct_reuse(self):
        self.assertEqual(self.store.pause(self.revision(), "FIX-b3c-pause", ["FIX-activity"], "Artificial pause")["status"], "committed")
        self.assertEqual(self.inspect()["status"], "blocked")
        context = copy.deepcopy(self.context)
        context["selection_needed"] = False
        self.assertEqual(self.service.inspect_config(None, context)["status"], "blocked")

    def test_delete_late_result_cannot_restore_personal_config_and_generic_resources_are_unchanged(self):
        resource_bytes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT / "resources/strategies").rglob("*.json")}
        request = self.submission()
        self.assertEqual(self.service.submit_config(request)["status"], "committed")
        deleted = self.store.delete_scope(self.revision(), "FIX-b3c-delete", ["FIX-content-source"])
        self.assertEqual(deleted["status"], "committed", deleted)
        request["expected_state_revision"] = self.revision()
        self.assertEqual(self.service.submit_config(request)["status"], "rejected")
        self.assertNotIn("FIX-strategy", by_id(self.state()))
        self.assertNotIn("FIX-content-source", by_id(self.state()))
        self.assertEqual(resource_bytes, {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT / "resources/strategies").rglob("*.json")})
        self.assertEqual(self.catalog.load("encoding/S07")["status"], "ok")

    def test_method_revision_preserves_historical_config_and_original_events(self):
        self.assertEqual(self.service.submit_config(self.submission())["status"], "committed")
        before = self.state()
        second = copy.deepcopy(self.config)
        second.update(revision=2, previous_config=ref(self.config))
        second["local_adaptations"] = ["Different wording with the same required connection"]
        result = self.service.submit_config(self.submission("FIX-b3c-second-revision", second))
        self.assertEqual(result["status"], "committed", result)
        history = self.store.read_refs([ref(self.config)], "read")
        self.assertEqual(history["status"], "ok")
        self.assertEqual(history["objects"], [self.config])
        self.assertEqual(by_id(before)["FIX-event"], by_id(self.state())["FIX-event"])
        self.assertEqual(by_id(self.state())["FIX-strategy"]["revision"], 2)

    def test_reuse_requires_current_adopted_config_and_keeps_legitimate_previous_revision_readable(self):
        before = self.state()
        self.assertEqual(self.service.reuse_config({"id": "FIX-method", "revision": 1}, self.context)["status"], "blocked")
        self.assertEqual(before, self.state())

    def test_adoption_requires_scope_limits_and_time_and_respects_declared_scope(self):
        for field in ("scope", "limitations", "time"):
            with self.subTest(field=field):
                config = copy.deepcopy(self.config)
                del config["adoption"][field]
                result = self.service.submit_config(self.submission(config=config))
                self.assertEqual(result["status"], "rejected", result)
        config = copy.deepcopy(self.config)
        config["adoption"]["scope"] = {"purpose": "independent"}
        self.assertEqual(self.service.submit_config(self.submission(config=config))["status"], "rejected")

    def test_old_review_binding_is_preserved_but_cannot_approve_current_reuse(self):
        config = copy.deepcopy(self.config)
        del config["review_status"]["binding"]["material_context"]
        result = self.inspect(config)
        self.assertNotEqual(result["status"], "compatible", result)
        self.assertNotIn("material_context", config["review_status"]["binding"])

    def test_independent_method_requires_material_review_for_independent_use(self):
        snapshot = copy.deepcopy(self.snapshot)
        material = by_id(snapshot)["FIX-material"]
        material["verification"]["use"]["binding"]["purpose"] = "teaching"
        store = LearningStore(Path(self.temp.name) / "teaching-material", entry_actor="AG1")
        self.assertEqual(store.init_workspace()["status"], "committed")
        self.assertEqual(store.import_fixture(snapshot, self.artifacts)["status"], "committed")
        config, context = self.independent_declarations()
        context["material_context"]["purpose"] = "teaching"
        self.rebind(config, context)
        result = StrategiesService(store, self.catalog).inspect_config(config, context)
        self.assertEqual(result["status"], "blocked", result)
        self.assertIn("independent_material_use_required", {p["code"] for p in result["reasons"]})
        self.assertEqual(self.service.submit_config(self.submission())["status"], "committed")
        result = self.service.reuse_config(ref(self.config), self.context)
        self.assertEqual(result["status"], "reusable", result)
        self.assertFalse(result["mutated"])
        self.assertFalse(result["teaching_started"])
        second = copy.deepcopy(self.config)
        second.update(revision=2, previous_config=ref(self.config))
        second["local_adaptations"].append("Keep history while choosing new current wording")
        self.assertEqual(self.service.submit_config(self.submission("FIX-b3c-reuse-update", second))["status"], "committed")
        before = self.state()
        latest = self.service.reuse_config(ref(second), self.context)
        self.assertEqual(latest["status"], "reusable", latest)
        self.assertFalse(latest["mutated"])
        self.assertEqual(self.service.reuse_config(ref(self.config), self.context)["status"], "blocked")
        self.assertEqual(self.store.read_refs([ref(self.config)], "read")["objects"], [self.config])
        self.assertEqual(before, self.state())

    def test_current_material_declarations_must_support_both_correctness_and_use(self):
        for number, (axis, status, checked_revision) in enumerate((("content", "pending", 1), ("use", "pending", 1), ("content", "supported", 99), ("use", "supported", 99))):
            with self.subTest(axis=axis, status=status, checked_revision=checked_revision):
                snapshot = copy.deepcopy(self.snapshot)
                material = by_id(snapshot)["FIX-material"]
                material["verification"][axis].update(status=status, checked_revision=checked_revision)
                store = LearningStore(Path(self.temp.name) / f"material-{number}", entry_actor="AG1")
                self.assertEqual(store.init_workspace()["status"], "committed")
                self.assertEqual(store.import_fixture(snapshot, self.artifacts)["status"], "committed")
                before = store.read_context()
                service = StrategiesService(store, self.catalog)
                result = service.inspect_config(self.config, self.context)
                self.assertEqual(result["status"], "blocked", result)
                context = copy.deepcopy(self.context)
                context["selection_needed"] = False
                self.assertEqual(service.inspect_config(None, context)["status"], "blocked")
                self.assertEqual(before, store.read_context())

    def test_config_may_not_expand_resources_allowed_by_current_goal(self):
        config, context = copy.deepcopy(self.config), copy.deepcopy(self.context)
        context["allowed_resources"].append("Unapproved complete worked answer")
        self.rebind(config, context)
        self.assert_limited_without_write(config, context)

    def test_independent_positive_declarations_keep_one_event_and_no_adoption_in_inspection(self):
        config, context = copy.deepcopy(self.config), copy.deepcopy(self.context)
        context["purpose"] = "independent"
        config["help_and_feedback_constraints"]["exposure"] = fact("known", "Artificial declaration: only permitted premises before the answer")
        config["help_and_feedback_constraints"]["contact_history"] = fact("known", "Artificial known prior support, not a claim of strict noncontact")
        self.rebind(config, context)
        before = self.state()
        result = self.inspect(config, context)
        self.assertEqual(result["status"], "compatible", result)
        self.assertFalse(result["adopted"])
        self.assertEqual(result["new_performance_events"], 0)
        self.assertEqual(before, self.state())

    def test_independent_time_requirement_cannot_be_hidden_by_false_context_flag(self):
        service, store = self.time_service(["infer-Q"])
        config, context = self.independent_declarations()
        self.assertFalse(context["requires_time_condition"])
        before = store.read_context()
        result = service.inspect_config(config, context)
        self.assertIn(result["status"], {"limited", "blocked", "rejected"}, result)
        self.assertFalse(result["mutated"])
        self.assertEqual(before, store.read_context())

    def test_teaching_may_continue_before_target_time_requirement_without_creating_delayed_work(self):
        service, store = self.time_service(["infer-Q"])
        before = store.read_context()
        result = service.inspect_config(self.config, self.context)
        self.assertEqual(result["status"], "compatible", result)
        self.assertFalse(result["adopted"])
        self.assertFalse(result["plan_changed"])
        self.assertEqual(before, store.read_context())

    def test_time_requirement_on_another_criterion_does_not_become_current_activity_debt(self):
        service, store = self.time_service(["complete-chain"])
        config, context = self.independent_declarations()
        before = store.read_context()
        result = service.inspect_config(config, context)
        self.assertEqual(result["status"], "compatible", result)
        self.assertFalse(result["plan_changed"])
        self.assertEqual(before, store.read_context())

    def test_not_required_goal_time_cannot_be_replaced_by_an_extra_independent_requirement(self):
        config, context = self.independent_declarations()
        context["requires_time_condition"] = True
        config["help_and_feedback_constraints"]["time_condition"] = fact("known", True)
        self.rebind(config, context)
        self.assert_limited_without_write(config, context)

    def test_matching_required_time_declaration_is_checked_without_claiming_temporal_or_learning_verification(self):
        service, store = self.time_service(["infer-Q"])
        config, context = self.independent_declarations()
        context["requires_time_condition"] = True
        self.rebind(config, context)
        before = store.read_context()
        pending = service.inspect_config(config, context)
        self.assertIn(pending["status"], {"limited", "blocked", "rejected"}, pending)
        config["help_and_feedback_constraints"]["time_condition"] = fact("known", True)
        result = service.inspect_config(config, context)
        self.assertEqual(result["status"], "compatible", result)
        self.assertEqual(result["semantic_verification"], "declaration_checks_only")
        self.assertFalse(result["adopted"])
        self.assertEqual(before, store.read_context())

    def test_trace_is_read_only_and_recovery_remains_separate_pending_responsibilities(self):
        self.assertEqual(self.service.submit_config(self.submission())["status"], "committed")
        before = self.state()
        result = self.service.trace_change({"changed_refs": [ref(self.config)]})
        self.assertEqual(result["status"], "candidate", result)
        self.assertFalse(result["mutated"])
        self.assertFalse(result["professional_restrictions_lifted"])
        self.assertFalse(result["historical_events_rewritten"])
        self.assertEqual(result["unknown_dependencies"]["status"], "unknown")
        self.assertTrue(all(item["status"] == "pending" for item in result["recovery"].values()))
        self.assertEqual(before, self.state())

    def test_source_resource_change_finds_only_recorded_selected_uses_without_rewriting_history(self):
        self.assertEqual(self.service.submit_config(self.submission())["status"], "committed")
        before = self.state()
        result = self.service.trace_change({"resource_keys": ["encoding/S07"]})
        self.assertEqual(result["status"], "candidate", result)
        self.assertIn(ref(self.config), result["affected_refs"])
        self.assertNotIn({"id": "FIX-method", "revision": 1}, result["affected_refs"])
        self.assertEqual(before, self.state())

    def test_resource_source_revision_trace_distinguishes_matching_and_unmatched_old_versions(self):
        self.assertEqual(self.service.submit_config(self.submission())["status"], "committed")
        before = self.state()
        source = next(source for source in self.config["source_refs"] if source["source_id"] == "R03")
        matching = self.service.trace_change({"resource_changes": [{"source_id": "R03", "previous_revision": source["declared_revision"]}]})
        self.assertEqual(matching["status"], "candidate", matching)
        self.assertIn(ref(self.config), matching["affected_refs"])
        unmatched = self.service.trace_change({"resource_changes": [{"source_id": "R03", "previous_revision": "unmatched/old"}]})
        self.assertEqual(unmatched["status"], "candidate", unmatched)
        self.assertNotIn(ref(self.config), unmatched["affected_refs"])
        self.assertEqual(unmatched["unknown_dependencies"]["status"], "unknown")
        self.assertEqual(before, self.state())

    def test_restriction_is_committed_before_recovery_trace_and_remains_effective(self):
        self.assertEqual(self.service.submit_config(self.submission())["status"], "committed")
        result = self.service.restrict_change({"changed_refs": [ref(self.config)], "expected_state_revision": self.revision(), "operation_id": "FIX-b3c-change-restrict", "intended_uses": ["strategy_configuration"], "reason": "Artificial configuration mismatch"})
        self.assertEqual(result["status"], "candidate", result)
        self.assertTrue(result["mutated"])
        self.assertEqual(result["control_receipt"]["status"], "committed")
        reopened = StrategiesService(LearningStore(self.root, entry_actor="AG1"), self.catalog)
        self.assertEqual(reopened.inspect_config(self.config, self.context)["status"], "blocked")

    def test_malformed_nested_declarations_return_error_without_throwing_or_writing(self):
        invalids = []
        for field, value in (("resource_checks", None), ("source_refs", None), ("required_learner_operations", False), ("selected_parts", "title only")):
            config = copy.deepcopy(self.config)
            config[field] = value
            invalids.append(config)
        config = copy.deepcopy(self.config)
        config.pop("id")
        invalids.append(config)
        for number, config in enumerate(invalids):
            with self.subTest(number=number):
                self.assert_limited_without_write(config)

    def test_cli_invalid_payload_returns_structured_error_without_input_marker(self):
        request = Path(self.temp.name) / "invalid.json"
        request.write_text(json.dumps(["PRIVATE-INPUT-MARKER"]), encoding="utf-8")
        completed = subprocess.run([sys.executable, str(ROOT / "src/runtime/learning_strategies.py"), "inspect", "--workspace", str(self.root), "--request", str(request)], capture_output=True, text=True, encoding="utf-8")
        self.assertNotEqual(completed.returncode, 0)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "rejected")
        self.assertNotIn("PRIVATE-INPUT-MARKER", completed.stdout + completed.stderr)
        self.assertEqual(self.revision(), 1)

    def test_cli_change_restrict_persists_control_and_returns_pending_recovery(self):
        self.assertEqual(self.service.submit_config(self.submission())["status"], "committed")
        request = Path(self.temp.name) / "change.json"
        request.write_text(json.dumps({"resource_keys": ["encoding/S07"], "expected_state_revision": self.revision(), "operation_id": "FIX-b3c-cli-restrict", "intended_uses": ["strategy_configuration"], "reason": "Artificial resource mismatch"}), encoding="utf-8")
        completed = subprocess.run([sys.executable, str(ROOT / "src/runtime/learning_strategies.py"), "change", "--restrict", "--workspace", str(self.root), "--request", str(request)], cwd=self.temp.name, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "candidate", result)
        self.assertEqual(result["control_receipt"]["status"], "committed")
        self.assertTrue(result["mutated"])
        self.assertTrue(all(item["status"] == "pending" for item in result["recovery"].values()))
        service = StrategiesService(LearningStore(self.root, entry_actor="AG1"), self.catalog)
        self.assertEqual(service.reuse_config(ref(self.config), self.context)["status"], "rejected")
        self.assertEqual(self.store.read_refs([ref(self.config)], "read")["objects"], [self.config])


if __name__ == "__main__":
    unittest.main()
