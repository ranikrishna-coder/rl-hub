/**
 * Verifier Data Layer
 * All verifier definitions for the AgentWork Simulator, grouped by system.
 * Follows the RL verifier paradigm: objective, verifiable rewards using
 * rule-based, trajectory-based, and LLM-judged approaches.
 */

(function () {
    'use strict';

    // ── Jira Verifiers (4) ──────────────────────────────────────────────
    const jiraVerifiers = [
        {
            id: 'jira-issue-resolution',
            name: 'Jira Issue Resolution',
            type: 'rule-based',
            system: 'Jira',
            environment: 'jira',
            version: 1,
            status: 'active',
            usedInScenarios: ['Issue Resolution Flow', 'Status Update Workflow'],
            description: 'Validates tool sequence and argument validity for Jira issue resolution. Checks get_issue → get_transitions → transition_issue order and verifies transition_id comes from valid transitions.',
            metadata: { type: 'rule-based', environment: 'jira', onFailure: 'log_and_continue', timeout: '30s' },
            logic: {
                type: 'jira_issue_resolution_validator',
                checks: {
                    tool_sequence: {
                        expected_order: ['get_issue_summary_and_description', 'get_transitions', 'transition_issue'],
                        allow_extra_calls: true,
                        min_required_calls: 3
                    },
                    argument_validity: {
                        tool: 'transition_issue',
                        field: 'transition_id',
                        must_be_in: { source_tool: 'get_transitions', source_field: 'valid_transition_ids' }
                    }
                },
                scoring: { tool_usage_weight: 0.2, sequence_weight: 0.4, valid_transition_weight: 0.4 }
            },
            exampleInput: {
                trajectory: [
                    { tool_call: 'get_issue_summary_and_description', arguments: { issue_key: 'ISK-2' } },
                    { tool_call: 'get_transitions', arguments: { issue_key: 'ISK-2' }, tool_result: { valid_transitions: [{ id: '31', name: 'In Progress' }, { id: '61', name: 'Done' }] } },
                    { tool_call: 'transition_issue', arguments: { issue_key: 'ISK-2', transition_id: '61' } }
                ]
            },
            exampleOutput: { verdict: 'pass', score: 0.95, details: { sequence_ok: true, transition_id_valid: true, valid_transition_ids: ['31', '61'] } },
            failurePolicy: { hard_fail: true, penalty: -1.0, log_failure: true },
            subVerifiers: [
                { id: 'jira-ir-tool-seq', name: 'Tool Sequence', description: 'Validates correct tool call order', enabled: true },
                { id: 'jira-ir-arg-valid', name: 'Argument Validity', description: 'Checks transition_id from valid transitions', enabled: true },
                { id: 'jira-ir-scoring', name: 'Scoring Weights', description: 'Applies weighted scoring for usage, sequence, transition', enabled: true }
            ]
        },
        {
            id: 'jira-comment-management',
            name: 'Jira Comment Management',
            type: 'rule-based',
            system: 'Jira',
            environment: 'jira',
            version: 1,
            status: 'active',
            usedInScenarios: ['Comment Thread Management'],
            description: 'Validates tool sequence and content for Jira comment workflows. Ensures add_comment → get_comments order with non-empty comment body.',
            metadata: { type: 'rule-based', environment: 'jira', onFailure: 'log_and_continue', timeout: '30s' },
            logic: {
                type: 'jira_comment_management_validator',
                checks: {
                    tool_sequence: { expected_order: ['add_comment', 'get_comments'], allow_extra_calls: true, min_required_calls: 2 },
                    argument_validity: { tool: 'add_comment', required_fields: ['issue_key', 'body'], content_non_empty: true }
                },
                scoring: { tool_usage_weight: 0.3, sequence_weight: 0.5, content_valid_weight: 0.2 }
            },
            exampleInput: {
                trajectory: [
                    { tool_call: 'add_comment', arguments: { issue_key: 'ISK-2', body: 'Updated status.' } },
                    { tool_call: 'get_comments', arguments: { issue_key: 'ISK-2' } }
                ]
            },
            exampleOutput: { verdict: 'pass', score: 0.92, details: { sequence_ok: true, content_valid: true } },
            failurePolicy: { hard_fail: false, penalty: -0.5, log_failure: true }
        },
        {
            id: 'jira-task-management',
            name: 'Jira Task Management',
            type: 'rule-based',
            system: 'Jira',
            environment: 'jira',
            version: 1,
            status: 'active',
            usedInScenarios: ['Create Sub-task', 'Delete Sub-task'],
            description: 'Deterministic, rubric-based verifier for Jira task and sub-task workflows. Provides dense rewards for correct sub-task creation and deletion.',
            metadata: { type: 'rule-based', environment: 'jira', onFailure: 'log_and_continue', timeout: '30s' },
            logic: {
                type: 'jira_task_management_validator',
                checks: {
                    tool_sequence: { expected_order: ['get_issue_summary_and_description', 'create_subtask'], allow_extra_calls: true, min_required_calls: 1 },
                    create_subtask: { tool: 'create_subtask', required_fields: ['parent_key', 'summary'], summary_non_empty: true, parent_must_exist: true }
                },
                scoring: { tool_usage_weight: 0.3, sequence_weight: 0.3, field_validity_weight: 0.4 }
            },
            exampleInput: {
                trajectory: [
                    { tool_call: 'get_issue_summary_and_description', arguments: { issue_key: 'PROJ-101' } },
                    { tool_call: 'create_subtask', arguments: { parent_key: 'PROJ-101', summary: 'Reproduce SSO 500 error', description: 'Follow steps from incident report' } }
                ]
            },
            exampleOutput: { verdict: 'pass', score: 0.93, details: { sequence_ok: true, subtask_created: true, fields_valid: true } },
            failurePolicy: { hard_fail: false, penalty: -0.5, log_failure: true }
        },
        {
            id: 'jira-ruler-resolution',
            name: 'RULER \u00b7 Jira Resolution',
            type: 'llm-judge',
            system: 'Jira',
            environment: 'jira',
            version: 1,
            status: 'active',
            usedInScenarios: ['Issue Resolution Flow'],
            description: 'LLM-based relative ranking of Jira resolution trajectories. Uses GPT-4.1-mini to score multiple agent trajectories on tool usage, order of operations, and resolution outcome.',
            metadata: { type: 'llm-judge', environment: 'jira', onFailure: 'return_low_score', timeout: '120s' },
            logic: {
                type: 'ruler_llm_judge',
                model: 'gpt-4.1-mini',
                scoring: 'relative',
                output_range: [0, 1],
                judge_prompt: 'You are evaluating multiple agent trajectories for resolving a Jira issue.\nRank them based on:\n1. Correct tool usage\n2. Correct order of operations\n3. Whether the issue ends in a resolved state\n\nReturn a score between 0 and 1 for each trajectory.'
            },
            exampleInput: {
                trajectories: [
                    { id: 'traj_1', steps: ['thought', 'thought'] },
                    { id: 'traj_2', steps: ['get_issue_summary_and_description', 'get_transitions', 'transition_issue'] }
                ]
            },
            exampleOutput: { scores: { traj_1: 0.12, traj_2: 0.94 } },
            failurePolicy: { hard_fail: false, penalty: 0.0, log_failure: true }
        }
    ];

    // ── ADP Verifiers (3) ───────────────────────────────────────────────
    const adpVerifiers = [
        {
            id: 'adp-worker-creation',
            name: 'ADP Worker Creation',
            type: 'rule-based',
            system: 'ADP',
            environment: 'hr_payroll',
            version: 1,
            status: 'active',
            usedInScenarios: ['Create Worker & Assign'],
            description: 'Validates the ADP worker creation sequence: get_pay_group → build_worker_payload → post_worker. Ensures pay group is resolved before payload construction.',
            metadata: { type: 'rule-based', environment: 'hr_payroll', onFailure: 'log_and_continue', timeout: '30s' },
            logic: {
                type: 'adp_worker_creation_validator',
                checks: {
                    tool_sequence: { expected_order: ['get_pay_group', 'build_worker_payload', 'post_worker'], allow_extra_calls: false, min_required_calls: 3 },
                    argument_validity: { tool: 'post_worker', required_fields: ['worker_payload'], payload_must_include: ['pay_group_id', 'worker_name'] }
                },
                scoring: { tool_usage_weight: 0.3, sequence_weight: 0.4, field_validity_weight: 0.3 }
            },
            exampleInput: {
                trajectory: [
                    { tool_call: 'get_pay_group', arguments: { org_code: 'US-WEST' } },
                    { tool_call: 'build_worker_payload', arguments: { pay_group_id: 'PG-101', worker_name: 'Jane Doe' } },
                    { tool_call: 'post_worker', arguments: { worker_payload: { pay_group_id: 'PG-101', worker_name: 'Jane Doe' } } }
                ]
            },
            exampleOutput: { verdict: 'pass', score: 0.96, details: { sequence_ok: true, fields_valid: true } },
            failurePolicy: { hard_fail: true, penalty: -1.0, log_failure: true }
        },
        {
            id: 'adp-bulk-import',
            name: 'ADP Bulk Import',
            type: 'rule-based',
            system: 'ADP',
            environment: 'hr_payroll',
            version: 1,
            status: 'active',
            usedInScenarios: ['Bulk Worker Import'],
            description: 'Validates ADP bulk worker import: validate_positions → build_bulk_payload → post_bulk. Ensures position validation before bulk submission.',
            metadata: { type: 'rule-based', environment: 'hr_payroll', onFailure: 'log_and_continue', timeout: '60s' },
            logic: {
                type: 'adp_bulk_import_validator',
                checks: {
                    tool_sequence: { expected_order: ['validate_positions', 'build_bulk_payload', 'post_bulk'], allow_extra_calls: false, min_required_calls: 3 },
                    row_validation: { min_valid_rows: 1, max_error_rate: 0.1 }
                },
                scoring: { tool_usage_weight: 0.2, sequence_weight: 0.4, validation_weight: 0.4 }
            },
            exampleInput: {
                trajectory: [
                    { tool_call: 'validate_positions', arguments: { positions: ['POS-001', 'POS-002'] } },
                    { tool_call: 'build_bulk_payload', arguments: { validated_positions: ['POS-001', 'POS-002'] } },
                    { tool_call: 'post_bulk', arguments: { bulk_payload: { count: 2 } } }
                ]
            },
            exampleOutput: { verdict: 'pass', score: 0.91, details: { sequence_ok: true, error_rate: 0.0 } },
            failurePolicy: { hard_fail: false, penalty: -0.8, log_failure: true }
        },
        {
            id: 'adp-time-off-payroll',
            name: 'ADP Time-Off & Payroll',
            type: 'trajectory-based',
            system: 'ADP',
            environment: 'hr_payroll',
            version: 1,
            status: 'active',
            usedInScenarios: ['Time-Off Request', 'Payroll Processing'],
            description: 'Evaluates the end-to-end time-off and payroll approval trajectory. Scores based on accrual balance check, request validation, and correct submission.',
            metadata: { type: 'trajectory-based', environment: 'hr_payroll', onFailure: 'log_and_continue', timeout: '45s' },
            logic: {
                type: 'adp_time_off_trajectory',
                trajectory_checks: {
                    required_steps: ['get_accrual_balance', 'validate_request', 'submit_time_off'],
                    balance_must_be_positive: true,
                    approval_chain: ['manager', 'hr']
                },
                scoring: { completeness_weight: 0.4, correctness_weight: 0.4, efficiency_weight: 0.2 }
            },
            exampleInput: {
                trajectory: [
                    { step: 1, tool_call: 'get_accrual_balance', result: { balance: 80, used: 40 } },
                    { step: 2, tool_call: 'validate_request', result: { valid: true, days_requested: 5 } },
                    { step: 3, tool_call: 'submit_time_off', result: { submitted: true, approval_status: 'pending' } }
                ]
            },
            exampleOutput: { verdict: 'pass', score: 0.88, details: { completeness: 1.0, correctness: 0.9, efficiency: 0.75 } },
            failurePolicy: { hard_fail: false, penalty: -0.5, log_failure: true }
        }
    ];

    // ── Workday Verifiers (3) ───────────────────────────────────────────
    const workdayVerifiers = [
        {
            id: 'workday-record-creation',
            name: 'Workday Record Creation',
            type: 'rule-based',
            system: 'Workday',
            environment: 'hr_payroll',
            version: 1,
            status: 'active',
            usedInScenarios: ['Create Worker Record'],
            description: 'Validates Workday worker record creation: get_supervisory_org → build_worker_payload → post_worker. Ensures org context is fetched before record creation.',
            metadata: { type: 'rule-based', environment: 'hr_payroll', onFailure: 'log_and_continue', timeout: '30s' },
            logic: {
                type: 'workday_record_creation_validator',
                checks: {
                    tool_sequence: { expected_order: ['get_supervisory_org', 'build_worker_payload', 'post_worker'], allow_extra_calls: false, min_required_calls: 3 },
                    argument_validity: { tool: 'post_worker', required_fields: ['worker_payload'], payload_must_include: ['supervisory_org_id', 'worker_name'] }
                },
                scoring: { tool_usage_weight: 0.3, sequence_weight: 0.4, field_validity_weight: 0.3 }
            },
            exampleInput: {
                trajectory: [
                    { tool_call: 'get_supervisory_org', arguments: { org_name: 'Engineering' } },
                    { tool_call: 'build_worker_payload', arguments: { org_id: 'ORG-42', worker_name: 'John Smith' } },
                    { tool_call: 'post_worker', arguments: { worker_payload: { supervisory_org_id: 'ORG-42', worker_name: 'John Smith' } } }
                ]
            },
            exampleOutput: { verdict: 'pass', score: 0.94, details: { sequence_ok: true, fields_valid: true } },
            failurePolicy: { hard_fail: true, penalty: -1.0, log_failure: true }
        },
        {
            id: 'workday-bulk-import',
            name: 'Workday Bulk Import',
            type: 'rule-based',
            system: 'Workday',
            environment: 'hr_payroll',
            version: 1,
            status: 'active',
            usedInScenarios: ['Bulk Record Import'],
            description: 'Validates Workday bulk record import: build_bulk_csv → validate_rows → launch_integration. Ensures data validation before integration launch.',
            metadata: { type: 'rule-based', environment: 'hr_payroll', onFailure: 'log_and_continue', timeout: '60s' },
            logic: {
                type: 'workday_bulk_import_validator',
                checks: {
                    tool_sequence: { expected_order: ['build_bulk_csv', 'validate_rows', 'launch_integration'], allow_extra_calls: false, min_required_calls: 3 },
                    row_validation: { min_valid_rows: 1, max_error_rate: 0.05 }
                },
                scoring: { tool_usage_weight: 0.2, sequence_weight: 0.4, validation_weight: 0.4 }
            },
            exampleInput: {
                trajectory: [
                    { tool_call: 'build_bulk_csv', arguments: { records: [{ name: 'A' }, { name: 'B' }] } },
                    { tool_call: 'validate_rows', arguments: { csv_path: '/tmp/bulk.csv' }, result: { valid: 2, errors: 0 } },
                    { tool_call: 'launch_integration', arguments: { csv_path: '/tmp/bulk.csv' } }
                ]
            },
            exampleOutput: { verdict: 'pass', score: 0.95, details: { sequence_ok: true, error_rate: 0.0 } },
            failurePolicy: { hard_fail: false, penalty: -0.8, log_failure: true }
        },
        {
            id: 'workday-time-off-approval',
            name: 'Workday Time-Off Approval',
            type: 'trajectory-based',
            system: 'Workday',
            environment: 'hr_payroll',
            version: 1,
            status: 'active',
            usedInScenarios: ['Time-Off & Expense Approval'],
            description: 'Evaluates the end-to-end Workday time-off and expense approval trajectory. Scores based on report retrieval, balance validation, and proper approval flow.',
            metadata: { type: 'trajectory-based', environment: 'hr_payroll', onFailure: 'log_and_continue', timeout: '45s' },
            logic: {
                type: 'workday_time_off_trajectory',
                trajectory_checks: {
                    required_steps: ['get_report', 'validate_balance', 'approve_request'],
                    balance_must_cover_request: true,
                    approval_chain: ['manager']
                },
                scoring: { completeness_weight: 0.4, correctness_weight: 0.4, efficiency_weight: 0.2 }
            },
            exampleInput: {
                trajectory: [
                    { step: 1, tool_call: 'get_report', result: { employee: 'Jane', balance: 120 } },
                    { step: 2, tool_call: 'validate_balance', result: { sufficient: true, hours_requested: 16 } },
                    { step: 3, tool_call: 'approve_request', result: { approved: true } }
                ]
            },
            exampleOutput: { verdict: 'pass', score: 0.90, details: { completeness: 1.0, correctness: 0.95, efficiency: 0.80 } },
            failurePolicy: { hard_fail: false, penalty: -0.5, log_failure: true }
        }
    ];

    // ── SAP SuccessFactors Verifiers (3) ────────────────────────────────
    const sapVerifiers = [
        {
            id: 'sap-employment-record',
            name: 'SAP Employment Record',
            type: 'rule-based',
            system: 'SAP SuccessFactors',
            environment: 'hr_payroll',
            version: 1,
            status: 'active',
            usedInScenarios: ['Create Employment Record'],
            description: 'Validates SAP SuccessFactors employment record creation: get_job_classification → build_employment_payload → post_employment.',
            metadata: { type: 'rule-based', environment: 'hr_payroll', onFailure: 'log_and_continue', timeout: '30s' },
            logic: {
                type: 'sap_employment_record_validator',
                checks: {
                    tool_sequence: { expected_order: ['get_job_classification', 'build_employment_payload', 'post_employment'], allow_extra_calls: false, min_required_calls: 3 },
                    argument_validity: { tool: 'post_employment', required_fields: ['employment_payload'], payload_must_include: ['job_classification_id', 'employee_name'] }
                },
                scoring: { tool_usage_weight: 0.3, sequence_weight: 0.4, field_validity_weight: 0.3 }
            },
            exampleInput: {
                trajectory: [
                    { tool_call: 'get_job_classification', arguments: { job_code: 'ENG-SWE' } },
                    { tool_call: 'build_employment_payload', arguments: { classification_id: 'JC-100', employee_name: 'Alice' } },
                    { tool_call: 'post_employment', arguments: { employment_payload: { job_classification_id: 'JC-100', employee_name: 'Alice' } } }
                ]
            },
            exampleOutput: { verdict: 'pass', score: 0.94, details: { sequence_ok: true, fields_valid: true } },
            failurePolicy: { hard_fail: true, penalty: -1.0, log_failure: true }
        },
        {
            id: 'sap-bulk-upsert',
            name: 'SAP Bulk Upsert',
            type: 'rule-based',
            system: 'SAP SuccessFactors',
            environment: 'hr_payroll',
            version: 1,
            status: 'active',
            usedInScenarios: ['Bulk Upsert Records'],
            description: 'Validates SAP SuccessFactors bulk upsert: build_bulk_payload → validate_records → post_upsert. Ensures record validation before submission.',
            metadata: { type: 'rule-based', environment: 'hr_payroll', onFailure: 'log_and_continue', timeout: '60s' },
            logic: {
                type: 'sap_bulk_upsert_validator',
                checks: {
                    tool_sequence: { expected_order: ['build_bulk_payload', 'validate_records', 'post_upsert'], allow_extra_calls: false, min_required_calls: 3 },
                    row_validation: { min_valid_rows: 1, max_error_rate: 0.05 }
                },
                scoring: { tool_usage_weight: 0.2, sequence_weight: 0.4, validation_weight: 0.4 }
            },
            exampleInput: {
                trajectory: [
                    { tool_call: 'build_bulk_payload', arguments: { records: [{ id: 'E001' }, { id: 'E002' }] } },
                    { tool_call: 'validate_records', arguments: { payload_ref: 'bulk_001' }, result: { valid: 2, errors: 0 } },
                    { tool_call: 'post_upsert', arguments: { payload_ref: 'bulk_001' } }
                ]
            },
            exampleOutput: { verdict: 'pass', score: 0.93, details: { sequence_ok: true, error_rate: 0.0 } },
            failurePolicy: { hard_fail: false, penalty: -0.8, log_failure: true }
        },
        {
            id: 'sap-onboarding',
            name: 'SAP Onboarding',
            type: 'trajectory-based',
            system: 'SAP SuccessFactors',
            environment: 'hr_payroll',
            version: 1,
            status: 'active',
            usedInScenarios: ['Employee Onboarding'],
            description: 'Evaluates the end-to-end SAP SuccessFactors onboarding trajectory. Scores template retrieval, checklist assignment, and process launch.',
            metadata: { type: 'trajectory-based', environment: 'hr_payroll', onFailure: 'log_and_continue', timeout: '45s' },
            logic: {
                type: 'sap_onboarding_trajectory',
                trajectory_checks: {
                    required_steps: ['get_onboarding_template', 'assign_checklist', 'launch_process'],
                    checklist_must_be_complete: true
                },
                scoring: { completeness_weight: 0.4, correctness_weight: 0.35, efficiency_weight: 0.25 }
            },
            exampleInput: {
                trajectory: [
                    { step: 1, tool_call: 'get_onboarding_template', result: { template_id: 'OB-ENG', items: 8 } },
                    { step: 2, tool_call: 'assign_checklist', result: { assigned: true, items_assigned: 8 } },
                    { step: 3, tool_call: 'launch_process', result: { launched: true, onboarding_id: 'OB-001' } }
                ]
            },
            exampleOutput: { verdict: 'pass', score: 0.91, details: { completeness: 1.0, correctness: 0.90, efficiency: 0.85 } },
            failurePolicy: { hard_fail: false, penalty: -0.5, log_failure: true }
        }
    ];

    // ── Epic/Cerner Clinical Verifiers (3) ──────────────────────────────
    const clinicalVerifiers = [
        {
            id: 'clinical-outcome',
            name: 'Clinical Outcome',
            type: 'rule-based',
            system: 'Epic',
            environment: 'clinical',
            version: 1,
            status: 'active',
            usedInScenarios: ['Treatment Pathway Optimization', 'Sepsis Early Intervention', 'ICU Resource Allocation'],
            description: 'Validates treatment outcomes meet clinical thresholds. Checks risk score improvement, vital sign stability, severity reduction, and mortality risk reduction.',
            metadata: { type: 'rule-based', environment: 'clinical', onFailure: 'log_and_continue', timeout: '30s' },
            logic: {
                type: 'clinical_outcome_validator',
                checks: {
                    risk_improvement: { min_improvement: 0.1, weight: 0.4 },
                    vital_stability: { max_deviation: 0.2, weight: 0.3 },
                    severity_reduction: { min_reduction: 0.05, weight: 0.2 },
                    mortality_reduction: { min_reduction: 0.02, weight: 0.1 }
                },
                scoring: { risk_weight: 0.4, vital_weight: 0.3, severity_weight: 0.2, mortality_weight: 0.1 }
            },
            exampleInput: {
                state: { risk_score: 0.7, vitals: { hr: 95, bp_sys: 130 }, severity: 'moderate' },
                next_state: { risk_score: 0.5, vitals: { hr: 78, bp_sys: 120 }, severity: 'mild' }
            },
            exampleOutput: { verdict: 'pass', score: 0.87, details: { risk_improvement: 0.29, vital_stability: 0.85, severity_reduced: true } },
            failurePolicy: { hard_fail: false, penalty: -0.5, log_failure: true }
        },
        {
            id: 'clinical-treatment-sequence',
            name: 'Treatment Sequence',
            type: 'trajectory-based',
            system: 'Epic',
            environment: 'clinical',
            version: 1,
            status: 'active',
            usedInScenarios: ['Treatment Pathway Optimization', 'Medication Dosing', 'Care Coordination'],
            description: 'Evaluates the full treatment pathway trajectory quality. Assesses pathway efficiency, resource utilization, treatment ordering appropriateness, and time to improvement.',
            metadata: { type: 'trajectory-based', environment: 'clinical', onFailure: 'log_and_continue', timeout: '60s' },
            logic: {
                type: 'treatment_sequence_trajectory',
                trajectory_checks: {
                    pathway_efficiency: { max_steps: 20, optimal_steps: 8, weight: 0.4 },
                    resource_utilization: { min_diversity: 2, max_redundancy: 0.3, weight: 0.3 },
                    treatment_ordering: { follow_clinical_guidelines: true, weight: 0.2 },
                    time_to_improvement: { max_steps_to_first_improvement: 5, weight: 0.1 }
                },
                scoring: { efficiency_weight: 0.4, resource_weight: 0.3, ordering_weight: 0.2, timing_weight: 0.1 }
            },
            exampleInput: {
                trajectory: [
                    { step: 1, action: 'diagnostic_test', result: { risk_delta: -0.05 } },
                    { step: 2, action: 'medication_adjustment', result: { risk_delta: -0.15 } },
                    { step: 3, action: 'monitoring', result: { risk_delta: -0.02 } },
                    { step: 4, action: 'discharge', result: { risk_delta: 0.0 } }
                ]
            },
            exampleOutput: { verdict: 'pass', score: 0.82, details: { efficiency: 0.9, resource_util: 0.75, ordering: 0.85, timing: 0.80 } },
            failurePolicy: { hard_fail: false, penalty: -0.3, log_failure: true }
        },
        {
            id: 'clinical-ai-judge',
            name: 'Clinical AI Judge',
            type: 'llm-judge',
            system: 'Epic',
            environment: 'clinical',
            version: 1,
            status: 'active',
            usedInScenarios: ['Treatment Pathway Optimization', 'Emergency Triage'],
            description: 'LLM-based assessment of clinical decision appropriateness. Evaluates whether treatment choices align with clinical guidelines and patient condition.',
            metadata: { type: 'llm-judge', environment: 'clinical', onFailure: 'return_low_score', timeout: '120s' },
            logic: {
                type: 'clinical_llm_judge',
                model: 'gpt-4.1-mini',
                scoring: 'absolute',
                output_range: [0, 1],
                judge_prompt: 'You are a clinical decision evaluator. Assess the agent\'s treatment trajectory for:\n1. Clinical appropriateness of each action\n2. Adherence to treatment guidelines\n3. Patient safety considerations\n4. Outcome improvement trajectory\n\nReturn a score between 0 and 1.'
            },
            exampleInput: {
                patient: { severity: 'severe', conditions: ['sepsis', 'pneumonia'] },
                trajectory: [{ action: 'blood_cultures', step: 1 }, { action: 'iv_antibiotics', step: 2 }, { action: 'fluid_resuscitation', step: 3 }]
            },
            exampleOutput: { score: 0.91, rationale: 'Appropriate sepsis protocol followed: cultures before antibiotics, timely fluid resuscitation.' },
            failurePolicy: { hard_fail: false, penalty: 0.0, log_failure: true }
        }
    ];

    // ── Philips/GE Imaging Verifiers (3) ────────────────────────────────
    const imagingVerifiers = [
        {
            id: 'imaging-priority',
            name: 'Imaging Priority',
            type: 'rule-based',
            system: 'Philips',
            environment: 'imaging',
            version: 1,
            status: 'active',
            usedInScenarios: ['Imaging Order Prioritization', 'Radiology Scheduling'],
            description: 'Validates urgency-based imaging prioritization rules. Ensures STAT orders are processed first, high-priority within SLA, and equipment availability is respected.',
            metadata: { type: 'rule-based', environment: 'imaging', onFailure: 'log_and_continue', timeout: '30s' },
            logic: {
                type: 'imaging_priority_validator',
                checks: {
                    urgency_ordering: { stat_first: true, priority_hierarchy: ['STAT', 'urgent', 'high', 'routine'], weight: 0.5 },
                    sla_compliance: { stat_max_wait: 15, urgent_max_wait: 60, weight: 0.3 },
                    equipment_check: { must_verify_availability: true, weight: 0.2 }
                },
                scoring: { urgency_weight: 0.5, sla_weight: 0.3, equipment_weight: 0.2 }
            },
            exampleInput: {
                queue: [
                    { id: 'ORD-1', urgency: 'routine', modality: 'CT' },
                    { id: 'ORD-2', urgency: 'STAT', modality: 'MRI' }
                ],
                action: { processed: 'ORD-2' }
            },
            exampleOutput: { verdict: 'pass', score: 0.95, details: { urgency_correct: true, sla_met: true } },
            failurePolicy: { hard_fail: false, penalty: -0.5, log_failure: true }
        },
        {
            id: 'imaging-scan-sequence',
            name: 'Scan Sequence',
            type: 'trajectory-based',
            system: 'Philips',
            environment: 'imaging',
            version: 1,
            status: 'active',
            usedInScenarios: ['Scan Parameter Optimization', 'Imaging Workflow Routing'],
            description: 'Evaluates imaging workflow sequence efficiency. Assesses scan ordering, equipment utilization across the trajectory, and patient throughput.',
            metadata: { type: 'trajectory-based', environment: 'imaging', onFailure: 'log_and_continue', timeout: '45s' },
            logic: {
                type: 'scan_sequence_trajectory',
                trajectory_checks: {
                    throughput: { min_scans_per_hour: 3, weight: 0.4 },
                    equipment_utilization: { min_utilization: 0.7, weight: 0.3 },
                    wait_time: { max_avg_wait: 30, weight: 0.3 }
                },
                scoring: { throughput_weight: 0.4, utilization_weight: 0.3, wait_weight: 0.3 }
            },
            exampleInput: {
                trajectory: [
                    { step: 1, action: 'schedule_ct', equipment: 'CT-1', wait: 10 },
                    { step: 2, action: 'schedule_mri', equipment: 'MRI-2', wait: 25 },
                    { step: 3, action: 'schedule_xray', equipment: 'XR-1', wait: 5 }
                ]
            },
            exampleOutput: { verdict: 'pass', score: 0.84, details: { throughput: 4.0, utilization: 0.78, avg_wait: 13.3 } },
            failurePolicy: { hard_fail: false, penalty: -0.3, log_failure: true }
        },
        {
            id: 'imaging-ai-judge',
            name: 'Imaging AI Judge',
            type: 'llm-judge',
            system: 'Philips',
            environment: 'imaging',
            version: 1,
            status: 'active',
            usedInScenarios: ['Imaging Order Prioritization', 'AI-Assisted Diagnostics'],
            description: 'LLM-based assessment of imaging order appropriateness. Evaluates whether imaging decisions match clinical indications and follow ACR guidelines.',
            metadata: { type: 'llm-judge', environment: 'imaging', onFailure: 'return_low_score', timeout: '120s' },
            logic: {
                type: 'imaging_llm_judge',
                model: 'gpt-4.1-mini',
                scoring: 'absolute',
                output_range: [0, 1],
                judge_prompt: 'You are an imaging order evaluator. Assess the agent\'s prioritization decisions for:\n1. Clinical appropriateness of imaging modality selection\n2. Urgency classification accuracy\n3. Equipment utilization efficiency\n4. Patient throughput optimization\n\nReturn a score between 0 and 1.'
            },
            exampleInput: {
                orders: [{ id: 'ORD-1', modality: 'CT', indication: 'chest pain', urgency: 'STAT' }],
                decisions: [{ order: 'ORD-1', scheduled: true, equipment: 'CT-1', wait_minutes: 8 }]
            },
            exampleOutput: { score: 0.88, rationale: 'STAT chest pain CT appropriately prioritized with minimal wait time.' },
            failurePolicy: { hard_fail: false, penalty: 0.0, log_failure: true }
        }
    ];

    // ── Change Healthcare Revenue Cycle Verifiers (3) ───────────────────
    const revenueVerifiers = [
        {
            id: 'revenue-billing-compliance',
            name: 'Billing Compliance',
            type: 'rule-based',
            system: 'Change Healthcare',
            environment: 'revenue_cycle',
            version: 1,
            status: 'active',
            usedInScenarios: ['Patient Billing Prioritization', 'Contract Compliance Scoring'],
            description: 'Validates billing code sequences and pre-authorization rules. Ensures correct billing codes, pre-auth verification, and compliance with payer contracts.',
            metadata: { type: 'rule-based', environment: 'revenue_cycle', onFailure: 'log_and_continue', timeout: '30s' },
            logic: {
                type: 'billing_compliance_validator',
                checks: {
                    billing_code_validity: { must_be_valid_cpt: true, weight: 0.4 },
                    pre_auth_check: { required_for_high_value: true, threshold: 1000, weight: 0.3 },
                    contract_compliance: { must_match_payer_terms: true, weight: 0.3 }
                },
                scoring: { code_weight: 0.4, preauth_weight: 0.3, contract_weight: 0.3 }
            },
            exampleInput: {
                claim: { cpt_code: '99213', amount: 250, payer: 'BlueCross', pre_auth: false },
                action: { prioritized: true, submitted: true }
            },
            exampleOutput: { verdict: 'pass', score: 0.90, details: { code_valid: true, preauth_ok: true, contract_compliant: true } },
            failurePolicy: { hard_fail: true, penalty: -1.0, log_failure: true }
        },
        {
            id: 'revenue-claims-sequence',
            name: 'Claims Sequence',
            type: 'trajectory-based',
            system: 'Change Healthcare',
            environment: 'revenue_cycle',
            version: 1,
            status: 'active',
            usedInScenarios: ['Claims Rejection Recovery', 'Denial Appeals Sequencing', 'Payment Reconciliation'],
            description: 'Evaluates end-to-end claims processing trajectory. Scores claim submission ordering, denial follow-up timing, and recovery rate.',
            metadata: { type: 'trajectory-based', environment: 'revenue_cycle', onFailure: 'log_and_continue', timeout: '60s' },
            logic: {
                type: 'claims_sequence_trajectory',
                trajectory_checks: {
                    submission_order: { high_value_first: true, weight: 0.3 },
                    denial_followup: { max_days_to_appeal: 30, weight: 0.4 },
                    recovery_rate: { min_recovery: 0.7, weight: 0.3 }
                },
                scoring: { ordering_weight: 0.3, followup_weight: 0.4, recovery_weight: 0.3 }
            },
            exampleInput: {
                trajectory: [
                    { step: 1, action: 'submit_claim', claim_value: 5000, result: { accepted: false, denial_code: 'CO-4' } },
                    { step: 2, action: 'appeal_denial', result: { appeal_submitted: true, days_elapsed: 5 } },
                    { step: 3, action: 'resubmit_claim', result: { accepted: true, amount_recovered: 4500 } }
                ]
            },
            exampleOutput: { verdict: 'pass', score: 0.86, details: { ordering: 0.9, followup_timing: 0.95, recovery: 0.90 } },
            failurePolicy: { hard_fail: false, penalty: -0.5, log_failure: true }
        },
        {
            id: 'revenue-ai-judge',
            name: 'Revenue AI Judge',
            type: 'llm-judge',
            system: 'Change Healthcare',
            environment: 'revenue_cycle',
            version: 1,
            status: 'active',
            usedInScenarios: ['Revenue Forecast Simulation', 'Insurance Plan Matching'],
            description: 'LLM-based assessment of revenue cycle decisions. Evaluates billing priorities, denial management strategies, and financial optimization.',
            metadata: { type: 'llm-judge', environment: 'revenue_cycle', onFailure: 'return_low_score', timeout: '120s' },
            logic: {
                type: 'revenue_llm_judge',
                model: 'gpt-4.1-mini',
                scoring: 'absolute',
                output_range: [0, 1],
                judge_prompt: 'You are a revenue cycle evaluator. Assess the agent\'s billing and claims decisions for:\n1. Billing code accuracy and appropriateness\n2. Claims prioritization strategy\n3. Denial management effectiveness\n4. Revenue optimization\n\nReturn a score between 0 and 1.'
            },
            exampleInput: {
                claims: [{ id: 'CLM-1', amount: 3500, status: 'denied' }],
                decisions: [{ claim: 'CLM-1', action: 'appeal', appeal_basis: 'medical_necessity' }]
            },
            exampleOutput: { score: 0.85, rationale: 'Appropriate appeal strategy for medical necessity denial with supporting documentation.' },
            failurePolicy: { hard_fail: false, penalty: 0.0, log_failure: true }
        }
    ];

    // ── Health Catalyst Population Health Verifiers (2) ─────────────────
    const populationHealthVerifiers = [
        {
            id: 'pophealth-outreach-compliance',
            name: 'Outreach Compliance',
            type: 'rule-based',
            system: 'Health Catalyst',
            environment: 'population_health',
            version: 1,
            status: 'active',
            usedInScenarios: ['Chronic Disease Outreach', 'High-Risk Patient Engagement'],
            description: 'Validates outreach workflow steps. Ensures patient risk stratification, appropriate contact method, and follow-up scheduling.',
            metadata: { type: 'rule-based', environment: 'population_health', onFailure: 'log_and_continue', timeout: '30s' },
            logic: {
                type: 'outreach_compliance_validator',
                checks: {
                    risk_stratification: { must_be_performed: true, weight: 0.4 },
                    contact_method: { must_match_preference: true, weight: 0.3 },
                    followup_scheduled: { must_be_within_days: 14, weight: 0.3 }
                },
                scoring: { risk_weight: 0.4, contact_weight: 0.3, followup_weight: 0.3 }
            },
            exampleInput: {
                patient: { risk_level: 'high', preferred_contact: 'phone' },
                action: { contact_method: 'phone', followup_days: 7 }
            },
            exampleOutput: { verdict: 'pass', score: 0.92, details: { risk_checked: true, contact_matched: true, followup_ok: true } },
            failurePolicy: { hard_fail: false, penalty: -0.5, log_failure: true }
        },
        {
            id: 'pophealth-trajectory',
            name: 'Population Health Trajectory',
            type: 'trajectory-based',
            system: 'Health Catalyst',
            environment: 'population_health',
            version: 1,
            status: 'active',
            usedInScenarios: ['Preventive Screening Policy', 'Vaccination Drive Prioritization'],
            description: 'Evaluates patient engagement sequences across the population health trajectory. Scores outreach timing, engagement rate, and outcome improvements.',
            metadata: { type: 'trajectory-based', environment: 'population_health', onFailure: 'log_and_continue', timeout: '45s' },
            logic: {
                type: 'population_health_trajectory',
                trajectory_checks: {
                    engagement_rate: { min_rate: 0.6, weight: 0.4 },
                    outcome_improvement: { min_improvement: 0.1, weight: 0.4 },
                    cost_efficiency: { max_cost_per_patient: 200, weight: 0.2 }
                },
                scoring: { engagement_weight: 0.4, outcome_weight: 0.4, cost_weight: 0.2 }
            },
            exampleInput: {
                trajectory: [
                    { step: 1, action: 'identify_cohort', result: { patients: 500, high_risk: 75 } },
                    { step: 2, action: 'outreach_campaign', result: { contacted: 450, engaged: 310 } },
                    { step: 3, action: 'followup_assessment', result: { improved: 280, cost_total: 45000 } }
                ]
            },
            exampleOutput: { verdict: 'pass', score: 0.85, details: { engagement: 0.69, improvement: 0.90, cost_per_patient: 90 } },
            failurePolicy: { hard_fail: false, penalty: -0.3, log_failure: true }
        }
    ];

    // ── Veeva/IQVIA Clinical Trials Verifiers (2) ───────────────────────
    const clinicalTrialsVerifiers = [
        {
            id: 'trials-protocol-compliance',
            name: 'Trial Protocol Compliance',
            type: 'rule-based',
            system: 'Veeva',
            environment: 'clinical_trials',
            version: 1,
            status: 'active',
            usedInScenarios: ['Adaptive Cohort Allocation', 'Trial Protocol Optimization'],
            description: 'Validates protocol adherence rules for clinical trials. Ensures eligibility criteria are met, randomization is correct, and dosing follows the protocol.',
            metadata: { type: 'rule-based', environment: 'clinical_trials', onFailure: 'log_and_continue', timeout: '30s' },
            logic: {
                type: 'trial_protocol_compliance_validator',
                checks: {
                    eligibility: { must_meet_criteria: true, weight: 0.4 },
                    randomization: { must_follow_scheme: true, weight: 0.3 },
                    dosing_adherence: { max_deviation: 0.1, weight: 0.3 }
                },
                scoring: { eligibility_weight: 0.4, randomization_weight: 0.3, dosing_weight: 0.3 }
            },
            exampleInput: {
                patient: { age: 45, condition: 'type_2_diabetes', eligible: true },
                action: { arm: 'treatment', dose: 100, protocol_dose: 100 }
            },
            exampleOutput: { verdict: 'pass', score: 0.96, details: { eligible: true, randomization_ok: true, dose_deviation: 0.0 } },
            failurePolicy: { hard_fail: true, penalty: -1.0, log_failure: true }
        },
        {
            id: 'trials-enrollment-trajectory',
            name: 'Trial Enrollment Trajectory',
            type: 'trajectory-based',
            system: 'Veeva',
            environment: 'clinical_trials',
            version: 1,
            status: 'active',
            usedInScenarios: ['Enrollment Funnel Optimization', 'Patient Retention Sequencing'],
            description: 'Evaluates enrollment funnel sequence. Scores screening efficiency, enrollment conversion rate, and retention across the trial trajectory.',
            metadata: { type: 'trajectory-based', environment: 'clinical_trials', onFailure: 'log_and_continue', timeout: '45s' },
            logic: {
                type: 'enrollment_trajectory',
                trajectory_checks: {
                    screening_efficiency: { min_screen_to_enroll: 0.3, weight: 0.35 },
                    enrollment_rate: { target_per_month: 10, weight: 0.35 },
                    retention: { min_retention: 0.85, weight: 0.3 }
                },
                scoring: { screening_weight: 0.35, enrollment_weight: 0.35, retention_weight: 0.3 }
            },
            exampleInput: {
                trajectory: [
                    { step: 1, action: 'screen_patients', result: { screened: 50, eligible: 20 } },
                    { step: 2, action: 'enroll_patients', result: { enrolled: 15, conversion: 0.75 } },
                    { step: 3, action: 'retention_check', result: { active: 14, dropped: 1 } }
                ]
            },
            exampleOutput: { verdict: 'pass', score: 0.87, details: { screening_eff: 0.40, enrollment: 15, retention: 0.93 } },
            failurePolicy: { hard_fail: false, penalty: -0.5, log_failure: true }
        }
    ];

    // ── HIL (Human-in-the-Loop) Verifiers ──────────────────────────────
    const hilVerifiers = [
        {
            id: 'hil-jira-resolution',
            name: 'HIL: Jira Resolution Review',
            type: 'human-eval',
            system: 'Jira',
            environment: 'jira',
            version: 1,
            status: 'active',
            usedInScenarios: ['Issue Resolution Flow'],
            description: 'Human-in-the-loop evaluation of Jira issue resolution. A human reviewer assesses the agent trajectory for correctness, completeness, and quality before training can proceed.',
            metadata: { type: 'human-eval', environment: 'jira', onFailure: 'block_training', timeout: 'manual' },
            logic: {
                type: 'human_evaluation',
                criteria: ['Tool usage correctness', 'Workflow compliance', 'Resolution quality'],
                scoring: 'manual',
                output_range: [0, 1]
            },
            exampleInput: { trajectory: ['get_issue_summary_and_description', 'get_transitions', 'transition_issue'] },
            exampleOutput: { verdict: 'pass', score: 0.9, reviewer_comments: 'Correct sequence, valid transition used.' },
            failurePolicy: { hard_fail: true, penalty: 0.0, log_failure: true },
            subVerifiers: []
        },
        {
            id: 'hil-clinical-treatment',
            name: 'HIL: Treatment Pathway Review',
            type: 'human-eval',
            system: 'Epic',
            environment: 'clinical',
            version: 1,
            status: 'active',
            usedInScenarios: ['Treatment Pathway Optimization'],
            description: 'Human reviewer evaluates RL agent treatment recommendations for clinical appropriateness, safety, and guideline adherence.',
            metadata: { type: 'human-eval', environment: 'clinical', onFailure: 'block_training', timeout: 'manual' },
            logic: {
                type: 'human_evaluation',
                criteria: ['Clinical safety', 'Guideline adherence', 'Treatment appropriateness'],
                scoring: 'manual',
                output_range: [0, 1]
            },
            exampleInput: { trajectory: ['assess_patient', 'prescribe_treatment', 'schedule_followup'] },
            exampleOutput: { verdict: 'pass', score: 0.85, reviewer_comments: 'Safe treatment plan.' },
            failurePolicy: { hard_fail: true, penalty: 0.0, log_failure: true },
            subVerifiers: []
        },
        {
            id: 'hil-adp-worker',
            name: 'HIL: ADP Worker Review',
            type: 'human-eval',
            system: 'ADP',
            environment: 'hr_payroll',
            version: 1,
            status: 'active',
            usedInScenarios: ['Create Worker & Assign'],
            description: 'Human review of ADP worker creation and assignment trajectories. Validates compliance with HR policies and data accuracy.',
            metadata: { type: 'human-eval', environment: 'hr_payroll', onFailure: 'block_training', timeout: 'manual' },
            logic: {
                type: 'human_evaluation',
                criteria: ['Data accuracy', 'Policy compliance', 'Workflow correctness'],
                scoring: 'manual',
                output_range: [0, 1]
            },
            exampleInput: { trajectory: ['get_pay_group', 'build_worker_payload', 'post_worker'] },
            exampleOutput: { verdict: 'pass', score: 0.92, reviewer_comments: 'Correct pay group and worker data.' },
            failurePolicy: { hard_fail: true, penalty: 0.0, log_failure: true },
            subVerifiers: []
        },
        {
            id: 'hil-workday-record',
            name: 'HIL: Workday Record Review',
            type: 'human-eval',
            system: 'Workday',
            environment: 'hr_payroll',
            version: 1,
            status: 'active',
            usedInScenarios: ['Workday Create Worker Record'],
            description: 'Human review of Workday record creation workflows for data integrity and compliance.',
            metadata: { type: 'human-eval', environment: 'hr_payroll', onFailure: 'block_training', timeout: 'manual' },
            logic: {
                type: 'human_evaluation',
                criteria: ['Record completeness', 'Org structure compliance', 'Data validity'],
                scoring: 'manual',
                output_range: [0, 1]
            },
            exampleInput: { trajectory: ['get_supervisory_org', 'build_worker_payload', 'post_worker'] },
            exampleOutput: { verdict: 'pass', score: 0.88, reviewer_comments: 'Worker record created correctly.' },
            failurePolicy: { hard_fail: true, penalty: 0.0, log_failure: true },
            subVerifiers: []
        },
        {
            id: 'hil-imaging-review',
            name: 'HIL: Imaging Order Review',
            type: 'human-eval',
            system: 'Philips',
            environment: 'imaging',
            version: 1,
            status: 'active',
            usedInScenarios: ['Imaging Order Prioritization'],
            description: 'Human radiologist reviews RL agent imaging order priorities for clinical appropriateness and urgency accuracy.',
            metadata: { type: 'human-eval', environment: 'imaging', onFailure: 'block_training', timeout: 'manual' },
            logic: {
                type: 'human_evaluation',
                criteria: ['Priority accuracy', 'Clinical appropriateness', 'Resource efficiency'],
                scoring: 'manual',
                output_range: [0, 1]
            },
            exampleInput: { trajectory: ['prioritize_stat', 'schedule_ct', 'defer_routine'] },
            exampleOutput: { verdict: 'pass', score: 0.91, reviewer_comments: 'Correct priority assignment.' },
            failurePolicy: { hard_fail: true, penalty: 0.0, log_failure: true },
            subVerifiers: []
        },
        {
            id: 'hil-revenue-cycle',
            name: 'HIL: Revenue Cycle Review',
            type: 'human-eval',
            system: 'Change Healthcare',
            environment: 'revenue_cycle',
            version: 1,
            status: 'active',
            usedInScenarios: ['Claims Processing'],
            description: 'Human review of billing and claims decisions for coding accuracy, compliance, and revenue optimization.',
            metadata: { type: 'human-eval', environment: 'revenue_cycle', onFailure: 'block_training', timeout: 'manual' },
            logic: {
                type: 'human_evaluation',
                criteria: ['Coding accuracy', 'Compliance adherence', 'Revenue optimization'],
                scoring: 'manual',
                output_range: [0, 1]
            },
            exampleInput: { trajectory: ['validate_codes', 'check_auth', 'submit_claim'] },
            exampleOutput: { verdict: 'pass', score: 0.87, reviewer_comments: 'Codes valid, auth confirmed.' },
            failurePolicy: { hard_fail: true, penalty: 0.0, log_failure: true },
            subVerifiers: []
        }
    ];

    // ── Combine all verifiers ───────────────────────────────────────────
    var ALL_VERIFIERS = [].concat(
        jiraVerifiers,
        adpVerifiers,
        workdayVerifiers,
        sapVerifiers,
        clinicalVerifiers,
        imagingVerifiers,
        revenueVerifiers,
        populationHealthVerifiers,
        clinicalTrialsVerifiers,
        hilVerifiers
    );

    // ── System metadata ─────────────────────────────────────────────────
    var VERIFIER_SYSTEMS = [
        { system: 'Jira', description: 'Validate Jira issue workflows', category: 'jira' },
        { system: 'ADP', description: 'Validate ADP HR & payroll workflows', category: 'hr_payroll' },
        { system: 'Workday', description: 'Validate Workday HR workflows', category: 'hr_payroll' },
        { system: 'SAP SuccessFactors', description: 'Validate SAP HR workflows', category: 'hr_payroll' },
        { system: 'Epic', description: 'Validate clinical treatment workflows', category: 'clinical' },
        { system: 'Philips', description: 'Validate imaging & radiology workflows', category: 'imaging' },
        { system: 'Change Healthcare', description: 'Validate revenue cycle workflows', category: 'revenue_cycle' },
        { system: 'Health Catalyst', description: 'Validate population health workflows', category: 'population_health' },
        { system: 'Veeva', description: 'Validate clinical trials workflows', category: 'clinical_trials' }
    ];

    // ── Category → system mapping ───────────────────────────────────────
    var CATEGORY_TO_SYSTEM = {
        'jira': 'Jira',
        'hr_payroll': 'ADP',           // default; UI will show all HR systems
        'clinical': 'Epic',
        'imaging': 'Philips',
        'revenue_cycle': 'Change Healthcare',
        'population_health': 'Health Catalyst',
        'clinical_trials': 'Veeva',
        'hospital_operations': 'Epic',
        'telehealth': 'Epic',
        'interoperability': 'Epic',
        'cross_workflow': 'Epic'
    };

    // ── Helper functions ────────────────────────────────────────────────

    /** Get all verifiers for a given system name */
    function getVerifiersBySystem(system) {
        if (!system || system === 'all') return ALL_VERIFIERS.slice();
        return ALL_VERIFIERS.filter(function (v) { return v.system === system; });
    }

    /** Get all verifiers matching a type */
    function getVerifiersByType(type) {
        if (!type || type === 'all') return ALL_VERIFIERS.slice();
        return ALL_VERIFIERS.filter(function (v) { return v.type === type; });
    }

    /** Get a single verifier by ID */
    function getVerifierById(id) {
        return ALL_VERIFIERS.find(function (v) { return v.id === id; }) || null;
    }

    /** Get verifier group summaries (system + count) */
    function getVerifierGroups() {
        return VERIFIER_SYSTEMS.map(function (s) {
            var count = ALL_VERIFIERS.filter(function (v) { return v.system === s.system; }).length;
            return { system: s.system, count: count, description: s.description, category: s.category };
        });
    }

    /** Map environment category to default verifier system */
    function getSystemForCategory(category) {
        return CATEGORY_TO_SYSTEM[category] || 'Epic';
    }

    /** Get all systems that serve a given category (for HR which has ADP, Workday, SAP) */
    function getSystemsForCategory(category) {
        return VERIFIER_SYSTEMS
            .filter(function (s) { return s.category === category; })
            .map(function (s) { return s.system; });
    }

    /** Add a new verifier to the runtime list */
    function addVerifier(verifier) {
        ALL_VERIFIERS.push(verifier);
    }

    /** Generate a unique verifier ID */
    function generateVerifierId() {
        return 'custom-' + Date.now() + '-' + Math.random().toString(36).substr(2, 6);
    }

    // ── Expose on window ────────────────────────────────────────────────
    window.VERIFIER_DATA = {
        all: ALL_VERIFIERS,
        systems: VERIFIER_SYSTEMS,
        categoryToSystem: CATEGORY_TO_SYSTEM,
        getBySystem: getVerifiersBySystem,
        getByType: getVerifiersByType,
        getById: getVerifierById,
        getGroups: getVerifierGroups,
        getSystemForCategory: getSystemForCategory,
        getSystemsForCategory: getSystemsForCategory,
        add: addVerifier,
        generateId: generateVerifierId
    };
})();
