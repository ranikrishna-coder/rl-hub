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
            { id: 'sc_jira_1', name: 'Resolve Jira ticket ISK2', category: 'jira', task_count: 5, description: 'Resolve a Jira issue by transitioning through correct statuses' },
            { id: 'sc_jira_2', name: 'Jira Status Update Workflow', category: 'jira', task_count: 3, description: 'Update issue status following valid transition paths' },
            { id: 'sc_jira_3', name: 'Jira Subtask Management', category: 'jira', task_count: 8, description: 'Create and manage subtasks for parent issues' },
            { id: 'sc_jira_4', name: 'Jira Comment Thread', category: 'jira', task_count: 4, description: 'Add and manage comments on Jira issues' },
            { id: 'sc_epic_1', name: 'Epic Patient Lookup', category: 'clinical', task_count: 3, description: 'Search and retrieve patient records in Epic EHR' },
            { id: 'sc_epic_2', name: 'Epic Order Entry', category: 'clinical', task_count: 7, description: 'Place and manage clinical orders in Epic' },
            { id: 'sc_img_1', name: 'Radiology Scheduling', category: 'imaging', task_count: 5, description: 'Schedule and prioritize radiology imaging orders' },
            { id: 'sc_img_2', name: 'MRI Scan Scheduling', category: 'imaging', task_count: 4, description: 'Optimize MRI scan scheduling across facilities' },
            { id: 'sc_rev_1', name: 'Claims Rejection Recovery', category: 'revenue_cycle', task_count: 6, description: 'Recover rejected insurance claims through workflow automation' },
            { id: 'sc_rev_2', name: 'Pre-Authorization Workflow', category: 'revenue_cycle', task_count: 8, description: 'Automate pre-authorization requests and approvals' },
            { id: 'sc_pop_1', name: 'Chronic Disease Outreach', category: 'population_health', task_count: 6, description: 'Manage outreach campaigns for chronic disease patients' },
            { id: 'sc_ct_1', name: 'Adaptive Cohort Allocation', category: 'clinical_trials', task_count: 5, description: 'Dynamically allocate patients to clinical trial cohorts' },
            { id: 'sc_ct_2', name: 'Protocol Deviation Detection', category: 'clinical_trials', task_count: 4, description: 'Detect and handle protocol deviations in real-time' },
            { id: 'sc_hr_1', name: 'Employee Onboarding', category: 'hr_payroll', task_count: 10, description: 'Complete employee onboarding workflow' },
            { id: 'sc_hr_2', name: 'Payroll Processing', category: 'hr_payroll', task_count: 6, description: 'Process payroll across ADP, Workday, SAP systems' },
            { id: 'sc_tele_1', name: 'Virtual Visit Routing', category: 'telehealth', task_count: 4, description: 'Route patients to appropriate telehealth providers' },
            { id: 'sc_hosp_1', name: 'Staffing Allocation', category: 'hospital_operations', task_count: 5, description: 'Optimize hospital staff allocation across units' },
            { id: 'sc_inter_1', name: 'Data Reconciliation', category: 'interoperability', task_count: 7, description: 'Reconcile patient data across disparate systems' },
            { id: 'sc_cross_1', name: 'Patient Journey Optimization', category: 'cross_workflow', task_count: 9, description: 'Optimize end-to-end patient journey across departments' },
        ],

        agents: [
            { id: 'agent_qwen17', name: 'Qwen 1.7B Instruct', base_model: 'qwen-1.7b-instruct', trainable: true, compatible_categories: ['jira', 'hr_payroll', 'imaging'] },
            { id: 'agent_llama32', name: 'LLaMA 3.2 1B', base_model: 'llama-3.2-1b', trainable: true, compatible_categories: ['jira', 'clinical', 'telehealth'] },
            { id: 'agent_mistral', name: 'Mistral 7B Instruct', base_model: 'mistral-7b-instruct-v0.3', trainable: true, compatible_categories: ['jira', 'clinical', 'imaging', 'revenue_cycle', 'hr_payroll', 'population_health', 'clinical_trials', 'hospital_operations', 'interoperability', 'telehealth', 'cross_workflow'] },
            { id: 'agent_gpt4o', name: 'GPT-4o (Baseline)', base_model: 'gpt-4o', trainable: false, compatible_categories: ['jira', 'clinical', 'imaging', 'revenue_cycle', 'hr_payroll', 'population_health', 'clinical_trials', 'hospital_operations', 'interoperability', 'telehealth', 'cross_workflow'] },
        ],

        algorithms: [
            { id: 'GRPO', name: 'GRPO', description: 'Group Relative Policy Optimization — optimizes relative trajectory rankings', recommended: true },
            { id: 'PPO', name: 'PPO', description: 'Proximal Policy Optimization — general-purpose RL algorithm', recommended: false },
            { id: 'DPO', name: 'DPO', description: 'Direct Preference Optimization — learns from preference pairs', recommended: false },
            { id: 'A2C', name: 'A2C', description: 'Advantage Actor-Critic — synchronous policy gradient method', recommended: false },
        ],

        // Training runs — populated dynamically from backend via /api/training/jobs
        trainingRuns: [
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
