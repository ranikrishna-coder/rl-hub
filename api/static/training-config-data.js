/**
 * Training Configuration Data
 * Environments are loaded dynamically from GET /environments API.
 * Scenarios, agents, algorithms, and training runs are hardcoded.
 * Future: Replace all with fetch to GET /api/training/config
 */
(function () {
    'use strict';

    window.TRAINING_CONFIG = {
        // Environments loaded dynamically — see training.js loadEnvironments()
        environments: [],

        scenarios: [
            // Default scenarios — one per category
            { id: 'sc_jira_1', name: 'Jira Issue Resolution', category: 'jira', task_count: 5, description: 'Resolve a Jira issue by transitioning through correct statuses',
              expected_workflow: ['jira_get_issue', 'jira_transition_issue', 'jira_add_comment', 'jira_update_fields', 'jira_resolve_issue'] },

            { id: 'sc_epic_1', name: 'Clinical Workflow', category: 'clinical', task_count: 3, description: 'Search and retrieve patient records, place clinical orders in Epic EHR',
              expected_workflow: ['fhir_patient_search', 'fhir_patient_read', 'fhir_encounter_search'] },

            { id: 'sc_img_1', name: 'Imaging Workflow', category: 'imaging', task_count: 5, description: 'Schedule and prioritize radiology imaging orders',
              expected_workflow: ['pacs_query_worklist', 'pacs_check_availability', 'pacs_schedule_exam', 'pacs_assign_priority', 'pacs_confirm_booking'] },

            { id: 'sc_rev_1', name: 'Revenue Cycle Workflow', category: 'revenue_cycle', task_count: 6, description: 'Recover rejected insurance claims through workflow automation',
              expected_workflow: ['claims_get_rejection', 'claims_analyze_denial_code', 'claims_correct_coding', 'claims_resubmit_claim', 'claims_track_status', 'claims_update_account'] },

            { id: 'sc_pop_1', name: 'Population Health Workflow', category: 'population_health', task_count: 6, description: 'Manage outreach campaigns for chronic disease patients',
              expected_workflow: ['registry_query_patients', 'risk_stratify_cohort', 'outreach_generate_list', 'outreach_assign_care_manager', 'outreach_send_notification', 'outreach_track_engagement'] },

            { id: 'sc_ct_1', name: 'Clinical Trials Workflow', category: 'clinical_trials', task_count: 5, description: 'Dynamically allocate patients to clinical trial cohorts',
              expected_workflow: ['trial_screen_eligibility', 'trial_evaluate_criteria', 'trial_randomize_arm', 'trial_enroll_subject', 'trial_update_registry'] },

            { id: 'sc_hr_1', name: 'HR & Payroll Workflow', category: 'hr_payroll', task_count: 10, description: 'Complete employee onboarding workflow across ADP, Workday, SAP',
              expected_workflow: ['hr_create_employee', 'hr_assign_role', 'hr_setup_benefits', 'hr_provision_access', 'hr_assign_training', 'hr_schedule_orientation'] },

            { id: 'sc_tele_1', name: 'Telehealth Workflow', category: 'telehealth', task_count: 4, description: 'Route patients to appropriate telehealth providers',
              expected_workflow: ['tele_triage_request', 'tele_match_provider', 'tele_check_availability', 'tele_schedule_visit'] },

            { id: 'sc_hosp_1', name: 'Hospital Operations Workflow', category: 'hospital_operations', task_count: 5, description: 'Optimize hospital staff allocation across units',
              expected_workflow: ['staffing_get_census', 'staffing_evaluate_acuity', 'staffing_calculate_ratios', 'staffing_assign_nurses', 'staffing_notify_staff'] },

            { id: 'sc_inter_1', name: 'Interoperability Workflow', category: 'interoperability', task_count: 7, description: 'Reconcile patient data across disparate systems',
              expected_workflow: ['interop_query_source_a', 'interop_query_source_b', 'interop_match_records', 'interop_resolve_conflicts', 'interop_merge_demographics', 'interop_update_master', 'interop_audit_log'] },

            { id: 'sc_cross_1', name: 'Cross-Workflow Orchestration', category: 'cross_workflow', task_count: 9, description: 'Optimize end-to-end patient journey across departments',
              expected_workflow: ['admission_register', 'triage_assess', 'lab_order_create', 'imaging_schedule', 'pharmacy_dispense', 'care_plan_update', 'discharge_prepare', 'follow_up_schedule', 'billing_finalize'] },

            // ClinKriya Clinic (MedAgentBench) scenarios — keyed by environment name
            { id: 'sc_ck_7', name: 'Prolonged QT Management', environment: 'ClinKriya Clinic', category: 'clinical', task_count: 12, description: 'Monitor QTc interval, review current medications, and decide on clinical action using FHIR observation and medication data. Training task for GRPO run.',
              expected_workflow: ['fhir_observation_search', 'fhir_medication_request_search', 'evaluate_qtc_risk', 'fhir_create_service_request', 'fhir_create_medication_request'] },
            { id: 'sc_ck_3', name: 'Blood Pressure Recording', environment: 'ClinKriya Clinic', category: 'clinical', task_count: 8, description: 'Record a vital-signs blood pressure observation (118/77 mmHg) for a patient encounter by posting a FHIR Observation resource.',
              expected_workflow: ['fhir_patient_search', 'fhir_encounter_search', 'fhir_create_observation'] },
            { id: 'sc_ck_8', name: 'Orthopedic Referral', environment: 'ClinKriya Clinic', category: 'clinical', task_count: 10, description: 'Create an urgent FHIR ServiceRequest for orthopedic consultation following ACL tear assessment using SNOMED referral code.',
              expected_workflow: ['fhir_patient_search', 'fhir_condition_search', 'fhir_create_service_request'] },
            { id: 'sc_ck_10', name: 'A1C Lab Order', environment: 'ClinKriya Clinic', category: 'clinical', task_count: 7, description: 'Order hemoglobin A1C lab test (LOINC 4548-4) for diabetic patient management by creating a stat FHIR ServiceRequest.',
              expected_workflow: ['fhir_patient_search', 'fhir_condition_search', 'fhir_create_service_request'] },
        ],

        agents: [
            { id: 'agent_qwen06', name: 'Qwen3 0.6B', base_model: 'Qwen/Qwen3-0.6B', trainable: true, compatible_categories: ['dev-sim', 'jira'] },
            { id: 'agent_qwen17', name: 'Qwen 1.7B Instruct', base_model: 'qwen-1.7b-instruct', trainable: true, compatible_categories: ['jira', 'hr_payroll', 'imaging', 'dev-sim'] },
            { id: 'agent_llama32', name: 'LLaMA 3.2 1B', base_model: 'llama-3.2-1b', trainable: true, compatible_categories: ['jira', 'clinical', 'telehealth', 'dev-sim'] },
            { id: 'agent_mistral', name: 'Mistral 7B Instruct', base_model: 'mistral-7b-instruct-v0.3', trainable: true, compatible_categories: ['jira', 'clinical', 'imaging', 'revenue_cycle', 'hr_payroll', 'population_health', 'clinical_trials', 'hospital_operations', 'interoperability', 'telehealth', 'cross_workflow', 'dev-sim'] },
            { id: 'agent_gpt4o', name: 'GPT-4o (Baseline)', base_model: 'gpt-4o', trainable: false, compatible_categories: ['jira', 'clinical', 'imaging', 'revenue_cycle', 'hr_payroll', 'population_health', 'clinical_trials', 'hospital_operations', 'interoperability', 'telehealth', 'cross_workflow', 'dev-sim'] },
        ],

        algorithms: [
            { id: 'GRPO', name: 'GRPO', description: 'Group Relative Policy Optimization — optimizes relative trajectory rankings', recommended: true },
            { id: 'PPO', name: 'PPO', description: 'Proximal Policy Optimization — general-purpose RL algorithm', recommended: false },
            { id: 'DPO', name: 'DPO', description: 'Direct Preference Optimization — learns from preference pairs', recommended: false },
            { id: 'A2C', name: 'A2C', description: 'Advantage Actor-Critic — synchronous policy gradient method', recommended: false },
        ],

        // Training runs — 2 demo runs + dynamically populated from backend via /api/training/jobs
        trainingRuns: [
            {
                id: 'run_grpo_ck_001',
                job_id: 'run_grpo_ck_001',
                name: 'train_clinkriya_grpo_2026_03_07',
                description: 'GRPO + LoRA training on ClinKriya Clinic \u2013 PCP clinical task suite (vitals, labs, referrals, medication management)',
                status: 'completed',
                environment: 'ClinKriya Clinic',
                environmentDisplay: 'ClinKriya Clinic',
                category: 'huggingface',
                model: 'qwen2.5-7b-instruct',
                algorithm: 'GRPO',
                progress: 100,
                started: 'Mar 7, 2026',
                completed: 'Mar 8, 2026',
                episodes: 50,
                successRate: 80.0,
                avgReward: 1.300,
                baselineReward: 1.057,
                results: {
                    mean_reward: 1.300,
                    max_reward: 1.500,
                    min_reward: -0.350,
                    total_episodes: 50,
                    episodes_completed: 50
                },
                baseline_results: {
                    mean_reward: 1.057,
                    max_reward: 1.500,
                    min_reward: -0.050,
                    episodes: 1
                },
                model_saved: true,
                model_url: '/workspace/Healthcare/rl_output/run_20260307_044232/checkpoints/final',
                model_metadata: {
                    job_id: 'run_grpo_ck_001',
                    environment_name: 'ClinKriya Clinic',
                    algorithm: 'GRPO',
                    lora: true,
                    num_epochs: 50,
                    group_size: 64,
                    mean_reward: 1.300,
                    eval_pass_rate: 0.80,
                    eval_mean_reward: 1.040,
                    training_completed: true,
                    timestamp: '2026-03-08T06:00:00Z'
                },
                hil_required: false,
                human_evaluations: [],
                _mock_baseline_rollout: {
                    id: 'bl_ck_001',
                    environment_name: 'ClinKriya Clinic',
                    episode_number: 0,
                    total_reward: -0.05,
                    total_steps: 6,
                    status: 'completed',
                    source: 'training',
                    policy_name: 'qwen2.5-7b-instruct',
                    checkpoint_label: 'base',
                    scenario_name: 'Prolonged QT Management (task7_5)',
                    steps: [
                        { step: 1, action: 'fhir_observation_search', reward: 0.20,
                          timeline_events: [
                            { timestamp_ms: 0, event_type: 'SYSTEM', content: 'Task: Evaluate prolonged QT management for Patient/S2090974' },
                            { timestamp_ms: 312, event_type: 'TOOL_CALL', tool_name: 'fhir_observation_search', tool_args: { code: 'QTCINTERVAL', patient: 'Patient/S2090974' } },
                            { timestamp_ms: 580, event_type: 'TOOL_RESULT', content: 'QTc interval: 428 ms' }
                          ]
                        },
                        { step: 2, action: 'fhir_medication_request_search', reward: 0.00,
                          timeline_events: [
                            { timestamp_ms: 750, event_type: 'TOOL_CALL', tool_name: 'fhir_medication_request_search', tool_args: { patient: 'Patient/S2090974' } },
                            { timestamp_ms: 980, event_type: 'TOOL_RESULT', content: 'Active meds: VENLAFAXINE 37.5mg, FLUOROMETHOLONE 0.1%, ZYRTEC 10mg' }
                          ]
                        },
                        { step: 3, action: 'fhir_medication_request_search', reward: 0.00,
                          timeline_events: [
                            { timestamp_ms: 1200, event_type: 'MODEL_THOUGHT', content: 'QTc is 428ms (< 500ms threshold). Will still check meds again and order ECG.' },
                            { timestamp_ms: 1450, event_type: 'TOOL_CALL', tool_name: 'fhir_medication_request_search', tool_args: { patient: 'Patient/S2090974' } }
                          ]
                        },
                        { step: 4, action: 'fhir_service_request_create', reward: -0.40,
                          timeline_events: [
                            { timestamp_ms: 1700, event_type: 'TOOL_CALL', tool_name: 'fhir_service_request_create', tool_args: { code: '445118002', display: '12-lead electrocardiogram', patient: 'Patient/S2090974' } },
                            { timestamp_ms: 1900, event_type: 'TOOL_RESULT', content: 'ServiceRequest created (spurious \u2014 QTc normal, ECG not indicated)' }
                          ]
                        },
                        { step: 5, action: null, reward: -0.10,
                          timeline_events: [
                            { timestamp_ms: 2100, event_type: 'TOOL_CALL', tool_name: 'fhir_observation_search', tool_args: { code: 'QTCINTERVAL', patient: 'Patient/S2090974' } },
                            { timestamp_ms: 2350, event_type: 'TOOL_RESULT', content: 'QTc: 428 ms (repeated lookup \u2014 invalid FHIR call)' }
                          ]
                        },
                        { step: 6, action: null, reward: 0.00,
                          timeline_events: [
                            { timestamp_ms: 2500, event_type: 'MODEL_THOUGHT', content: 'Episode truncated without calling finish().' }
                          ]
                        }
                    ],
                    final_outcome: { reward: -0.05, steps: 6, resolved: false },
                    final_environment_state: { qtc_ms: 428, threshold_ms: 500, drug_stopped: false, ecg_ordered: true, terminal_pass: false },
                    verifier_results: [
                        { check: 'QTc lookup', passed: true, detail: 'fhir_observation_search(QTCINTERVAL) called correctly' },
                        { check: 'Threshold evaluation', passed: false, detail: 'Model did not call finish() with correct assessment' },
                        { check: 'Spurious action penalty', passed: false, detail: 'ECG ordered unnecessarily when QTc < 500ms' },
                        { check: 'Invalid FHIR call', passed: false, detail: 'Redundant observation search penalised' }
                    ]
                },
                _mock_trained_rollout: {
                    id: 'tr_ck_001',
                    environment_name: 'ClinKriya Clinic',
                    episode_number: 49,
                    total_reward: 1.30,
                    total_steps: 2,
                    status: 'completed',
                    source: 'training',
                    policy_name: 'qwen2.5-7b-instruct',
                    checkpoint_label: 'clinkriya_grpo_epoch_50',
                    scenario_name: 'Prolonged QT Management (task7_12)',
                    steps: [
                        { step: 1, action: 'fhir_observation_search', reward: 0.20,
                          timeline_events: [
                            { timestamp_ms: 0, event_type: 'SYSTEM', content: 'Task: Evaluate prolonged QT management for Patient/S2090974' },
                            { timestamp_ms: 88, event_type: 'TOOL_CALL', tool_name: 'fhir_observation_search', tool_args: { code: 'QTCINTERVAL', patient: 'Patient/S2090974' } },
                            { timestamp_ms: 210, event_type: 'TOOL_RESULT', content: 'QTc interval: 428 ms (below 500ms threshold)' }
                          ]
                        },
                        { step: 2, action: 'finish', reward: 1.10,
                          timeline_events: [
                            { timestamp_ms: 290, event_type: 'MODEL_THOUGHT', content: 'QTc is 428ms which is below the 500ms threshold. No drug discontinuation or ECG order required.' },
                            { timestamp_ms: 360, event_type: 'TOOL_CALL', tool_name: 'finish', tool_args: { answer: [428] } },
                            { timestamp_ms: 440, event_type: 'TOOL_RESULT', content: 'Episode complete \u2014 PASS: correct QTc reported, no spurious actions' }
                          ]
                        }
                    ],
                    final_outcome: { reward: 1.30, steps: 2, resolved: true },
                    final_environment_state: { qtc_ms: 428, threshold_ms: 500, drug_stopped: false, ecg_ordered: false, terminal_pass: true },
                    verifier_results: [
                        { check: 'QTc lookup', passed: true, detail: 'fhir_observation_search(QTCINTERVAL) called on first turn' },
                        { check: 'Threshold evaluation', passed: true, detail: 'finish([428]) called with correct QTc value' },
                        { check: 'No spurious actions', passed: true, detail: 'No unnecessary drug stops or ECG orders' },
                        { check: 'Efficiency', passed: true, detail: 'Task resolved in 2 turns' }
                    ]
                },
                _episodes: [
                    {
                        epoch: 1, task_id: 'task7_5', mean_reward: 1.057, pass_rate: 76.6,
                        rollouts: [
                            { idx: 63, rollout_id: 'R-04', label: 'Optimal \u2014 Clean Trajectory', train_step: 3200,
                              reward: 1.50, pass: true,  turns: 3, advantage: 0.671,
                              tools: ['fhir_observation_search', 'calculator', 'finish'],
                              episode_rewards: { qtc_lookup: 0.2, threshold_eval: 0.3, ecg_order: 0.0, drug_stop: 0.0, terminal: 1.0, spurious_action: 0.0, invalid_fhir: 0.0, coupled_missing: 0.0 } },
                            { idx: 0,  rollout_id: 'R-03', label: 'Near-Optimal', train_step: 2400,
                              reward: 1.40, pass: true,  turns: 3, advantage: 0.5195,
                              tools: ['fhir_observation_search', 'fhir_observation_search'],
                              episode_rewards: { qtc_lookup: 0.2, threshold_eval: 0.3, ecg_order: 0.0, drug_stop: 0.0, terminal: 1.0, spurious_action: 0.0, invalid_fhir: -0.1, coupled_missing: 0.0 } },
                            { idx: 33, rollout_id: 'R-01', label: 'Threshold Hallucination', train_step: 800,
                              reward: 0.05, pass: false, turns: 5, advantage: -1.5255,
                              tools: ['fhir_observation_search', 'fhir_observation_search', 'fhir_medication_request_search', 'fhir_service_request_create'],
                              episode_rewards: { qtc_lookup: 0.2, threshold_eval: 0.0, ecg_order: 0.25, drug_stop: 0.0, terminal: 0.0, spurious_action: -0.4, invalid_fhir: 0.0, coupled_missing: 0.0 } },
                            { idx: 21, rollout_id: 'R-02', label: 'Reasoning\u2013Action Gap', train_step: 1600,
                              reward: -0.25, pass: false, turns: 6, advantage: -1.98,
                              tools: ['fhir_observation_search', 'fhir_observation_search', 'calculator', 'fhir_service_request_create', 'fhir_service_request_create'],
                              episode_rewards: { qtc_lookup: 0.2, threshold_eval: 0.0, ecg_order: 0.25, drug_stop: 0.0, terminal: 0.0, spurious_action: -0.4, invalid_fhir: -0.3, coupled_missing: 0.0 } },
                            { idx: 30, rollout_id: 'R-00', label: 'Catastrophic Failure', train_step: 0,
                              reward: -0.35, pass: false, turns: 9, advantage: -2.1314,
                              tools: ['fhir_observation_search', 'fhir_observation_search', 'fhir_medication_request_search', 'fhir_medication_request_search', 'fhir_service_request_create', 'fhir_service_request_create'],
                              episode_rewards: { qtc_lookup: 0.2, threshold_eval: 0.0, ecg_order: 0.25, drug_stop: 0.0, terminal: 0.0, spurious_action: -0.4, invalid_fhir: -0.4, coupled_missing: 0.0 } }
                        ]
                    },
                    {
                        epoch: 15, task_id: 'task7_3', mean_reward: 1.152, pass_rate: 100.0,
                        rollouts: [
                            { idx: 2,  reward: 1.50, pass: true, turns: 3, tools: ['fhir_observation_search', 'calculator', 'finish'],
                              episode_rewards: { qtc_lookup: 0.2, threshold_eval: 0.3, ecg_order: 0.0, drug_stop: 0.0, terminal: 1.0, spurious_action: 0.0, invalid_fhir: 0.0, coupled_missing: 0.0 } },
                            { idx: 7,  reward: 1.50, pass: true, turns: 3, tools: ['fhir_observation_search', 'fhir_observation_search', 'finish'],
                              episode_rewards: { qtc_lookup: 0.2, threshold_eval: 0.3, ecg_order: 0.0, drug_stop: 0.0, terminal: 1.0, spurious_action: 0.0, invalid_fhir: 0.0, coupled_missing: 0.0 } },
                            { idx: 11, reward: 1.40, pass: true, turns: 3, tools: ['fhir_observation_search', 'fhir_observation_search', 'finish'],
                              episode_rewards: { qtc_lookup: 0.2, threshold_eval: 0.3, ecg_order: 0.0, drug_stop: 0.0, terminal: 1.0, spurious_action: 0.0, invalid_fhir: -0.1, coupled_missing: 0.0 } },
                            { idx: 19, reward: 1.30, pass: true, turns: 2, tools: ['fhir_observation_search', 'finish'],
                              episode_rewards: { qtc_lookup: 0.2, threshold_eval: 0.3, ecg_order: 0.0, drug_stop: 0.0, terminal: 1.0, spurious_action: 0.0, invalid_fhir: -0.2, coupled_missing: 0.0 } },
                            { idx: 25, reward: 1.30, pass: true, turns: 2, tools: ['fhir_observation_search', 'finish'],
                              episode_rewards: { qtc_lookup: 0.2, threshold_eval: 0.3, ecg_order: 0.0, drug_stop: 0.0, terminal: 1.0, spurious_action: 0.0, invalid_fhir: -0.2, coupled_missing: 0.0 } }
                        ]
                    },
                    {
                        epoch: 50, task_id: 'task7_12', mean_reward: 1.300, pass_rate: 100.0,
                        rollouts: [
                            { idx: 0,  reward: 1.30, pass: true, turns: 2, tools: ['fhir_observation_search', 'finish'],
                              episode_rewards: { qtc_lookup: 0.2, threshold_eval: 0.3, ecg_order: 0.0, drug_stop: 0.0, terminal: 1.0, spurious_action: 0.0, invalid_fhir: -0.2, coupled_missing: 0.0 } },
                            { idx: 1,  reward: 1.30, pass: true, turns: 2, tools: ['fhir_observation_search', 'finish'],
                              episode_rewards: { qtc_lookup: 0.2, threshold_eval: 0.3, ecg_order: 0.0, drug_stop: 0.0, terminal: 1.0, spurious_action: 0.0, invalid_fhir: -0.2, coupled_missing: 0.0 } },
                            { idx: 2,  reward: 1.30, pass: true, turns: 2, tools: ['fhir_observation_search', 'finish'],
                              episode_rewards: { qtc_lookup: 0.2, threshold_eval: 0.3, ecg_order: 0.0, drug_stop: 0.0, terminal: 1.0, spurious_action: 0.0, invalid_fhir: -0.2, coupled_missing: 0.0 } },
                            { idx: 3,  reward: 1.30, pass: true, turns: 2, tools: ['fhir_observation_search', 'finish'],
                              episode_rewards: { qtc_lookup: 0.2, threshold_eval: 0.3, ecg_order: 0.0, drug_stop: 0.0, terminal: 1.0, spurious_action: 0.0, invalid_fhir: -0.2, coupled_missing: 0.0 } },
                            { idx: 4,  reward: 1.30, pass: true, turns: 2, tools: ['fhir_observation_search', 'finish'],
                              episode_rewards: { qtc_lookup: 0.2, threshold_eval: 0.3, ecg_order: 0.0, drug_stop: 0.0, terminal: 1.0, spurious_action: 0.0, invalid_fhir: -0.2, coupled_missing: 0.0 } }
                        ]
                    }
                ]
            },
            {
                id: 'run_grpo_001',
                job_id: 'run_grpo_001',
                name: 'train_jira_grpo_2026_01_15',
                description: 'GRPO training on Jira Issue Resolution',
                status: 'completed',
                environment: 'JiraIssueResolution',
                environmentDisplay: 'Jira Issue Resolution',
                category: 'jira',
                model: 'qwen-1.7b-instruct',
                algorithm: 'GRPO',
                progress: 100,
                started: 'Jan 15, 2026',
                completed: 'Jan 16, 2026',
                episodes: 320,
                successRate: 85.6,
                avgReward: 0.63,
                baselineReward: 0.22,
                results: {
                    mean_reward: 0.63,
                    max_reward: 0.91,
                    min_reward: 0.04,
                    total_episodes: 320,
                    episodes_completed: 320
                },
                baseline_results: {
                    mean_reward: 0.22,
                    max_reward: 0.38,
                    min_reward: 0.02,
                    episodes: 5
                },
                model_saved: true,
                model_url: '/models/grpo/JiraIssueResolution_run_grpo_001.zip',
                model_metadata: {
                    job_id: 'run_grpo_001',
                    environment_name: 'JiraIssueResolution',
                    algorithm: 'GRPO',
                    num_episodes: 320,
                    mean_reward: 0.63,
                    max_reward: 0.91,
                    min_reward: 0.04,
                    total_episodes_completed: 320,
                    training_completed: true,
                    timestamp: '2026-01-16T08:42:00Z'
                },
                hil_required: false,
                human_evaluations: [],
                _mock_baseline_rollout: {
                    id: 'bl_mock_001',
                    environment_name: 'JiraIssueResolution',
                    episode_number: 0,
                    total_reward: 0.12,
                    total_steps: 3,
                    status: 'completed',
                    source: 'training',
                    policy_name: 'qwen-1.7b-instruct',
                    checkpoint_label: 'base',
                    scenario_name: 'Resolve Jira ticket ISK2',
                    steps: [
                        { step: 1, action: null, reward: 0.02,
                          timeline_events: [
                            { timestamp_ms: 0, event_type: 'SYSTEM', content: 'User request received: "Resolve Jira ticket ISK2"' },
                            { timestamp_ms: 412, event_type: 'MODEL_THOUGHT', content: 'Need to resolve the ticket.' }
                          ]
                        },
                        { step: 2, action: null, reward: 0.05,
                          timeline_events: [
                            { timestamp_ms: 913, event_type: 'MODEL_THOUGHT', content: 'Should check possible transitions.' }
                          ]
                        },
                        { step: 3, action: null, reward: 0.05,
                          timeline_events: [
                            { timestamp_ms: 1284, event_type: 'MODEL_THOUGHT', content: 'No further action taken.' }
                          ]
                        }
                    ],
                    final_outcome: { reward: 0.12, steps: 3, resolved: false },
                    final_environment_state: { issue_key: 'ISK2', status: 'In Progress' },
                    verifier_results: [
                        { check: 'Tool Sequence Validator', passed: false, detail: 'No tool calls observed' },
                        { check: 'Transition Validator', passed: false, detail: 'transition_issue was never invoked' }
                    ]
                },
                _mock_trained_rollout: {
                    id: 'tr_mock_001',
                    environment_name: 'JiraIssueResolution',
                    episode_number: 287,
                    total_reward: 0.91,
                    total_steps: 3,
                    status: 'completed',
                    source: 'training',
                    policy_name: 'qwen-1.7b-instruct',
                    checkpoint_label: 'jira_grpo_step_300',
                    scenario_name: 'Resolve Jira ticket ISK2',
                    steps: [
                        { step: 1, action: 'get_issue_summary_and_description', reward: 0.15,
                          timeline_events: [
                            { timestamp_ms: 0, event_type: 'SYSTEM', content: 'User request received: "Resolve Jira ticket ISK2"' },
                            { timestamp_ms: 88, event_type: 'TOOL_CALL', tool_name: 'get_issue_summary_and_description', tool_args: { issue_key: 'ISK2' } },
                            { timestamp_ms: 168, event_type: 'TOOL_RESULT', content: 'ISK-2: "Login page error" \u2014 Status: Open, Priority: High' }
                          ]
                        },
                        { step: 2, action: 'get_transitions', reward: 0.20,
                          timeline_events: [
                            { timestamp_ms: 248, event_type: 'TOOL_CALL', tool_name: 'get_transitions', tool_args: { issue_key: 'ISK2' } },
                            { timestamp_ms: 338, event_type: 'TOOL_RESULT', content: 'valid_transitions:\n  - id: 61\n    name: Done' }
                          ]
                        },
                        { step: 3, action: 'transition_issue', reward: 0.56,
                          timeline_events: [
                            { timestamp_ms: 418, event_type: 'TOOL_CALL', tool_name: 'transition_issue', tool_args: { issue_key: 'ISK2', transition_id: '61' } },
                            { timestamp_ms: 508, event_type: 'TOOL_RESULT', content: 'Status changed: Open \u2192 In Progress' },
                            { timestamp_ms: 588, event_type: 'TOOL_CALL', tool_name: 'get_transitions', tool_args: { issue_key: 'ISK2' } },
                            { timestamp_ms: 658, event_type: 'TOOL_RESULT', content: 'valid_transitions:\n  - id: 61\n    name: Done' },
                            { timestamp_ms: 738, event_type: 'TOOL_CALL', tool_name: 'transition_issue', tool_args: { issue_key: 'ISK2', transition_id: '61' } },
                            { timestamp_ms: 828, event_type: 'TOOL_RESULT', content: 'Status changed: In Progress \u2192 Done' }
                          ]
                        }
                    ],
                    final_outcome: { reward: 0.91, steps: 3, resolved: true },
                    final_environment_state: { issue_status: 'Done', resolution: 'Fixed', comments: 0 },
                    verifier_results: [
                        { check: 'Tool sequence order', passed: true, detail: 'get_issue \u2192 get_transitions \u2192 transition_issue \u2014 correct order' },
                        { check: 'Valid transitions only', passed: true, detail: 'All transition_ids from get_transitions result' },
                        { check: 'Issue resolved', passed: true, detail: 'Issue moved to Done status' }
                    ]
                }
            },
            {
                id: 'run_grpo_sre_001',
                job_id: 'run_grpo_sre_001',
                name: 'train_sre_03_12',
                description: 'GRPO + LoRA on OOMKilled scenario \u2014 K8s memory-limit remediation with Qwen3-0.6B',
                status: 'completed',
                environment: 'sre 24*7',
                environmentDisplay: 'SRE 24*7',
                category: 'dev-sim',
                model: 'Qwen/Qwen3-0.6B',
                algorithm: 'GRPO',
                progress: 100,
                started: 'Mar 12, 2026',
                completed: 'Mar 12, 2026',
                episodes: 20,
                successRate: 100,
                avgReward: 3.10,
                baselineReward: 3.05,
                results: {
                    mean_reward: 3.10,
                    max_reward: 3.05,
                    min_reward: 1.25,
                    total_episodes: 6,
                    episodes_completed: 6,
                    eval_episodes: 1,
                    eval_resolve_rate: 1.0,
                    training_mean_reward: 2.475,
                    training_resolve_rate: 1.0
                },
                baseline_results: {
                    mean_reward: 3.05,
                    max_reward: 3.05,
                    min_reward: 3.05,
                    episodes: 3,
                    resolve_rate: 0.667
                },
                model_saved: true,
                model_url: 'outputs/k8s-sre-grpo-Qwen-Qwen3-0.6B-2026-03-11_00-35-44/checkpoint-10',
                model_metadata: {
                    job_id: 'run_grpo_sre_001',
                    environment_name: 'sre 24*7',
                    algorithm: 'GRPO',
                    lora: true,
                    lora_r: 16,
                    num_epochs: 20,
                    total_steps: 10,
                    total_tokens: 143159,
                    training_duration_s: 2897.6,
                    group_size: 2,
                    mean_reward: 2.475,
                    eval_pass_rate: 1.0,
                    eval_mean_reward: 3.10,
                    training_completed: true,
                    timestamp: '2026-03-12T01:24:24Z'
                },
                hil_required: false,
                human_evaluations: [],
                _training_metrics: {
                    per_step: [
                        { step: 1, epoch: 0.1, loss: -0.1456, reward_mean: 1.75, kl: 0.0, entropy: 0.343, grad_norm: 0.441, lr: 0.0, completion_len: 115.5 },
                        { step: 2, epoch: 0.2, loss: 0.0, reward_mean: -0.30, kl: 0.0, entropy: 0.215, grad_norm: 0.0, lr: 1e-6, completion_len: 143.0 },
                        { step: 3, epoch: 0.3, loss: 0.0, reward_mean: -0.95, kl: 0.001, entropy: 0.158, grad_norm: 0.007, lr: 2e-6, completion_len: 90.0 },
                        { step: 4, epoch: 0.4, loss: 0.0, reward_mean: -0.55, kl: 0.001, entropy: 0.152, grad_norm: 0.007, lr: 1.92e-6, completion_len: 139.0 },
                        { step: 5, epoch: 0.5, loss: 0.0, reward_mean: -0.55, kl: 0.002, entropy: 0.361, grad_norm: 0.006, lr: 1.71e-6, completion_len: 156.5 },
                        { step: 6, epoch: 0.6, loss: 0.0, reward_mean: 0.25, kl: 0.001, entropy: 0.132, grad_norm: 0.004, lr: 1.38e-6, completion_len: 153.5 },
                        { step: 7, epoch: 0.7, loss: 0.0, reward_mean: -0.95, kl: 0.001, entropy: 0.058, grad_norm: 0.003, lr: 1e-6, completion_len: 140.5 },
                        { step: 8, epoch: 0.8, loss: 0.0139, reward_mean: -1.10, kl: 0.002, entropy: 0.193, grad_norm: 0.033, lr: 6.17e-7, completion_len: 108.5 },
                        { step: 9, epoch: 0.9, loss: 0.0, reward_mean: 0.10, kl: 0.001, entropy: 0.082, grad_norm: 0.003, lr: 2.93e-7, completion_len: 164.5 },
                        { step: 10, epoch: 1.0, loss: 0.0, reward_mean: 0.10, kl: 0.001, entropy: 0.198, grad_norm: 0.005, lr: 7.61e-8, completion_len: 91.0 }
                    ],
                    per_episode: [
                        { episode: 1, reward: 2.55, diagnosis: -0.5, fix: 3.05 },
                        { episode: 2, reward: -1.60, diagnosis: 0.0, fix: 0.0 },
                        { episode: 3, reward: -0.30, diagnosis: 0.0, fix: 0.0 },
                        { episode: 4, reward: -0.30, diagnosis: 0.0, fix: 0.0 },
                        { episode: 5, reward: -0.60, diagnosis: 0.0, fix: 0.0 },
                        { episode: 6, reward: -1.30, diagnosis: 0.0, fix: 0.0 },
                        { episode: 7, reward: -0.30, diagnosis: 0.0, fix: 0.0 },
                        { episode: 8, reward: -0.80, diagnosis: 0.0, fix: 0.0 },
                        { episode: 9, reward: -0.80, diagnosis: 0.0, fix: 0.0 },
                        { episode: 10, reward: -0.30, diagnosis: 0.0, fix: 0.0 },
                        { episode: 11, reward: 0.30, diagnosis: 0.0, fix: 0.0 },
                        { episode: 12, reward: -0.30, diagnosis: 0.0, fix: 0.5 },
                        { episode: 13, reward: -0.80, diagnosis: -0.5, fix: 0.0 },
                        { episode: 14, reward: -0.60, diagnosis: 0.0, fix: 0.0 },
                        { episode: 15, reward: -0.80, diagnosis: 0.0, fix: 0.0 },
                        { episode: 16, reward: -1.40, diagnosis: 0.0, fix: 0.0 },
                        { episode: 17, reward: -0.30, diagnosis: 0.0, fix: 0.0 },
                        { episode: 18, reward: 0.00, diagnosis: 0.0, fix: 0.5 },
                        { episode: 19, reward: -0.30, diagnosis: 0.0, fix: 0.0 },
                        { episode: 20, reward: 0.10, diagnosis: 0.4, fix: 0.0 }
                    ]
                },
                _mock_baseline_rollout: {
                    id: 'bl_sre_001',
                    environment_name: 'sre 24*7',
                    episode_number: 0,
                    total_reward: 3.05,
                    total_steps: 2,
                    status: 'completed',
                    source: 'eval',
                    policy_name: 'Qwen/Qwen3-0.6B',
                    checkpoint_label: 'base',
                    scenario_name: 'OOMKilled \u2014 payment-api pods in hackathon namespace',
                    steps: [
                        {
                            step: 1, action: 'diagnose', reward: 0.0,
                            timeline_events: [
                                { timestamp_ms: 0, event_type: 'SYSTEM', content: 'CRITICAL: payment-api pods OOMKilled in hackathon namespace' },
                                { timestamp_ms: 450, event_type: 'TOOL_CALL', tool_name: 'diagnose', tool_args: { text: 'OOMKilled for payment-api pods in namespace "hackathon"' } },
                                { timestamp_ms: 680, event_type: 'TOOL_RESULT', content: 'Diagnosis submitted' }
                            ]
                        },
                        {
                            step: 2, action: 'set_resources', reward: 3.05,
                            timeline_events: [
                                { timestamp_ms: 900, event_type: 'MODEL_THOUGHT', content: 'OOMKilled means memory limit exceeded. Need to increase memory limits for the deployment.' },
                                { timestamp_ms: 1200, event_type: 'TOOL_CALL', tool_name: 'set_resources', tool_args: { namespace: 'hackathon', deploymentName: 'payment-api', containerName: 'payment-api', memoryLimit: '128Mi' } },
                                { timestamp_ms: 1500, event_type: 'TOOL_RESULT', content: 'Resources updated. 3/3 pods healthy. Incident resolved.' }
                            ]
                        }
                    ],
                    final_outcome: { reward: 3.05, steps: 2, resolved: true },
                    final_environment_state: { fault_type: 'oom_kill', namespace: 'hackathon', deployment: 'payment-api', pods_healthy: true, incident_resolved: true },
                    verifier_results: [
                        { check: 'Diagnostic flow', passed: true, detail: 'diagnose() called with correct fault identification' },
                        { check: 'Namespace correctness', passed: false, detail: 'Used hackathon namespace (not payments)' },
                        { check: 'Fix command correctness', passed: true, detail: 'set_resources with correct memory limit applied' },
                        { check: 'Pod health', passed: true, detail: '3/3 pods Running after fix' },
                        { check: 'Repetition penalty', passed: true, detail: 'No repeated commands' }
                    ]
                },
                _mock_trained_rollout: {
                    id: 'tr_sre_001',
                    environment_name: 'sre 24*7',
                    episode_number: 8,
                    total_reward: 3.10,
                    total_steps: 2,
                    status: 'completed',
                    source: 'eval',
                    policy_name: 'Qwen/Qwen3-0.6B',
                    checkpoint_label: 'sre_grpo_step_10',
                    scenario_name: 'OOMKilled \u2014 payment-api pods in payments namespace',
                    steps: [
                        {
                            step: 1, action: 'diagnose', reward: 0.0,
                            timeline_events: [
                                { timestamp_ms: 0, event_type: 'SYSTEM', content: 'CRITICAL: payment-api pods OOMKilled in payments namespace' },
                                { timestamp_ms: 320, event_type: 'TOOL_CALL', tool_name: 'diagnose', tool_args: { text: 'OOMKilled for payment-api in payments namespace \u2014 memory limit exceeded' } },
                                { timestamp_ms: 510, event_type: 'TOOL_RESULT', content: 'Diagnosis submitted' }
                            ]
                        },
                        {
                            step: 2, action: 'set_resources', reward: 3.10,
                            timeline_events: [
                                { timestamp_ms: 650, event_type: 'MODEL_THOUGHT', content: 'OOMKilled \u2192 increase memory limits. kubectl set resources deployment/payment-api --limits=memory=256Mi -n payments' },
                                { timestamp_ms: 880, event_type: 'TOOL_CALL', tool_name: 'set_resources', tool_args: { namespace: 'payments', deploymentName: 'payment-api', containerName: 'payment-api', memoryLimit: '256Mi' } },
                                { timestamp_ms: 1100, event_type: 'TOOL_RESULT', content: 'Resources updated. 3/3 pods healthy. Incident resolved in 2 turns. Optimal memory limit chosen.' }
                            ]
                        }
                    ],
                    final_outcome: { reward: 3.10, steps: 2, resolved: true },
                    final_environment_state: { fault_type: 'oom_kill', namespace: 'payments', deployment: 'payment-api', pods_healthy: true, incident_resolved: true },
                    verifier_results: [
                        { check: 'Diagnostic flow', passed: true, detail: 'diagnose() called with correct OOMKilled identification' },
                        { check: 'Namespace correctness', passed: true, detail: 'Correct namespace: payments' },
                        { check: 'Fix command correctness', passed: true, detail: 'set_resources with correct deployment and memory limit' },
                        { check: 'Pod health', passed: true, detail: '3/3 pods Running after fix' },
                        { check: 'Repetition penalty', passed: true, detail: 'No repeated commands' }
                    ]
                },
                _episodes: [
                    {
                        epoch: 1, task_id: 'ImagePullBackOff_frontend', mean_reward: -0.125, pass_rate: 0.0,
                        rollouts: [
                            {
                                idx: 0, reward: -0.125, pass: false, turns: 16, tools: ['diagnose', 'set_image', 'get_pod_status', 'get_pod_status', 'get_pod_status', 'get_pod_status', 'get_pod_status', 'get_pod_status', 'get_pod_status', 'get_pod_status', 'get_pod_status', 'get_pod_status', 'get_pod_status', 'get_pod_status', 'get_pod_status', 'get_pod_status'],
                                episode_rewards: { diagnostic_flow: 0.0, repetition_penalty: 0.0, pod_health: 0.0, namespace_correctness: 1.0, fix_command_correctness: 0.3 }
                            }
                        ]
                    },
                    {
                        epoch: 2, task_id: 'OOMKilled_payments', mean_reward: 1.525, pass_rate: 100.0,
                        rollouts: [
                            {
                                idx: 0, reward: 1.525, pass: true, turns: 2, tools: ['diagnose', 'set_resources'],
                                episode_rewards: { diagnostic_flow: 0.1, repetition_penalty: 1.0, pod_health: 1.0, namespace_correctness: 1.0, fix_command_correctness: 1.0 }
                            }
                        ]
                    },
                    {
                        epoch: 4, task_id: 'OOMKilled_payments_v2', mean_reward: 1.275, pass_rate: 100.0,
                        rollouts: [
                            {
                                idx: 0, reward: 1.275, pass: true, turns: 2, tools: ['diagnose', 'set_resources'],
                                episode_rewards: { diagnostic_flow: 0.1, repetition_penalty: 1.0, pod_health: 1.0, namespace_correctness: 1.0, fix_command_correctness: 0.8 }
                            },
                            {
                                idx: 1, reward: 1.525, pass: true, turns: 2, tools: ['diagnose', 'set_resources'],
                                episode_rewards: { diagnostic_flow: 0.1, repetition_penalty: 1.0, pod_health: 1.0, namespace_correctness: 1.0, fix_command_correctness: 1.0 }
                            }
                        ]
                    },
                    {
                        epoch: 6, task_id: 'OOMKilled_hackathon', mean_reward: 1.525, pass_rate: 100.0,
                        rollouts: [
                            {
                                idx: 0, reward: 1.525, pass: true, turns: 2, tools: ['diagnose', 'set_resources'],
                                episode_rewards: { diagnostic_flow: 0.1, repetition_penalty: 1.0, pod_health: 1.0, namespace_correctness: 0.0, fix_command_correctness: 1.0 }
                            }
                        ]
                    },
                    {
                        epoch: 7, task_id: 'ImagePullBackOff_frontend_v2', mean_reward: 0.475, pass_rate: 100.0,
                        rollouts: [
                            {
                                idx: 0, reward: 0.475, pass: true, turns: 5, tools: ['diagnose', 'get_pod_status', 'set_image', 'get_pod_status', 'get_pod_status'],
                                episode_rewards: { diagnostic_flow: 0.3, repetition_penalty: 0.5, pod_health: 1.0, namespace_correctness: 1.0, fix_command_correctness: 0.8 }
                            }
                        ]
                    },
                    {
                        epoch: 8, task_id: 'OOMKilled_payments_v3', mean_reward: 1.525, pass_rate: 100.0,
                        rollouts: [
                            {
                                idx: 0, reward: 1.525, pass: true, turns: 2, tools: ['diagnose', 'set_resources'],
                                episode_rewards: { diagnostic_flow: 0.1, repetition_penalty: 1.0, pod_health: 1.0, namespace_correctness: 1.0, fix_command_correctness: 1.0 }
                            }
                        ]
                    }
                ]
            }
        ],

        // Archived mock data (kept for reference, not loaded)
        _archivedMockRuns: [
            {
                id: 'run_grpo_001',
                job_id: 'run_grpo_001',
                name: 'train_jira_grpo_2026_01_15',
                description: 'GRPO training on Jira Issue Resolution',
                status: 'completed',
                environment: 'JiraIssueResolution',
                environmentDisplay: 'Jira Issue Resolution',
                category: 'jira',
                model: 'qwen-1.7b-instruct',
                algorithm: 'GRPO',
                progress: 100,
                started: 'Jan 15, 2026',
                completed: 'Jan 16, 2026',
                episodes: 320,
                successRate: 85.6,
                avgReward: 0.63,
                baselineReward: 0.22,
                results: {
                    mean_reward: 0.63,
                    max_reward: 0.91,
                    min_reward: 0.04,
                    total_episodes: 320,
                    episodes_completed: 320
                },
                baseline_results: {
                    mean_reward: 0.22,
                    max_reward: 0.38,
                    min_reward: 0.02,
                    episodes: 5
                },
                model_saved: true,
                model_url: '/models/grpo/JiraIssueResolution_run_grpo_001.zip',
                model_metadata: {
                    job_id: 'run_grpo_001',
                    environment_name: 'JiraIssueResolution',
                    algorithm: 'GRPO',
                    num_episodes: 320,
                    mean_reward: 0.63,
                    max_reward: 0.91,
                    min_reward: 0.04,
                    total_episodes_completed: 320,
                    training_completed: true,
                    timestamp: '2026-01-16T08:42:00Z'
                },
                hil_required: false,
                human_evaluations: [],
                _mock_baseline_rollout: {
                    id: 'bl_mock_001',
                    environment_name: 'JiraIssueResolution',
                    episode_number: 0,
                    total_reward: 0.12,
                    total_steps: 3,
                    status: 'completed',
                    source: 'training',
                    policy_name: 'qwen-1.7b-instruct',
                    checkpoint_label: 'base',
                    scenario_name: 'Resolve Jira ticket ISK2',
                    steps: [
                        { step: 1, action: null, reward: 0.02,
                          timeline_events: [
                            { timestamp_ms: 0, event_type: 'SYSTEM', content: 'User request received: "Resolve Jira ticket ISK2"' },
                            { timestamp_ms: 412, event_type: 'MODEL_THOUGHT', content: 'Need to resolve the ticket.' }
                          ]
                        },
                        { step: 2, action: null, reward: 0.05,
                          timeline_events: [
                            { timestamp_ms: 913, event_type: 'MODEL_THOUGHT', content: 'Should check possible transitions.' }
                          ]
                        },
                        { step: 3, action: null, reward: 0.05,
                          timeline_events: [
                            { timestamp_ms: 1284, event_type: 'MODEL_THOUGHT', content: 'No further action taken.' }
                          ]
                        }
                    ],
                    final_outcome: { reward: 0.12, steps: 3, resolved: false },
                    final_environment_state: { issue_key: 'ISK2', status: 'In Progress' },
                    verifier_results: [
                        { check: 'Tool Sequence Validator', passed: false, detail: 'No tool calls observed' },
                        { check: 'Transition Validator', passed: false, detail: 'transition_issue was never invoked' }
                    ]
                },
                _mock_trained_rollout: {
                    id: 'tr_mock_001',
                    environment_name: 'JiraIssueResolution',
                    episode_number: 287,
                    total_reward: 0.91,
                    total_steps: 3,
                    status: 'completed',
                    source: 'training',
                    policy_name: 'qwen-1.7b-instruct',
                    checkpoint_label: 'jira_grpo_step_300',
                    scenario_name: 'Resolve Jira ticket ISK2',
                    steps: [
                        { step: 1, action: 'get_issue_summary_and_description', reward: 0.15,
                          timeline_events: [
                            { timestamp_ms: 0, event_type: 'SYSTEM', content: 'User request received: "Resolve Jira ticket ISK2"' },
                            { timestamp_ms: 88, event_type: 'TOOL_CALL', tool_name: 'get_issue_summary_and_description', tool_args: { issue_key: 'ISK2' } },
                            { timestamp_ms: 168, event_type: 'TOOL_RESULT', content: 'ISK-2: "Login page error" \u2014 Status: Open, Priority: High' }
                          ]
                        },
                        { step: 2, action: 'get_transitions', reward: 0.20,
                          timeline_events: [
                            { timestamp_ms: 248, event_type: 'TOOL_CALL', tool_name: 'get_transitions', tool_args: { issue_key: 'ISK2' } },
                            { timestamp_ms: 338, event_type: 'TOOL_RESULT', content: 'valid_transitions:\n  - id: 61\n    name: Done' }
                          ]
                        },
                        { step: 3, action: 'transition_issue', reward: 0.56,
                          timeline_events: [
                            { timestamp_ms: 418, event_type: 'TOOL_CALL', tool_name: 'transition_issue', tool_args: { issue_key: 'ISK2', transition_id: '61' } },
                            { timestamp_ms: 508, event_type: 'TOOL_RESULT', content: 'Status changed: Open \u2192 In Progress' },
                            { timestamp_ms: 588, event_type: 'TOOL_CALL', tool_name: 'get_transitions', tool_args: { issue_key: 'ISK2' } },
                            { timestamp_ms: 658, event_type: 'TOOL_RESULT', content: 'valid_transitions:\n  - id: 61\n    name: Done' },
                            { timestamp_ms: 738, event_type: 'TOOL_CALL', tool_name: 'transition_issue', tool_args: { issue_key: 'ISK2', transition_id: '61' } },
                            { timestamp_ms: 828, event_type: 'TOOL_RESULT', content: 'Status changed: In Progress \u2192 Done' }
                          ]
                        }
                    ],
                    final_outcome: { reward: 0.91, steps: 3, resolved: true },
                    final_environment_state: { issue_status: 'Done', resolution: 'Fixed', comments: 0 },
                    verifier_results: [
                        { check: 'Tool sequence order', passed: true, detail: 'get_issue \u2192 get_transitions \u2192 transition_issue \u2014 correct order' },
                        { check: 'Valid transitions only', passed: true, detail: 'All transition_ids from get_transitions result' },
                        { check: 'Issue resolved', passed: true, detail: 'Issue moved to Done status' }
                    ]
                }
            },
            {
                id: 'run_dpo_002',
                job_id: 'run_dpo_002',
                name: 'train_jira_dpo_2026_01_08',
                description: 'DPO training on Jira Status Update',
                status: 'running',
                environment: 'JiraStatusUpdate',
                environmentDisplay: 'Jira Status Update',
                category: 'jira',
                model: 'llama-3.2-1b',
                algorithm: 'DPO',
                progress: 67,
                started: 'Jan 8, 2026',
                episodes: 214,
                successRate: null,
                avgReward: null,
                baselineReward: null,
                results: null,
                baseline_results: null,
                model_saved: false,
                model_url: null,
                hil_required: false,
                human_evaluations: []
            },
            {
                id: 'run_ppo_003',
                job_id: 'run_ppo_003',
                name: 'train_clinical_ppo_2026_02_20',
                description: 'PPO training on Treatment Pathway Optimization',
                status: 'awaiting_human_eval',
                environment: 'TreatmentPathwayOptimization',
                environmentDisplay: 'Treatment Pathway Optimization',
                category: 'clinical',
                model: 'mistral-7b-instruct-v0.3',
                algorithm: 'PPO',
                progress: 100,
                started: 'Feb 20, 2026',
                completed: 'Feb 21, 2026',
                episodes: 200,
                successRate: 72.4,
                avgReward: 0.51,
                baselineReward: 0.18,
                results: {
                    mean_reward: 0.51,
                    max_reward: 0.78,
                    min_reward: 0.03,
                    total_episodes: 200,
                    episodes_completed: 200
                },
                baseline_results: {
                    mean_reward: 0.18,
                    max_reward: 0.31,
                    min_reward: 0.01,
                    episodes: 5
                },
                model_saved: true,
                model_url: '/models/ppo/TreatmentPathwayOptimization_run_ppo_003.zip',
                model_metadata: {
                    job_id: 'run_ppo_003',
                    environment_name: 'TreatmentPathwayOptimization',
                    algorithm: 'PPO',
                    num_episodes: 200,
                    mean_reward: 0.51,
                    total_episodes_completed: 200,
                    training_completed: true
                },
                hil_required: true,
                human_evaluations: []
            },
        ],
    };
})();
