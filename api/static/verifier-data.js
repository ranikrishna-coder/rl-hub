/**
 * Verifier Data Layer
 * All verifier definitions for the AgentWork Simulator, grouped by system.
 * Follows the RL verifier paradigm: objective, verifiable rewards using
 * rule-based, trajectory-based, and LLM-judged approaches.
 */

(function () {
    'use strict';

    // ── Jira Verifiers (1) ──────────────────────────────────────────────
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
        }
    ];

    // ── ADP Verifiers (1) ───────────────────────────────────────────────
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
        }
    ];

    // ── Workday Verifiers (1) ───────────────────────────────────────────
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
        }
    ];

    // ── SAP SuccessFactors Verifiers (1) ────────────────────────────────
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
        }
    ];

    // ── Epic/Cerner Clinical Verifiers (1) ──────────────────────────────
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
        }
    ];

    // ── Philips/GE Imaging Verifiers (1) ────────────────────────────────
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
        }
    ];

    // ── Change Healthcare Revenue Cycle Verifiers (1) ───────────────────
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
        }
    ];

    // ── Health Catalyst Population Health Verifiers (1) ─────────────────
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
        }
    ];

    // ── Veeva/IQVIA Clinical Trials Verifiers (1) ───────────────────────
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
        }
    ];

    // ── Combine all verifiers ───────────────────────────────────────────
    // ── ClinKriya Clinic Verifiers (MedAgentBench shaped reward) ────────
    const clinKriyaVerifiers = [
        {
            id: 'ck-correctness',
            name: 'Correctness Verifier',
            type: 'rule-based',
            system: 'ClinKriya Clinic',
            environment: 'clinical',
            envName: 'ClinKriya Clinic',
            version: 1,
            status: 'active',
            usedInScenarios: ['Prolonged QT Management', 'Blood Pressure Recording', 'Orthopedic Referral', 'A1C Lab Order'],
            description: 'Binary pass/fail check against reference solutions. Contributes up to 0.40 reward. Runs the task-specific grader and awards full credit on pass.',
            metadata: { type: 'rule-based', environment: 'ClinKriya Clinic', onFailure: 'partial_credit', timeout: '10s' },
            logic: {
                type: 'refsol_binary_grader',
                checks: { refsol_pass: { weight: 0.4, grader: 'task_type_specific' } },
                scoring: { pass: 0.4, fail: 0.0 }
            },
            subVerifiers: [
                { id: 'ck-correctness-refsol', name: 'Reference Solution Match', description: 'Runs task-specific grader against agent answer', enabled: true },
                { id: 'ck-correctness-partial', name: 'Partial Field Credit', description: 'Awards partial credit for correct FHIR fields', enabled: true }
            ]
        },
        {
            id: 'ck-structure',
            name: 'FHIR Structure Verifier',
            type: 'rule-based',
            system: 'ClinKriya Clinic',
            environment: 'clinical',
            envName: 'ClinKriya Clinic',
            version: 1,
            status: 'active',
            usedInScenarios: ['Prolonged QT Management', 'Blood Pressure Recording', 'Orthopedic Referral', 'A1C Lab Order'],
            description: 'Validates that the agent POSTed to the correct FHIR endpoint and used the right resourceType. Awards up to 0.20 reward: +0.05 for correct endpoint, +0.05 for correct resourceType, +0.10 for field-level partial credit.',
            metadata: { type: 'rule-based', environment: 'ClinKriya Clinic', onFailure: 'partial_credit', timeout: '5s' },
            logic: {
                type: 'fhir_structural_validator',
                checks: {
                    endpoint_match: { expected: { task3: 'Observation', task8: 'ServiceRequest', task10: 'ServiceRequest' }, weight: 0.05 },
                    resource_type: { must_match_endpoint: true, weight: 0.05 },
                    field_partial_credit: { checker: 'task_type_field_checker', weight: 0.1 }
                }
            },
            subVerifiers: [
                { id: 'ck-struct-endpoint', name: 'Endpoint Check', description: 'POST URL targets correct FHIR resource endpoint', enabled: true },
                { id: 'ck-struct-resource', name: 'ResourceType Check', description: 'Payload resourceType matches expected FHIR type', enabled: true },
                { id: 'ck-struct-fields', name: 'Field-level Partial Credit', description: 'Scores individual required fields (status, code, date, value)', enabled: true }
            ]
        },
        {
            id: 'ck-patient-ref',
            name: 'Patient Reference Verifier',
            type: 'rule-based',
            system: 'ClinKriya Clinic',
            environment: 'clinical',
            envName: 'ClinKriya Clinic',
            version: 1,
            status: 'active',
            usedInScenarios: ['Prolonged QT Management', 'Blood Pressure Recording', 'Orthopedic Referral', 'A1C Lab Order'],
            description: 'Checks that the FHIR payload subject.reference matches the correct Patient/{MRN} for the task case. Awards 0.10 reward on match.',
            metadata: { type: 'rule-based', environment: 'ClinKriya Clinic', onFailure: 'no_credit', timeout: '2s' },
            logic: {
                type: 'patient_mrn_validator',
                checks: { subject_reference: { format: 'Patient/{eval_MRN}', weight: 0.1 } }
            },
            subVerifiers: [
                { id: 'ck-patient-mrn', name: 'MRN Match', description: 'subject.reference must equal Patient/{case_data.eval_MRN}', enabled: true }
            ]
        },
        {
            id: 'ck-efficiency',
            name: 'Efficiency Verifier',
            type: 'trajectory-based',
            system: 'ClinKriya Clinic',
            environment: 'clinical',
            envName: 'ClinKriya Clinic',
            version: 1,
            status: 'active',
            usedInScenarios: ['Prolonged QT Management', 'Orthopedic Referral', 'A1C Lab Order'],
            description: 'Rewards agents that complete tasks in fewer steps. Score = 0.10 × (1 − step_count / max_steps). Max 8 steps per episode. Also penalises redundant GET calls beyond 3 (−0.05 per extra call).',
            metadata: { type: 'trajectory-based', environment: 'ClinKriya Clinic', onFailure: 'penalty', timeout: '2s' },
            logic: {
                type: 'step_efficiency_scorer',
                checks: {
                    efficiency_bonus: { formula: '0.1 * max(0, 1 - step_count / max_steps)', max_steps: 8 },
                    redundant_gets: { threshold: 3, penalty_per_extra: -0.05 }
                }
            },
            subVerifiers: [
                { id: 'ck-eff-steps', name: 'Step Count Bonus', description: 'Fewer steps → higher reward (up to 0.10)', enabled: true },
                { id: 'ck-eff-gets', name: 'Redundant GET Penalty', description: '−0.05 per GET request beyond 3', enabled: true }
            ]
        },
        {
            id: 'ck-format',
            name: 'Action Format Verifier',
            type: 'rule-based',
            system: 'ClinKriya Clinic',
            environment: 'clinical',
            envName: 'ClinKriya Clinic',
            version: 1,
            status: 'active',
            usedInScenarios: ['Prolonged QT Management', 'Blood Pressure Recording', 'Orthopedic Referral', 'A1C Lab Order'],
            description: 'Validates that every agent action is a valid GET, POST, or FINISH call. Applies a −0.10 penalty once if any invalid action format is detected. Also awards +0.05 completion bonus when agent calls FINISH.',
            metadata: { type: 'rule-based', environment: 'ClinKriya Clinic', onFailure: 'penalty', timeout: '2s' },
            logic: {
                type: 'action_format_validator',
                checks: {
                    valid_actions: { allowed: ['GET', 'POST', 'FINISH'], penalty: -0.1, once_per_episode: true },
                    finish_bonus: { reward: 0.05, condition: 'agent_answer is not None' }
                }
            },
            subVerifiers: [
                { id: 'ck-fmt-action', name: 'Valid Action Format', description: 'Checks every agent message starts with GET / POST / FINISH', enabled: true },
                { id: 'ck-fmt-finish', name: 'Completion Bonus', description: '+0.05 when agent explicitly calls FINISH', enabled: true }
            ]
        }
    ];

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
        hilVerifiers,
        clinKriyaVerifiers
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
