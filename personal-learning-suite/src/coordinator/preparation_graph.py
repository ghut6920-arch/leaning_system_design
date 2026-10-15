"""Compile an explicit preparation request without running or adopting anything.

The request supplies the professional work. This module adds only bounded
execution, exact-task capabilities and dependencies; it never supplies a finding.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from runtime.contract_rules import load_definition

from .workspace import GateError, encode, identifier, scopes


REQUEST_FIELDS = {"workflow_id", "authorization_ref", "stages", "purpose", "report_prompt",
                  "deadline_ms", "run_timeout_ms"}
STAGE_FIELDS = {"id", "role", "output", "prompt", "scope", "use", "inputs", "after",
                "review_required", "adopt", "output_spec", "from_stage", "provisional_conditions",
                "review_after", "adopt_after", "review_purpose", "wait_ms", "run_timeout_ms"}
INPUT_FIELDS = {"artifact", "revision", "use", "scope", "after_task", "provisional_conditions"}
DEFAULT_RUN_TIMEOUT_MS = 3600000


def _text(value, code):
    if not isinstance(value, str) or not value.strip():
        raise GateError(code)
    return value


def _positive(value):
    if type(value) is not int or value <= 0:
        raise GateError("invalid_preparation_deadline")
    return value


def _only(value, allowed):
    if not isinstance(value, dict) or not value.keys() <= allowed:
        raise GateError("unsupported_preparation_field")


def _references(value, stages):
    value = [value] if isinstance(value, str) else value
    if not isinstance(value, list):
        raise GateError("invalid_preparation_dependencies")
    result = []
    for item in value:
        identifier(item)
        if item not in stages:
            raise GateError("unknown_preparation_stage")
        if item in result:
            raise GateError("duplicate_preparation_dependency")
        result.append(item)
    return result


def _acyclic(dependencies):
    visiting, complete = set(), set()

    def visit(node):
        if node in visiting:
            raise GateError("cyclic_preparation_dependencies")
        if node in complete:
            return
        visiting.add(node)
        for upstream in dependencies[node]:
            visit(upstream)
        visiting.remove(node)
        complete.add(node)

    for node in dependencies:
        visit(node)


def _output_spec(stage):
    if "output_spec" not in stage:
        return
    value = stage["output_spec"]
    if (not isinstance(value, dict) or set(value) != {"kind", "members"}
            or value["kind"] != "preparation_sources"
            or stage["output"].get("validation") != "preparation_sources"):
        raise GateError("invalid_preparation_output_spec")
    # Match publication's complete path capability, including Windows aliases.
    from .runtime_outputs import validate_output_spec
    validate_output_spec(value)


def compile_preparation(request, *, thread_id, workspace):
    """Return assignments, bindings and a deterministic runtime plan.

    Stage references use declared stage IDs; ``inputs[].after_task`` also accepts
    the corresponding compiled task ID. Existing input descriptors remain actual
    descriptors, with no copied file bodies or inferred professional conclusions.
    Every stage supplies ``inputs`` explicitly, including ``[]`` when none exist.
    A ``from_stage`` readback instead receives that source's exact candidate;
    its explicit inputs must be empty, and adoption waits for source adoption.
    ``review_purpose`` supplies original requirements/evidence locations before
    any author exposure; it defaults to request ``purpose`` and original use.
    ``deadline_ms`` is absolute and must be supplied by the entry when wanted.
    """
    _only(request, REQUEST_FIELDS)
    request = deepcopy(request)
    workflow = identifier(request.get("workflow_id"))
    authorization = _text(request.get("authorization_ref"), "explicit_runtime_authorization_required")
    _text(thread_id, "original_thread_binding_required")
    root = str(Path(workspace).resolve())
    timeout = _positive(request.get("run_timeout_ms", DEFAULT_RUN_TIMEOUT_MS))
    if "deadline_ms" in request:
        _positive(request["deadline_ms"])
    for field in ("purpose", "report_prompt"):
        if field in request:
            _text(request[field], "explicit_preparation_prompt_required")
    if not isinstance(request.get("stages"), list) or not request["stages"]:
        raise GateError("explicit_preparation_stages_required")

    stages, outputs = {}, {}
    definitions = load_definition()["objects"]
    for stage in request["stages"]:
        _only(stage, STAGE_FIELDS)
        stage_id = identifier(stage.get("id"))
        if stage_id in stages:
            raise GateError("duplicate_preparation_stage")
        if stage.get("role") not in {"AG1", "AG2"}:
            raise GateError("invalid_preparation_role")
        _text(stage.get("prompt"), "explicit_preparation_prompt_required")
        scopes(stage.get("scope"))
        identifier(stage.get("use"))
        _only(stage.get("output"), {"id", "type", "validation"})
        output = stage["output"]
        output_id = identifier(output.get("id"))
        specification = definitions.get(_text(output.get("type"), "preparation_output_owner_mismatch"))
        if not specification or specification["owners"][0] != stage["role"]:
            raise GateError("preparation_output_owner_mismatch")
        if output_id in outputs:
            raise GateError("duplicate_preparation_output")
        if output.get("validation", "file_integrity") not in {"file_integrity", "utf8", "contract_fields", "preparation_sources"}:
            raise GateError("unsupported_validation_profile")
        if output.get("validation") == "preparation_sources" and output["type"] != "MaterialUse":
            raise GateError("ag2_material_sources_required")
        for field in ("review_required", "adopt"):
            stage.setdefault(field, True)
            if type(stage[field]) is not bool:
                raise GateError("explicit_preparation_boolean_required")
        if not isinstance(stage.get("inputs"), list):
            raise GateError("explicit_review_policy_and_inputs_required")
        for field in ("review_purpose", "provisional_conditions"):
            if field in stage:
                _text(stage[field], "explicit_preparation_prompt_required")
        for field in ("run_timeout_ms", "wait_ms"):
            if field in stage:
                _positive(stage[field])
        _output_spec(stage)
        stages[stage_id], outputs[output_id] = stage, stage_id

    if {stage["role"] for stage in stages.values()} != {"AG1", "AG2"} or not any(s["review_required"] for s in stages.values()):
        raise GateError("full_preparation_roles_required")

    task_ids = {key: identifier(workflow + "-" + key) for key in stages}
    task_stages = {task: key for key, task in task_ids.items()}
    all_tasks = list(task_ids.values()) + [identifier(task_ids[key] + "-review")
                                           for key, stage in stages.items() if stage["review_required"]]
    if len(set(all_tasks)) != len(all_tasks):
        raise GateError("duplicate_preparation_task")
    node_ids = {key: {part: identifier(task + "-" + part) for part in ("work", "questions", "review", "adopt")}
                for key, task in task_ids.items()}
    report_id = identifier(workflow + "-report")
    attention_id = identifier(workflow + "-attention")
    reserved = [report_id, attention_id]
    for key, stage in stages.items():
        reserved.append(node_ids[key]["work"])
        if stage["review_required"]:
            reserved.extend(node_ids[key][part] for part in ("questions", "review"))
        if stage["adopt"]:
            reserved.append(node_ids[key]["adopt"])
    if len(set(reserved)) != len(reserved):
        raise GateError("duplicate_preparation_node")
    node_scopes = {node: stage["scope"] for key, stage in stages.items() for node in node_ids[key].values()}
    node_scopes[report_id] = sorted({part for stage in stages.values() for part in stage["scope"]})
    node_scopes[attention_id] = node_scopes[report_id]

    work_dependencies = {}
    for key, stage in stages.items():
        for field in ("after", "review_after", "adopt_after"):
            stage[field] = _references(stage.get(field, []), stages)
        dependencies = list(stage["after"])
        source = stage.get("from_stage")
        if source is not None:
            source = _references(source, stages)
            if len(source) != 1:
                raise GateError("invalid_preparation_readback")
            stage["from_stage"] = source = source[0]
            original = stages[source]
            if (stage["role"] != "AG1" or stage["output"]["type"] != "ActivitySpec"
                    or stage["use"] != original["use"] or not set(stage["scope"]) <= set(original["scope"])
                    or stage["inputs"]):
                raise GateError("readback_scope_or_use_mismatch")
        for item in stage["inputs"]:
            _only(item, INPUT_FIELDS)
            artifact = identifier(item.get("artifact"))
            identifier(item.get("use"))
            scopes(item.get("scope"))
            if "revision" in item and (type(item["revision"]) is not int or item["revision"] < 1):
                raise GateError("exact_ref_required")
            if "provisional_conditions" in item:
                _text(item["provisional_conditions"], "explicit_provisional_conditions_required")
            producer = outputs.get(artifact)
            if "after_task" in item:
                reference = identifier(item["after_task"])
                source_key = task_stages.get(reference, reference)
                if source_key not in stages:
                    raise GateError("unknown_preparation_stage")
                if "revision" in item or producer != source_key:
                    raise GateError("preparation_input_producer_mismatch")
                item["after_task"] = task_ids[source_key]
                producer = source_key
            if producer is not None:
                original = stages[producer]
                if item["use"] != original["use"] or not set(item["scope"]) <= set(original["scope"]):
                    raise GateError("preparation_input_scope_or_use_mismatch")
                if producer not in dependencies:
                    dependencies.append(producer)
        work_dependencies[key] = dependencies
        for dependency in dependencies + stage["adopt_after"]:
            if not stages[dependency]["adopt"]:
                raise GateError("preparation_dependency_not_adopted")
        if source and stage["adopt"] and not stages[source]["adopt"]:
            raise GateError("preparation_dependency_not_adopted")

    bindings = [{"id": identifier(workflow + "-" + role), "role": role,
                 "host_kind": "desktop" if role == "AG0" else "cli",
                 "thread_id": thread_id if role == "AG0" else None, "cwd": root,
                 "authorized": True, "authorization_ref": authorization}
                for role in ("AG0", "AG1", "AG2", "AG3")]
    assignments, nodes, graph = [], [], {}
    review_count = 0

    def add(node, depends):
        node["scope"] = deepcopy(node_scopes[node["id"]])
        node["run_timeout_ms"] = node.pop("_timeout", timeout)
        if "deadline_ms" in request:
            node["deadline_ms"] = request["deadline_ms"]
        nodes.append(node)
        graph[node["id"]] = set(depends)

    for key, stage in stages.items():
        task, ids = task_ids[key], node_ids[key]
        assignment = {"action": "assign", "task": task, "to": stage["role"],
                      "output": stage["output"], "scope": stage["scope"], "use": stage["use"],
                      "review_required": stage["review_required"], "inputs": stage["inputs"]}
        if any("after_task" in item for item in stage["inputs"]):
            assignment["wait_ms"] = stage.get("wait_ms", timeout)
        conditions = [{"kind": "adopted", "task": task_ids[d]} for d in work_dependencies[key]]
        depends = [node_ids[d]["adopt"] for d in work_dependencies[key]]
        worker = {"id": ids["work"], "binding": workflow + "-" + stage["role"], "task": task,
                  "allowed_tasks": [task], "manage_tasks": [task],
                  "allowed_actions": ["start", "submit", "confirm"], "conditions": conditions,
                  "required_intents": ["deliver", "opinion"], "completion": "business", "use": stage["use"],
                  "_timeout": stage.get("run_timeout_ms", timeout),
                  "prompt": (stage["prompt"] + "\n\nExact assigned task: " + task + ". Scope: " + encode(stage["scope"])
                             + "; original use: " + stage["use"] + ". Read the actual fixed input text and required originals. "
                             "Return the completed professional output and deliver for this exact task with path '$output', "
                             "then an explicit owner opinion for the same task with outcome supported, partial or rejected "
                             "and a substantive rationale based on the work actually completed. Do not prefill approval, "
                             "invent evidence, broaden the scope/use or claim adoption. End this turn after the result; do not wait or poll.")}
        if stage.get("from_stage"):
            source = stage["from_stage"]
            setup = {k: v for k, v in assignment.items() if k not in {"action", "inputs"}}
            setup.update(action="assign_readback", from_task=task_ids[source],
                         provisional_conditions=stage.get("provisional_conditions", "Exact submitted candidate for functional readback in its original scope/use; not an adopted input. Any owner opinion must explicitly state provisional limits."))
            worker.update(setup_intents=[setup], allowed_tasks=[task, task_ids[source]],
                          allowed_actions=["register", "start", "submit", "confirm"])
            conditions.append({"kind": "submitted", "task": task_ids[source]})
            depends.append(node_ids[source]["work"])
            worker["prompt"] += " This is candidate functional readback. If confirming before source adoption, explicitly set allow_provisional:true and state its limitations; provisional confirmation never authorizes adoption."
        else:
            assignments.append(assignment)
        if "output_spec" in stage:
            worker["output_spec"] = stage["output_spec"]
            worker["prompt"] += " The output_spec fixes the only authorized material members. Return output as JSON containing files with exactly their declared id and content; the executor saves the declared paths and builds the version inventory."
        add(worker, depends)

        if stage["review_required"]:
            review_binding = workflow + "-AG3" if review_count == 0 else identifier(task + "-AG3")
            review_count += 1
            if review_count > 1:
                bindings.append({**bindings[3], "id": review_binding})
            review_task = identifier(task + "-review")
            origin = stage.get("review_purpose", request.get("purpose", "Original authorized use: " + stage["use"]))
            question_dependencies = [ids["work"]] + [node_ids[d]["work"] for d in stage["review_after"]]
            add({"id": ids["questions"], "binding": review_binding, "allowed_tasks": [task, review_task],
                 "allowed_actions": ["start"], "conditions": [{"kind": "work_done", "node": n} for n in dict.fromkeys(question_dependencies)],
                 "completion": "result", "required_intents": [], "use": stage["use"],
                 "prompt": ("Independently frame the questions that could change the review decision using only the original purpose and necessary original evidence locations below. "
                            "Do not open the author's design, output or passing summary in this first step. State actual exposure and any missing original evidence honestly. "
                            "Return your bounded questions as output with intents:[]; finish the turn without waiting.\nOriginal purpose/evidence: "
                            + origin + "\nExact scope: " + encode(stage["scope"]) + "; use: " + stage["use"])}, question_dependencies)
            add({"id": ids["review"], "binding": review_binding, "task": review_task,
                 "allowed_tasks": [review_task, task], "manage_tasks": [review_task],
                 "allowed_actions": ["register", "start", "review"], "required_intents": ["opinion"],
                 "completion": "business", "use": stage["use"],
                 "conditions": [{"kind": "submitted", "task": task}, {"kind": "work_done", "node": ids["questions"]}],
                 "include_prior_results": [ids["questions"]],
                 "setup_intents": [{"action": "assign_review", "task": review_task, "from_task": task}],
                 "prompt": ("Review the exact assigned version against your previously recorded independent questions and original purpose. "
                            "Now read the author's goal/design, actual product and complete references; read any author passing summary last. "
                            "Read the necessary actual originals, record true exposure order and limitations, and do not claim blind or different-model review. "
                            "Return an explicit opinion for exact review task " + review_task + " with outcome supported, partial or rejected "
                            "and a substantive rationale from your actual checks. Do not invent approval or adoption. Finish the turn; do not wait or poll.")}, [ids["questions"], ids["work"]])

        if stage["adopt"]:
            adoption_conditions = [{"kind": "adoption_ready", "task": task}]
            adoption_dependencies = [ids["work"]] + ([ids["review"]] if stage["review_required"] else [])
            adoption_conditions.extend({"kind": "work_done", "node": n} for n in adoption_dependencies)
            adopted_dependencies = list(stage["adopt_after"])
            if stage.get("from_stage") and stage["from_stage"] not in adopted_dependencies:
                adopted_dependencies.append(stage["from_stage"])
            for dependency in adopted_dependencies:
                adoption_conditions.append({"kind": "adopted", "task": task_ids[dependency]})
                adoption_dependencies.append(node_ids[dependency]["adopt"])
            add({"id": ids["adopt"], "binding": workflow + "-AG0", "allowed_tasks": [task],
                 "allowed_actions": ["adopt"], "conditions": adoption_conditions,
                 "required_intents": ["adopt"], "completion": "business", "result_via_file": True, "use": stage["use"],
                 "prompt": ("Make the actual AG0 adoption decision for exact task " + task + " within its original scope/use. "
                            "Read the current exact professional receipts, unresolved limits, controls and any originals needed for this decision. "
                            "Readiness is only a program gate and is not your professional decision. If your actual judgment supports adoption, "
                            "return the explicit intent " + encode({"action": "adopt", "tasks": [task]})
                            + "; otherwise return the actual unresolved decision and no adopt intent. "
                            "Save the structured result through the runtime result entry, then report briefly to the user and end this turn without waiting.")}, adoption_dependencies)

    report_dependencies = list(graph)
    add({"id": report_id, "binding": workflow + "-AG0", "allowed_tasks": list(task_ids.values()),
         "allowed_actions": ["start"], "conditions": [{"kind": "work_done", "node": n} for n in report_dependencies]
         + [{"kind": "adopted", "task": task_ids[key]} for key, stage in stages.items() if stage["adopt"]],
         "completion": "result", "required_intents": [], "result_via_file": True, "use": "coordination",
         "prompt": (request.get("report_prompt", "Report the preparation's actual completed outputs, exact adopted versions, verification limits and any remaining user action from the recorded facts.")
                    + "\nThis final node reports results only. Return intents:[] and do not create or change professional decisions. "
                    "Save the structured result through the runtime result entry; give the user a concise readable result and end this turn without waiting or polling.")}, report_dependencies)
    add({"id": attention_id, "binding": workflow + "-AG0", "handling_attention": True,
         "allowed_tasks": list(task_ids.values()), "allowed_actions": ["start"],
         "conditions": [{"kind": "workflow_attention"}], "completion": "result", "required_intents": [],
         "result_via_file": True, "use": "coordination",
         "prompt": ("Report the workflow's actual failed or unresolved dispatches from decision_basis to the user. "
                    "Identify the affected task/node, exact observed state and reason, completed work that remains available, "
                    "and the concrete action or information needed to proceed. Preserve uncertainty; do not claim completion, "
                    "failure, cancellation or professional approval beyond the recorded facts. This node reports results only: "
                    "return intents:[] and save the structured result through the runtime result entry. Do not retry or resend "
                    "failed or unresolved work, start extra agents, change decisions, wait or poll. Give a concise readable "
                    "report to the user and end this turn.")}, [])
    _acyclic(graph)
    return {"workflow_id": workflow, "authorization_ref": authorization, "assignments": assignments,
            "bindings": bindings, "plan": {"id": workflow, "revision": 1, "authorization_ref": authorization,
                                          "enabled": True, "nodes": nodes}}
