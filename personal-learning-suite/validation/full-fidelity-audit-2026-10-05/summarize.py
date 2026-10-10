"""Summarize observed layers without converting fictional first turns to efficacy."""
from pathlib import Path
import json

OUT = Path(__file__).resolve().parent
read = lambda name: json.loads((OUT/name).read_text(encoding='utf-8-sig'))
integrity, learning = read('integrity-result.json'), read('learning-unchanged.json')
formats, b0 = read('skill-format-results.json'), read('b0-static-result.json')
resource = read('resource-check-observation.json')
assert integrity['status']=='pass' and learning['unchanged']
assert formats['status']=='pass' and b0['status']=='pass' and resource['status']=='pass'
result = {
    'execution_date_in_user_context':'2026-10-05',
    'kind':'whole-framework original-source fidelity review and fictional first-turn execution',
    'reviewers':['entry_continuity_fresh','design_assessment_fresh','teaching_forward_fresh'],
    'instruction_scope':{'skills':7,'skill_references':30,'agent_definitions':4,'total':41},
    'review_findings':{'confirmed_substantive_instruction_deviations':0,
        'confirmed_source_locator_errors_fixed':1,
        'main_flow_rewrite_required_by_observed_evidence':False},
    'first_turn_execution':{'fictional_cases':12,'cases_per_reviewer':4,
        'actual_requests_and_outputs_saved':True,'root_read_all_cases':True,
        'teaching_outputs_frozen_before_original_design_research_audit':True,
        'entry_and_design_cases_created_after_their_source_review':True,
        'ideal_answers_or_prior_outputs_provided_to_generators':False,
        'teaching_narrow_source_locator_fix_notice_received':True,
        'generated_learner_followups':False,'formal_learning_state_submissions':False,
        'same_system_model_subagents':True,'technical_read_isolation':False,
        'root_blind_grading':False,'reviewer_self_grading_is_independent':False},
    'validation_layers':{
        'V1':'limited specific math/code/content/figure anchors; not general efficacy',
        'V2':'12 actual fictional first turns; later feedback and runtime adoption not executed',
        'V3':'not_executed: no real learner performance',
        'V4':'not_executed: no comparable learning/cost observations'},
    'content_anchors':{'lower_bound_finite_inputs':280,'original_input_program_failures':80,
        'teacher_reference_failures':0,'general_proof_separate_from_finite_execution':True,
        'affine_png_opened_by_generator_and_root':True,
        'learner_independent_implementation_or_drawing_proven':False},
    'software_checks':{'skill_formats_passed':len(formats['results']),
        'b0_static_cases_passed':sum(c['status']=='pass' for c in b0['static_cases']),
        'b0_future_scenarios_not_executed':len(b0['runtime_scenarios']),
        'resource_build_check':resource['observed_stdout'],
        'previous_phase_483_runtime_regressions_rerun':False,
        'runtime_code_changed':False},
    'public_integrity':integrity,
    'learning_directory_unchanged':learning,
    'course_deployment':{'mode':'manual_files','native_skills_installed':False,
        'real_runtime_binding':False,'four_independent_teaching_agents_started':False},
    'costs':{'actual_real_learning_time':'unknown','user_wait_time':'unknown',
        'actual_model_fees':'unknown','fictional_budget_is_measured_time':False},
    'limits':['No original educational papers revalidated.',
        'Original source fidelity and first turns do not guarantee all models, later responses or learning outcomes.',
        'Independent source-first contexts are not cross-model replication, blind grading or real learning.']
}
(OUT/'verification-summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'source_review':'complete_with_stated_read_coverage',
    'actual_fictional_first_turns':12,'locator_error_fixed':1,
    'public_integrity':integrity['status'],'learning_unchanged_during_final_segment':learning['unchanged'],
    'whole_audit_learning_fingerprint_check_complete':False,
    'V3':'not_executed','V4':'not_executed'},ensure_ascii=False))
