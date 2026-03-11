// Environment Catalog Application

// API Base URL - auto-detected or set by config.js
// This will use window.API_BASE which is set by the auto-detection script in index.html
const API_BASE = window.API_BASE || (() => {
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') return 'http://localhost:8000';
    return window.location.origin;
})();
let allEnvironments = [];
let filteredEnvironments = [];

// Environment metadata with details
const environmentDetails = {
    'TreatmentPathwayOptimization': {
        category: 'clinical',
        system: 'Epic, Cerner, Allscripts',
        description: 'Optimizes treatment sequences for patients with multiple conditions, balancing clinical outcomes, efficiency, and cost-effectiveness.',
        stateFeatures: 20,
        actionType: 'Discrete',
        actionSpace: 6,
        kpis: ['Risk Score', 'Pathway Length', 'Cost Effectiveness', 'Treatment Efficiency'],
        useCase: 'Complex patient cases requiring coordinated multi-step treatment plans'
    },
    'SepsisEarlyIntervention': {
        category: 'clinical',
        system: 'Epic, Cerner',
        description: 'Early detection and intervention for sepsis cases using SOFA scores and vital signs monitoring.',
        stateFeatures: 18,
        actionType: 'Discrete',
        actionSpace: 5,
        kpis: ['SOFA Score', 'Mortality Risk', 'Time to Antibiotics', 'Bundle Compliance'],
        useCase: 'Critical care units, emergency departments'
    },
    'ICUResourceAllocation': {
        category: 'clinical',
        system: 'Epic, Cerner, Meditech',
        description: 'Optimally allocates ICU beds and staff resources based on patient acuity and resource availability.',
        stateFeatures: 22,
        actionType: 'Discrete',
        actionSpace: 6,
        kpis: ['ICU Occupancy', 'Queue Length', 'Bed Utilization', 'Staff Utilization'],
        useCase: 'Intensive care units, resource management'
    },
    'ImagingOrderPrioritization': {
        category: 'imaging',
        system: 'Philips, GE Healthcare',
        description: 'Prioritizes imaging orders based on clinical urgency, equipment availability, and patient needs.',
        stateFeatures: 20,
        actionType: 'Discrete',
        actionSpace: 5,
        kpis: ['Urgent Orders Waiting', 'Queue Length', 'Equipment Utilization'],
        useCase: 'Radiology departments, imaging centers'
    },
    'RiskStratification': {
        category: 'population_health',
        system: 'Health Catalyst, Innovaccer',
        description: 'Stratifies patient populations by risk level to enable targeted interventions and resource allocation.',
        stateFeatures: 17,
        actionType: 'Discrete',
        actionSpace: 5,
        kpis: ['High Risk Identified', 'Patients Stratified', 'Risk Management Cost'],
        useCase: 'Population health management, care coordination'
    },
    'ClaimsRouting': {
        category: 'revenue_cycle',
        system: 'Change Healthcare',
        description: 'Routes insurance claims to appropriate processors for optimal adjudication and payment.',
        stateFeatures: 18,
        actionType: 'Discrete',
        actionSpace: 5,
        kpis: ['Denial Rate', 'Collection Rate', 'Claims Routed', 'Queue Length'],
        useCase: 'Revenue cycle management, billing departments'
    },
    'TrialPatientMatching': {
        category: 'clinical_trials',
        system: 'Veeva, IQVIA',
        description: 'Matches patients to appropriate clinical trials based on eligibility criteria and trial requirements.',
        stateFeatures: 19,
        actionType: 'Discrete',
        actionSpace: 5,
        kpis: ['Enrollment', 'Enrollment Rate', 'Enrollment Progress', 'Trial Value'],
        useCase: 'Clinical research, trial management'
    },
    'StaffingAllocation': {
        category: 'hospital_operations',
        system: 'Meditech',
        description: 'Allocates staff across departments to optimize patient care and operational efficiency.',
        stateFeatures: 18,
        actionType: 'Discrete',
        actionSpace: 6,
        kpis: ['Staff Utilization', 'Occupancy Rate', 'Queue Length', 'Revenue'],
        useCase: 'Hospital operations, workforce management'
    },
    'VirtualVisitRouting': {
        category: 'telehealth',
        system: 'Teladoc, Amwell',
        description: 'Routes virtual visits to appropriate providers based on patient needs and provider availability.',
        stateFeatures: 16,
        actionType: 'Discrete',
        actionSpace: 5,
        kpis: ['Visits Routed', 'Queue Length', 'Provider Utilization', 'Visit Revenue'],
        useCase: 'Telehealth platforms, virtual care delivery'
    },
    'DataReconciliation': {
        category: 'interoperability',
        system: 'InterSystems, Orion Health',
        description: 'Reconciles data across multiple enterprise systems to ensure data integrity and consistency.',
        stateFeatures: 16,
        actionType: 'Discrete',
        actionSpace: 5,
        kpis: ['Data Quality', 'Records Reconciled', 'Reconciliation Cost'],
        useCase: 'Health information exchanges, data integration'
    },
    'PatientJourneyOptimization': {
        category: 'cross_workflow',
        system: 'Multiple',
        description: 'Multi-agent optimization across the entire patient care continuum from admission to discharge.',
        stateFeatures: 22,
        actionType: 'Discrete',
        actionSpace: 6,
        kpis: ['Journey Score', 'Risk Score', 'Journey Length', 'Journey Cost'],
        useCase: 'Care coordination, patient flow optimization',
        multiAgent: true
    },
    'JiraIssueResolution': {
        category: 'jira',
        system: 'Jira (Atlassian)',
        description: 'Jira Issue Resolution Flow: resolve issues end-to-end by fetching issue details, checking valid transitions, and applying the correct transition (e.g. to Done).',
        stateFeatures: 7,
        actionType: 'Discrete',
        actionSpace: 4,
        kpis: ['Tool Sequence Correct', 'Valid Transition Used', 'Steps to Resolution', 'Workflow Compliance'],
        useCase: 'Issue resolution workflows, ticket closure, status transitions',
        whatItDoes: '<p>Validates and rewards the correct Jira Issue Resolution workflow: <strong>get_issue_summary_and_description</strong> → <strong>get_transitions</strong> → <strong>transition_issue</strong>. Ensures transition_id is valid from get_transitions.</p>',
        howToUse: '<p>Use action 0 for the correct next step; wrong order or invalid transition incurs a penalty. Run simulation or training to learn the optimal sequence.</p>'
    },
    'JiraStatusUpdate': {
        category: 'jira',
        system: 'Jira (Atlassian)',
        description: 'Jira Status Update Workflow: change issue status across valid states by fetching transitions and applying the chosen transition.',
        stateFeatures: 6,
        actionType: 'Discrete',
        actionSpace: 3,
        kpis: ['Valid Transition Used', 'Sequence Correct', 'Steps Completed', 'Workflow Compliance'],
        useCase: 'Status updates, moving issues To Do → In Progress → Done',
        whatItDoes: '<p>Validates the Status Update workflow: <strong>get_transitions</strong> → <strong>transition_issue</strong>. Only valid transitions are allowed; transition IDs must match available options.</p>',
        howToUse: '<p>Use action 0 for the correct next step. Sequential status updates are enforced.</p>'
    },
    'JiraCommentManagement': {
        category: 'jira',
        system: 'Jira (Atlassian)',
        description: 'Jira Comment Thread Management: add and validate issue comments, then retrieve the comment thread.',
        stateFeatures: 6,
        actionType: 'Discrete',
        actionSpace: 3,
        kpis: ['Comment Added', 'Thread Retrieved', 'Sequence Correct', 'Workflow Compliance'],
        useCase: 'Adding comments to issues, retrieving comment threads',
        whatItDoes: '<p>Validates the Comment Management workflow: <strong>add_comment</strong> → <strong>get_comments</strong>. Comments must have valid content; issue must exist before commenting.</p>',
        howToUse: '<p>Use action 0 for the correct next step. Add comment first, then get_comments.</p>'
    },
    'JiraSubtaskManagement': {
        category: 'jira',
        system: 'Jira (Atlassian)',
        description: 'IT Operations: add subtasks to existing Jira tickets by fetching parent issue and creating subtask under it.',
        stateFeatures: 6,
        actionType: 'Discrete',
        actionSpace: 3,
        kpis: ['Parent Fetched', 'Subtask Created', 'Sequence Correct', 'Workflow Compliance'],
        useCase: 'Adding subtasks to Jira issues',
        whatItDoes: '<p>Validates the Subtask Management workflow: <strong>get_issue_summary_and_description</strong> → <strong>create_subtask</strong>. Fetches parent issue, then creates a subtask under it.</p>',
        howToUse: '<p>Use action 0 for the correct next step. Fetch parent first, then create_subtask.</p>'
    }
};

// ─── Category Config Registry ───────────────────────────────────────────
// Maps each environment category to default KPIs, config template, schema,
// training defaults, and description/guidance generators.
const CATEGORY_CONFIG_REGISTRY = {
    jira: {
        kpis: ['Tool Sequence Correct', 'Valid Transition Used', 'Steps to Resolution', 'Workflow Compliance'],
        configTemplate: { scenario_id: 'default' },
        configSchema: {
            scenario_id: { type: 'select', options: ['default', 'in_progress_to_blocked', 'in_progress_to_done', 'create_subtask'], label: 'Scenario', default: 'default' }
        },
        trainingDefaults: { algorithm: 'SLM', episodes: 320, maxSteps: 50 },
        descriptionTemplate: function(name, system) { return 'Jira workflow environment for ' + formatEnvironmentName(name).toLowerCase() + ' using ' + system + '.'; },
        whatItDoesTemplate: function(name) { return '<p>Validates the ' + formatEnvironmentName(name) + ' workflow using Jira API tool calls. The agent learns the correct sequence of API calls and valid parameters.</p>'; },
        howToUseTemplate: function() { return '<p>Use action 0 for the correct next step. Run simulation or training to learn the optimal workflow sequence.</p>'; }
    },
    clinical: {
        kpis: ['Risk Score', 'Pathway Length', 'Cost Effectiveness', 'Treatment Efficiency'],
        configTemplate: { patient_severity: 'moderate', num_conditions: 2, initial_risk: 50 },
        configSchema: {
            patient_severity: { type: 'select', options: ['low', 'moderate', 'high', 'critical'], label: 'Patient Severity', default: 'moderate' },
            num_conditions: { type: 'number', min: 1, max: 10, label: 'Number of Conditions', default: 2 },
            initial_risk: { type: 'range', min: 0, max: 100, label: 'Initial Risk Score', default: 50 }
        },
        trainingDefaults: { algorithm: 'PPO', episodes: 100, maxSteps: 1000 },
        descriptionTemplate: function(name, system) { return 'Clinical environment for ' + formatEnvironmentName(name).toLowerCase() + ' using ' + system + '.'; },
        whatItDoesTemplate: function(name) { return '<p>Optimizes clinical decision-making for ' + formatEnvironmentName(name).toLowerCase() + '. The agent learns to balance clinical outcomes, efficiency, and cost-effectiveness.</p>'; },
        howToUseTemplate: function() { return '<p>Configure patient parameters, select a training strategy, and run the simulation to optimize clinical workflows.</p>'; }
    },
    imaging: {
        kpis: ['Queue Length', 'Equipment Utilization', 'Urgent Orders Waiting', 'Throughput'],
        configTemplate: { queue_size: 15, ct_availability: 70, mri_availability: 60, xray_availability: 80 },
        configSchema: {
            queue_size: { type: 'number', min: 1, max: 100, label: 'Queue Size', default: 15 },
            ct_availability: { type: 'range', min: 0, max: 100, label: 'CT Availability (%)', default: 70 },
            mri_availability: { type: 'range', min: 0, max: 100, label: 'MRI Availability (%)', default: 60 },
            xray_availability: { type: 'range', min: 0, max: 100, label: 'X-Ray Availability (%)', default: 80 }
        },
        trainingDefaults: { algorithm: 'PPO', episodes: 100, maxSteps: 1000 },
        descriptionTemplate: function(name, system) { return 'Imaging environment for ' + formatEnvironmentName(name).toLowerCase() + ' using ' + system + '.'; },
        whatItDoesTemplate: function(name) { return '<p>Optimizes imaging operations for ' + formatEnvironmentName(name).toLowerCase() + ', including scheduling, prioritization, and resource allocation.</p>'; },
        howToUseTemplate: function() { return '<p>Configure imaging parameters such as queue size and equipment availability, then run simulations to optimize workflows.</p>'; }
    },
    revenue_cycle: {
        kpis: ['Denial Rate', 'Collection Rate', 'Claims Processed', 'Revenue Leakage'],
        configTemplate: { claim_volume: 100, denial_rate: 15, avg_claim_value: 500 },
        configSchema: {
            claim_volume: { type: 'number', min: 10, max: 10000, label: 'Claim Volume', default: 100 },
            denial_rate: { type: 'range', min: 0, max: 100, label: 'Initial Denial Rate (%)', default: 15 },
            avg_claim_value: { type: 'number', min: 50, max: 50000, label: 'Avg Claim Value ($)', default: 500 }
        },
        trainingDefaults: { algorithm: 'PPO', episodes: 100, maxSteps: 1000 },
        descriptionTemplate: function(name, system) { return 'Revenue cycle environment for ' + formatEnvironmentName(name).toLowerCase() + ' using ' + system + '.'; },
        whatItDoesTemplate: function(name) { return '<p>Optimizes revenue cycle operations for ' + formatEnvironmentName(name).toLowerCase() + ', including claims processing, denial management, and collections.</p>'; },
        howToUseTemplate: function() { return '<p>Configure claim parameters, then run simulations to optimize revenue cycle performance.</p>'; }
    },
    financial: {
        kpis: ['Sharpe Ratio', 'Total Return', 'Max Drawdown', 'Portfolio Value'],
        configTemplate: { initial_balance: 100000, transaction_cost: 0.001, max_position: 1.0 },
        configSchema: {
            initial_balance: { type: 'number', min: 1000, max: 10000000, label: 'Initial Balance ($)', default: 100000 },
            transaction_cost: { type: 'number', min: 0, max: 0.01, label: 'Transaction Cost (fraction)', default: 0.001 },
            max_position: { type: 'range', min: 0.1, max: 2.0, label: 'Max Position Size', default: 1.0 }
        },
        trainingDefaults: { algorithm: 'PPO', episodes: 100, maxSteps: 1500 },
        descriptionTemplate: function(name, system) { return 'Financial trading environment for ' + formatEnvironmentName(name).toLowerCase() + ' using ' + system + '.'; },
        whatItDoesTemplate: function(name) { return '<p>Optimizes financial trading strategies for ' + formatEnvironmentName(name).toLowerCase() + ', including risk-adjusted returns, portfolio optimization, and hedging.</p>'; },
        howToUseTemplate: function() { return '<p>Configure trading parameters such as initial balance and transaction costs, then run simulations to optimize trading strategies.</p>'; }
    },
    hr_payroll: {
        kpis: ['Processing Time', 'Compliance Rate', 'Error Rate', 'Employee Satisfaction'],
        configTemplate: { employee_count: 500, pay_periods: 26, compliance_threshold: 95 },
        configSchema: {
            employee_count: { type: 'number', min: 10, max: 100000, label: 'Employee Count', default: 500 },
            pay_periods: { type: 'number', min: 1, max: 52, label: 'Pay Periods/Year', default: 26 },
            compliance_threshold: { type: 'range', min: 80, max: 100, label: 'Compliance Threshold (%)', default: 95 }
        },
        trainingDefaults: { algorithm: 'PPO', episodes: 100, maxSteps: 500 },
        descriptionTemplate: function(name, system) { return 'HR & Payroll environment for ' + formatEnvironmentName(name).toLowerCase() + ' using ' + system + '.'; },
        whatItDoesTemplate: function(name) { return '<p>Optimizes HR and payroll operations for ' + formatEnvironmentName(name).toLowerCase() + '.</p>'; },
        howToUseTemplate: function() { return '<p>Configure employee and payroll parameters, then run simulations to optimize HR workflows.</p>'; }
    },
    telehealth: {
        kpis: ['Wait Time', 'Provider Utilization', 'Visit Completion Rate', 'Patient Satisfaction'],
        configTemplate: { provider_count: 10, avg_visit_duration: 15, max_queue: 20 },
        configSchema: {
            provider_count: { type: 'number', min: 1, max: 500, label: 'Provider Count', default: 10 },
            avg_visit_duration: { type: 'number', min: 5, max: 120, label: 'Avg Visit Duration (min)', default: 15 },
            max_queue: { type: 'number', min: 1, max: 200, label: 'Max Queue Size', default: 20 }
        },
        trainingDefaults: { algorithm: 'PPO', episodes: 100, maxSteps: 500 },
        descriptionTemplate: function(name, system) { return 'Telehealth environment for ' + formatEnvironmentName(name).toLowerCase() + ' using ' + system + '.'; },
        whatItDoesTemplate: function(name) { return '<p>Optimizes telehealth operations for ' + formatEnvironmentName(name).toLowerCase() + '.</p>'; },
        howToUseTemplate: function() { return '<p>Configure telehealth parameters such as provider count and visit duration, then run simulations.</p>'; }
    },
    population_health: {
        kpis: ['High Risk Identified', 'Patients Stratified', 'Intervention Coverage', 'Cost per Member'],
        configTemplate: { population_size: 1000, high_risk_pct: 20, intervention_budget: 50000 },
        configSchema: {
            population_size: { type: 'number', min: 100, max: 1000000, label: 'Population Size', default: 1000 },
            high_risk_pct: { type: 'range', min: 0, max: 100, label: 'High Risk (%)', default: 20 },
            intervention_budget: { type: 'number', min: 1000, max: 10000000, label: 'Budget ($)', default: 50000 }
        },
        trainingDefaults: { algorithm: 'PPO', episodes: 100, maxSteps: 1000 },
        descriptionTemplate: function(name, system) { return 'Population health environment for ' + formatEnvironmentName(name).toLowerCase() + ' using ' + system + '.'; },
        whatItDoesTemplate: function(name) { return '<p>Optimizes population health management for ' + formatEnvironmentName(name).toLowerCase() + '.</p>'; },
        howToUseTemplate: function() { return '<p>Configure population parameters and run simulations to optimize health strategies.</p>'; }
    },
    clinical_trials: {
        kpis: ['Enrollment Rate', 'Protocol Compliance', 'Trial Duration', 'Data Quality'],
        configTemplate: { target_enrollment: 200, num_sites: 5, trial_duration_months: 12 },
        configSchema: {
            target_enrollment: { type: 'number', min: 10, max: 10000, label: 'Target Enrollment', default: 200 },
            num_sites: { type: 'number', min: 1, max: 100, label: 'Number of Sites', default: 5 },
            trial_duration_months: { type: 'number', min: 1, max: 120, label: 'Duration (months)', default: 12 }
        },
        trainingDefaults: { algorithm: 'PPO', episodes: 100, maxSteps: 1000 },
        descriptionTemplate: function(name, system) { return 'Clinical trials environment for ' + formatEnvironmentName(name).toLowerCase() + ' using ' + system + '.'; },
        whatItDoesTemplate: function(name) { return '<p>Optimizes clinical trial operations for ' + formatEnvironmentName(name).toLowerCase() + '.</p>'; },
        howToUseTemplate: function() { return '<p>Configure trial parameters such as enrollment targets and site count, then run simulations.</p>'; }
    },
    hospital_operations: {
        kpis: ['Staff Utilization', 'Occupancy Rate', 'Queue Length', 'Revenue'],
        configTemplate: { bed_count: 100, staff_count: 50, avg_los: 3 },
        configSchema: {
            bed_count: { type: 'number', min: 10, max: 5000, label: 'Bed Count', default: 100 },
            staff_count: { type: 'number', min: 5, max: 2000, label: 'Staff Count', default: 50 },
            avg_los: { type: 'number', min: 1, max: 30, label: 'Avg Length of Stay (days)', default: 3 }
        },
        trainingDefaults: { algorithm: 'PPO', episodes: 100, maxSteps: 1000 },
        descriptionTemplate: function(name, system) { return 'Hospital operations environment for ' + formatEnvironmentName(name).toLowerCase() + ' using ' + system + '.'; },
        whatItDoesTemplate: function(name) { return '<p>Optimizes hospital operations for ' + formatEnvironmentName(name).toLowerCase() + '.</p>'; },
        howToUseTemplate: function() { return '<p>Configure hospital parameters such as bed count and staffing, then run simulations.</p>'; }
    },
    interoperability: {
        kpis: ['Data Quality', 'Records Reconciled', 'Reconciliation Cost', 'Exchange Efficiency'],
        configTemplate: { record_count: 1000, systems_count: 3, error_rate: 5 },
        configSchema: {
            record_count: { type: 'number', min: 100, max: 1000000, label: 'Record Count', default: 1000 },
            systems_count: { type: 'number', min: 2, max: 20, label: 'Systems Count', default: 3 },
            error_rate: { type: 'range', min: 0, max: 50, label: 'Error Rate (%)', default: 5 }
        },
        trainingDefaults: { algorithm: 'PPO', episodes: 100, maxSteps: 500 },
        descriptionTemplate: function(name, system) { return 'Interoperability environment for ' + formatEnvironmentName(name).toLowerCase() + ' using ' + system + '.'; },
        whatItDoesTemplate: function(name) { return '<p>Optimizes data interoperability for ' + formatEnvironmentName(name).toLowerCase() + '.</p>'; },
        howToUseTemplate: function() { return '<p>Configure data exchange parameters, then run simulations to optimize interoperability.</p>'; }
    },
    cross_workflow: {
        kpis: ['Journey Score', 'Risk Score', 'Journey Length', 'Journey Cost'],
        configTemplate: { workflow_count: 3, complexity: 'medium', optimization_target: 'balanced' },
        configSchema: {
            workflow_count: { type: 'number', min: 2, max: 20, label: 'Workflow Count', default: 3 },
            complexity: { type: 'select', options: ['low', 'medium', 'high'], label: 'Complexity', default: 'medium' },
            optimization_target: { type: 'select', options: ['speed', 'quality', 'cost', 'balanced'], label: 'Optimization Target', default: 'balanced' }
        },
        trainingDefaults: { algorithm: 'PPO', episodes: 200, maxSteps: 2000 },
        descriptionTemplate: function(name, system) { return 'Cross-workflow environment for ' + formatEnvironmentName(name).toLowerCase() + ' using ' + system + '.'; },
        whatItDoesTemplate: function(name) { return '<p>Multi-agent optimization for ' + formatEnvironmentName(name).toLowerCase() + ' across multiple workflows.</p>'; },
        howToUseTemplate: function() { return '<p>Configure cross-workflow parameters and run simulations to optimize end-to-end processes.</p>'; }
    }
};

const SDK_TRAINING_DEFAULTS = {
    gradio: { framework: 'gradio', policyType: 'MLP' },
    docker: { framework: 'custom', policyType: 'Custom' },
    static: { framework: 'N/A', policyType: 'N/A' },
    custom: { framework: 'custom', policyType: 'Custom' }
};

const SDK_TEMPLATES = {
    gradio: [
        { id: 'blank',          name: 'Blank',            logo: '',    color: '#9ca3af', blank: true },
        { id: 'audio-class',    name: 'Audio Classification', logo: 'https://cdn.simpleicons.org/gradio/F97316', color: '#f97316' },
        { id: 'chatbot',        name: 'Chatbot',          logo: 'https://cdn.simpleicons.org/gradio/F59E0B', color: '#f59e0b' },
        { id: 'diffusion',      name: 'Diffusion',        logo: 'https://cdn.simpleicons.org/gradio/8B5CF6', color: '#8b5cf6' },
        { id: 'image-class',    name: 'Image Classification', logo: 'https://cdn.simpleicons.org/gradio/06B6D4', color: '#06b6d4' },
        { id: 'leaderboard',    name: 'Leaderboard',      logo: 'https://cdn.simpleicons.org/gradio/EAB308', color: '#eab308' },
        { id: 'text-to-image',  name: 'Text to Image',    logo: 'https://cdn.simpleicons.org/gradio/A855F7', color: '#a855f7' },
        { id: 'trackio',        name: 'Trackio',          logo: 'https://cdn.simpleicons.org/gradio/EC4899', color: '#ec4899' }
    ],
    docker: [
        { id: 'blank',        name: 'Blank',            logo: '',    color: '#9ca3af', blank: true },
        { id: 'aimstack',     name: 'AimStack',         logo: 'https://cdn.simpleicons.org/aim/7C3AED',        color: '#7c3aed' },
        { id: 'argilla',      name: 'Argilla',          logo: 'https://cdn.simpleicons.org/argilla/00BCD4',    color: '#00bcd4' },
        { id: 'chatui',       name: 'ChatUI',           logo: 'https://cdn.simpleicons.org/huggingface/FFD21E', color: '#ffd21e' },
        { id: 'comfyui',      name: 'ComfyUI',          logo: 'https://cdn.simpleicons.org/comfyui/228B22',    color: '#228b22' },
        { id: 'evidence',     name: 'Evidence',          logo: 'https://cdn.simpleicons.org/evidence/43A047',  color: '#43a047' },
        { id: 'giskard',      name: 'Giskard',           logo: 'https://cdn.simpleicons.org/giskard/5C6BC0',  color: '#5c6bc0' },
        { id: 'jupyterlab',   name: 'JupyterLab',        logo: 'https://cdn.simpleicons.org/jupyter/F57C00',  color: '#f57c00' },
        { id: 'labelstudio',  name: 'Label Studio',      logo: 'https://cdn.simpleicons.org/labelstudio/FF6D00', color: '#ff6d00' },
        { id: 'langfuse',     name: 'Langfuse',           logo: 'https://cdn.simpleicons.org/langfuse/EF5350', color: '#ef5350' },
        { id: 'livebook',     name: 'Livebook',           logo: 'https://cdn.simpleicons.org/livebook/84CC16', color: '#84cc16' },
        { id: 'marimo',       name: 'marimo',             logo: 'https://cdn.simpleicons.org/marimo/00ACC1',   color: '#00acc1' },
        { id: 'mlflow',       name: 'MLflow',             logo: 'https://cdn.simpleicons.org/mlflow/0194E2',   color: '#0194e2' },
        { id: 'panel',        name: 'Panel',              logo: 'https://cdn.simpleicons.org/holoviz/66BB6A',  color: '#66bb6a' },
        { id: 'plotly',       name: 'Plotly Dash',        logo: 'https://cdn.simpleicons.org/plotly/3F4F75',   color: '#3f4f75' },
        { id: 'quarto',       name: 'Quarto',             logo: 'https://cdn.simpleicons.org/quarto/4A90D9',   color: '#4a90d9' },
        { id: 'shiny-py',     name: 'Shiny (Python)',     logo: 'https://cdn.simpleicons.org/rstudio/75AADB',  color: '#75aadb' },
        { id: 'shiny-r',      name: 'Shiny (R)',          logo: 'https://cdn.simpleicons.org/r/276DC3',        color: '#276dc3' },
        { id: 'streamlit',    name: 'Streamlit',          logo: 'https://cdn.simpleicons.org/streamlit/FF4B4B', color: '#ff4b4b' },
        { id: 'tensorboard',  name: 'TensorBoard',        logo: 'https://cdn.simpleicons.org/tensorflow/FF6F00', color: '#ff6f00' },
        { id: 'wandb',        name: 'W&B',                logo: 'https://cdn.simpleicons.org/weightsandbiases/FFBE00', color: '#ffbe00' },
        { id: 'zenml',        name: 'ZenML',              logo: 'https://cdn.simpleicons.org/zenml/7C3AED',    color: '#7c3aed' }
    ],
    static: [
        { id: 'blank',           name: 'Blank',             logo: '',    color: '#9ca3af', blank: true },
        { id: 'angular',         name: 'Angular',            logo: 'https://cdn.simpleicons.org/angular/DD0031',     color: '#dd0031' },
        { id: 'gradio-lite',     name: 'Gradio-Lite',        logo: 'https://cdn.simpleicons.org/gradio/F59E0B',     color: '#f59e0b' },
        { id: 'nextjs',          name: 'Next.js',            logo: 'https://cdn.simpleicons.org/nextdotjs/000000',   color: '#000000' },
        { id: 'paper-project',   name: 'Paper Project',      logo: 'https://cdn.simpleicons.org/files/78909C',      color: '#78909c' },
        { id: 'preact',          name: 'Preact',             logo: 'https://cdn.simpleicons.org/preact/673AB8',      color: '#673ab8' },
        { id: 'react',           name: 'React',              logo: 'https://cdn.simpleicons.org/react/61DAFB',      color: '#61dafb' },
        { id: 'solid',           name: 'SolidJS',            logo: 'https://cdn.simpleicons.org/solid/2C4F7C',      color: '#2c4f7c' },
        { id: 'svelte',          name: 'Svelte',             logo: 'https://cdn.simpleicons.org/svelte/FF3E00',     color: '#ff3e00' },
        { id: 'transformers-js', name: 'Transformers.js',    logo: 'https://cdn.simpleicons.org/huggingface/FFD21E', color: '#ffd21e' },
        { id: 'vue',             name: 'Vue',                logo: 'https://cdn.simpleicons.org/vuedotjs/4FC08D',   color: '#4fc08d' }
    ],
    custom: null
};

const DEFAULT_TERRAFORM_TEMPLATE = '# Welcome to Centific RL Environment & Agent - Terraform Template\n' +
'# This template provisions a small web application for\n' +
'# exploring reinforcement learning concepts.\n\n' +
'terraform {\n' +
'  required_providers {\n' +
'    docker = {\n' +
'      source  = "kreuzwerker/docker"\n' +
'      version = "~> 3.0"\n' +
'    }\n' +
'  }\n' +
'}\n\n' +
'provider "docker" {}\n\n' +
'resource "docker_image" "rl_app" {\n' +
'  name = "rl-intro-app:latest"\n' +
'  build {\n' +
'    context    = "${path.module}/app"\n' +
'    dockerfile = "Dockerfile"\n' +
'  }\n' +
'}\n\n' +
'resource "docker_container" "rl_app" {\n' +
'  name  = "rl-intro-app"\n' +
'  image = docker_image.rl_app.image_id\n\n' +
'  ports {\n' +
'    internal = 7860\n' +
'    external = 7860\n' +
'  }\n\n' +
'  env = [\n' +
'    "APP_TITLE=Intro to Reinforcement Learning",\n' +
'    "ENV_TYPE=custom",\n' +
'    "GRID_SIZE=5",\n' +
'    "MAX_STEPS=100"\n' +
'  ]\n\n' +
'  volumes {\n' +
'    host_path      = "${path.cwd}/data"\n' +
'    container_path = "/app/data"\n' +
'  }\n' +
'}\n\n' +
'output "app_url" {\n' +
'  value       = "http://localhost:7860"\n' +
'  description = "URL for the Intro to RL web app"\n' +
'}\n';

const HARDWARE_TRAINING_DEFAULTS = {
    'cpu-basic': { batchSize: 64, note: '2 vCPU / 16 GB' },
    'cpu-upgrade': { batchSize: 256, note: '8 vCPU / 32 GB' },
    'gpu-t4': { batchSize: 512, note: 'T4 GPU / 16 GB VRAM' },
    'gpu-a10': { batchSize: 1024, note: 'A10G GPU / 24 GB VRAM' }
};

// ─── Generate environment details for custom environments ───
function generateEnvironmentDetails(envData) {
    var category = envData.category || 'cross_workflow';
    var name = envData.name;
    var system = envData.system || 'Custom';
    var sdk = envData.sdk || 'gradio';
    var hardware = envData.hardware || 'cpu-basic';
    var source = envData.source || 'custom';

    // For HuggingFace imports, skip RL defaults — details are populated separately via analyze
    if (source === 'huggingface') {
        return {
            category: 'custom', system: system, description: envData.description || '',
            sdk: sdk, hardware: hardware, source: 'huggingface', isCustom: true,
            hf_url: envData.hf_url || ''
        };
    }

    // For custom/terraform SDK environments, skip RL defaults
    if (sdk === 'custom' || category === 'custom') {
        return {
            category: 'custom', system: system,
            description: envData.description || 'Custom environment: ' + formatEnvironmentName(name),
            sdk: sdk, hardware: hardware, source: source, isCustom: true,
            terraformTemplate: envData.terraformTemplate || null,
            template: envData.template || 'blank'
        };
    }

    // Standard RL environments — use category registry
    var registry = CATEGORY_CONFIG_REGISTRY[category] || CATEGORY_CONFIG_REGISTRY['cross_workflow'];
    return {
        category: category,
        system: system,
        description: envData.description || registry.descriptionTemplate(name, system),
        stateFeatures: envData.stateFeatures || 10,
        actionType: envData.actionType || 'Discrete',
        actionSpace: envData.actionSpace || 4,
        kpis: registry.kpis.slice(),
        useCase: 'Custom environment for ' + formatEnvironmentName(name).toLowerCase() + '.',
        whatItDoes: registry.whatItDoesTemplate(name),
        howToUse: registry.howToUseTemplate(),
        configTemplate: JSON.parse(JSON.stringify(registry.configTemplate)),
        configSchema: registry.configSchema,
        trainingDefaults: Object.assign({}, registry.trainingDefaults),
        sdk: sdk,
        hardware: hardware,
        sdkDefaults: SDK_TRAINING_DEFAULTS[sdk] || SDK_TRAINING_DEFAULTS['gradio'],
        hardwareDefaults: HARDWARE_TRAINING_DEFAULTS[hardware] || HARDWARE_TRAINING_DEFAULTS['cpu-basic'],
        source: source,
        isCustom: true
    };
}

// User journey: industry -> persona -> catalog
var JOURNEY_PERSONAS = {
    finance: [
        { id: 'revenue_cycle', label: 'Revenue cycle', desc: 'Claims, billing, payments' },
        { id: 'all', label: 'All finance', desc: 'All finance RL environments' }
    ],
    healthcare: [
        { id: 'clinical', label: 'Clinical', desc: 'Care pathways, interventions' },
        { id: 'imaging', label: 'Imaging', desc: 'Radiology, scheduling' },
        { id: 'population_health', label: 'Population health', desc: 'Risk, outreach' },
        { id: 'revenue_cycle', label: 'Revenue', desc: 'Billing, claims' },
        { id: 'clinical_trials', label: 'Clinical trials', desc: 'Trials, enrollment' },
        { id: 'hospital_operations', label: 'Operations', desc: 'Staffing, beds' },
        { id: 'all', label: 'All healthcare', desc: 'All healthcare RL environments' }
    ],
    enterprise: [
        { id: 'jira', label: 'Jira workflows', desc: 'Issue resolution, status, comments' }
    ],
    human_resources: [
        { id: 'hr_payroll', label: 'HR & Payroll', desc: 'Workday, SAP SuccessFactors, ADP' },
        { id: 'all', label: 'All HR & Payroll', desc: 'All HR and payroll RL environments' }
    ]
};

function applyJourneyFromUrl() {
    var params = new URLSearchParams(window.location.search);
    var industry = (params.get('industry') || '').toLowerCase();
    var persona = (params.get('persona') || '').toLowerCase();
    var step1 = document.getElementById('journey-step-1');
    var step2 = document.getElementById('journey-step-2');
    var browse = document.getElementById('catalog-browse');
    if (!step1 || !step2 || !browse) return;

    if (!industry) {
        step1.style.display = 'none';
        step2.style.display = 'none';
        browse.style.display = 'block';
        loadEnvironments();
        return;
    }
    if (industry && industry !== 'all' && !persona && JOURNEY_PERSONAS[industry]) {
        step1.style.display = 'none';
        step2.style.display = 'block';
        browse.style.display = 'none';
        var subtitle = document.getElementById('journey-step-2-subtitle');
        if (subtitle) subtitle.textContent = 'Select a workflow area for ' + (industry === 'enterprise' ? 'enterprise apps' : industry === 'human_resources' ? 'human resources' : industry) + '.';
        var container = document.getElementById('journey-persona-cards');
        if (container) {
            var links = JOURNEY_PERSONAS[industry].map(function(p) {
                var url = '/catalog?industry=' + encodeURIComponent(industry) + '&persona=' + encodeURIComponent(p.id);
                return '<a href="' + url + '" class="journey-card"><span class="journey-card-icon">' + (p.id === 'all' ? '📂' : '👤') + '</span><h2>' + p.label + '</h2><p>' + (p.desc || '') + '</p></a>';
            });
            container.innerHTML = links.join('');
        }
        return;
    }
    step1.style.display = 'none';
    step2.style.display = 'none';
    browse.style.display = 'block';
    loadEnvironments();
}

function applyIndustryPersonaFilter() {
    var params = new URLSearchParams(window.location.search);
    var industry = (params.get('industry') || '').toLowerCase();
    var persona = (params.get('persona') || '').toLowerCase();
    if (!allEnvironments.length) return;
    if (industry === 'all' || !industry) return;
    var domainFilter = document.getElementById('domain-filter');
    var category = 'all';
    if (industry === 'enterprise') {
        if (domainFilter) domainFilter.value = 'dev-sim';
        category = persona && persona === 'jira' ? 'jira' : 'all';
    } else if (industry === 'human_resources') {
        if (domainFilter) domainFilter.value = 'hr-sim';
        category = persona && persona !== 'all' ? 'hr_payroll' : 'all';
    } else if (industry === 'finance') {
        if (domainFilter) domainFilter.value = 'fin-sim';
        category = persona && persona !== 'all' ? persona : 'revenue_cycle';
    } else if (industry === 'healthcare') {
        if (domainFilter) domainFilter.value = 'med-sim';
        category = persona && persona !== 'all' ? persona : 'all';
    }
    updateFilterButtonsForDomain();
    updateSystemFilterOptions();
    document.querySelectorAll('.filter-btn').forEach(function(btn) { btn.classList.remove('active'); });
    var activeBtn = document.querySelector('.filter-btn[data-category="' + category + '"]');
    if (activeBtn) activeBtn.classList.add('active'); else if (document.querySelector('.filter-btn[data-category="all"]')) document.querySelector('.filter-btn[data-category="all"]').classList.add('active');
    filterEnvironments(document.getElementById('search-input').value, category);
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    applyJourneyFromUrl();
    setupEventListeners();
});

async function loadEnvironments() {
    try {
        const response = await fetch(`${API_BASE}/environments`);
        if (!response.ok) throw new Error('Failed to load environments');
        
        const data = await response.json();
        allEnvironments = data.environments || [];

        // Load persisted custom environments from backend and merge
        try {
            const customRes = await fetch(`${API_BASE}/api/custom-environments`);
            if (customRes.ok) {
                const customData = await customRes.json();
                const existingNames = new Set(allEnvironments.map(e => e.name));
                (customData.environments || []).forEach(function(ce) {
                    if (!existingNames.has(ce.name)) {
                        var envEntry = {
                            name: ce.name,
                            description: ce.description || 'Custom environment',
                            category: ce.category || 'custom',
                            system: ce.system || 'Custom',
                            workflow: ce.workflow || '',
                            domain: ce.domain || '',
                            tags: ce.tags || [],
                            sdk: ce.sdk || 'gradio',
                            hardware: ce.hardware || 'cpu-basic',
                            source: ce.source || 'custom',
                            isCustom: true
                        };
                        if (ce.hf_url) {
                            envEntry.hf_url = ce.hf_url;
                            envEntry.source = 'huggingface';
                            envEntry.hf_owner = ce.hf_owner || '';
                            envEntry.hf_repo = ce.hf_repo || '';
                        }
                        if (ce.terraformTemplate) { envEntry.terraformTemplate = ce.terraformTemplate; }
                        if (ce.owner) { envEntry.owner = ce.owner; }
                        allEnvironments.push(envEntry);

                        // For HF envs, fetch analysis to get rich details; otherwise generate RL defaults
                        if (envEntry.source === 'huggingface') {
                            environmentDetails[ce.name] = {
                                source: 'huggingface',
                                isCustom: true,
                                hf_url: ce.hf_url,
                                hf_owner: ce.hf_owner || '',
                                hf_repo: ce.hf_repo || '',
                                sdk: envEntry.sdk,
                                description: envEntry.description,
                                author: ce.hf_owner || '',
                                tags: [],
                                files: [],
                                endpoints: [],
                                models: {},
                                readme: ''
                            };
                            // Asynchronously enrich with analysis data
                            (function(eName) {
                                fetch(API_BASE + '/api/environment/' + encodeURIComponent(eName) + '/analyze')
                                    .then(function(r) { return r.ok ? r.json() : null; })
                                    .then(function(analysis) {
                                        if (analysis && environmentDetails[eName]) {
                                            environmentDetails[eName].readme = analysis.readme_raw || '';
                                            environmentDetails[eName].files = analysis.files || [];
                                            environmentDetails[eName].endpoints = analysis.endpoints || [];
                                            environmentDetails[eName].models = analysis.models || {};
                                            environmentDetails[eName].frontMatter = analysis.front_matter || {};
                                        }
                                    }).catch(function() {});
                            })(ce.name);
                        } else {
                            var generated = generateEnvironmentDetails(envEntry);
                            environmentDetails[ce.name] = generated;
                        }
                        existingNames.add(ce.name);
                    }
                });
                console.log('[Persistence] Loaded ' + (customData.environments || []).length + ' custom environments from backend');
            }
        } catch (e) { console.warn('[Persistence] Could not load custom environments:', e); }

        // Fallback: ensure JiraSubtaskManagement is in catalog (in case API hasn't been redeployed)
        if (!allEnvironments.some(e => e.name === 'JiraSubtaskManagement')) {
            const jiraSubtask = {
                name: 'JiraSubtaskManagement',
                class_path: 'environments.jira.jira_workflow_env.JiraSubtaskManagementEnv',
                system: 'Jira (Atlassian)',
                workflow: 'Jira',
                category: 'jira',
                multi_agent: false,
                actionSpace: 3,
                stateFeatures: 6,
                actionType: 'Discrete',
                actions: ['action_0', 'action_1', 'action_2']
            };
            allEnvironments.push(jiraSubtask);
            console.log('Added JiraSubtaskManagement to catalog (API fallback)');
        }

        // Fallback: ensure ClinKriya Clinic is in catalog (custom HF environment)
        if (!allEnvironments.some(e => e.name === 'ClinKriya Clinic')) {
            allEnvironments.push({
                name: 'ClinKriya Clinic',
                description: 'Clinical RL environment for healthcare workflows powered by MedAgentBench',
                category: 'cross_workflow',
                system: 'MedAgentBench',
                sdk: 'docker',
                source: 'huggingface',
                hf_url: 'https://huggingface.co/spaces/openenv-community/clinKriya',
                hf_owner: 'openenv-community',
                hf_repo: 'clinKriya',
                domain: 'cross-domain',
                workflow: 'Cross-Workflow',
                isCustom: true,
                tags: ['cross-domain', 'cross_workflow', 'cross-workflow', 'medagentbench'],
                actions: [],
                actionSpace: 'N/A',
                stateFeatures: 'N/A',
                actionType: 'Discrete'
            });
            environmentDetails['ClinKriya Clinic'] = {
                source: 'huggingface',
                isCustom: true,
                hf_url: 'https://huggingface.co/spaces/openenv-community/clinKriya',
                hf_owner: 'openenv-community',
                hf_repo: 'clinKriya',
                sdk: 'docker',
                description: 'Clinical RL environment for healthcare workflows powered by MedAgentBench',
                author: 'openenv-community',
                tags: [],
                files: [],
                endpoints: [],
                models: {},
                readme: ''
            };
            console.log('Added ClinKriya Clinic to catalog (fallback)');
        }
        
        // Enhance with details - generate unique descriptions for each environment
        allEnvironments = allEnvironments.map(env => {
            // Always generate description - ignore any from API
            const generatedDescription = environmentDetails[env.name]?.description || getEnvironmentDescription(env.name, env.category || 'other');
            
            // Debug: Log if description is still generic (for troubleshooting)
            if (generatedDescription && generatedDescription.includes('RL environment for optimization')) {
                console.warn(`⚠️ Generic description detected for ${env.name}, using generated description`);
            }
            
            return {
                ...env,
                ...(environmentDetails[env.name] || {}),
                // Force use of generated description (never use API description)
                description: generatedDescription,
                // Ensure category and workflow are set
                category: env.category || environmentDetails[env.name]?.category || 'other',
                workflow: env.workflow || environmentDetails[env.name]?.workflow || (env.category ? env.category.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'General')
            };
        });
        
        // Debug: Verify descriptions are set
        console.log(`✅ Loaded ${allEnvironments.length} environments with descriptions`);
        const sampleEnv = allEnvironments[0];
        if (sampleEnv) {
            console.log(`📝 Sample: ${sampleEnv.name} - Description: ${sampleEnv.description?.substring(0, 60)}...`);
        }
        
        // Calculate and update stats dynamically
        const totalEnvs = allEnvironments.length;
        const categories = new Set(allEnvironments.map(e => e.category || 'unknown'));
        const systems = new Set();
        allEnvironments.forEach(env => {
            const system = env.system || 'Unknown';
            // Split by comma to get individual systems
            system.split(',').forEach(s => {
                const trimmed = s.trim();
                if (trimmed) systems.add(trimmed);
            });
        });
        
        // Update stats in UI
        document.getElementById('total-envs').textContent = totalEnvs;
        document.getElementById('total-categories').textContent = categories.size;
        document.getElementById('total-systems').textContent = systems.size;
        const subtitleEl = document.getElementById('subtitle-env-count');
        if (subtitleEl) subtitleEl.textContent = `${totalEnvs} Reinforcement Learning Environments for Workflow Optimization`;
        
        // Populate Domain filter and Software System filter dropdown
        const domainFilter = document.getElementById('domain-filter');
        if (domainFilter) {
            domainFilter.addEventListener('change', () => {
                updateFilterButtonsForDomain();
                updateSystemFilterOptions();
                filterEnvironments(document.getElementById('search-input').value, getActiveCategory());
            });
        }
        updateFilterButtonsForDomain();
        updateSystemFilterOptions();
        const systemFilter = document.getElementById('system-filter');
        if (systemFilter) {
            systemFilter.addEventListener('change', () => {
                filterEnvironments(document.getElementById('search-input').value, getActiveCategory());
            });
        }
        
        // Initialize save data for all environments
        allEnvironments.forEach(env => {
            initializeSaveData(env.name);
        });
        
        // Reset fake counts only once (first time after update)
        resetAllSaveCounts();
        
        filteredEnvironments = allEnvironments;
        renderEnvironments();
        document.getElementById('loading').style.display = 'none';
        applyIndustryPersonaFilter();
        var urlParams = new URLSearchParams(window.location.search);
        // Pre-fill search from URL param (e.g., from landing page hero search)
        var searchParam = urlParams.get('search');
        if (searchParam) {
            var searchInput = document.getElementById('search-input');
            if (searchInput) {
                searchInput.value = searchParam;
                filterEnvironments(searchParam, getActiveCategory());
            }
        }
        var envParam = urlParams.get('env');
        if (envParam && allEnvironments.some(function(e) { return e.name === envParam; })) {
            showEnvironmentDetails(envParam);
            if (window.location.hash === '#training') {
                setTimeout(function() { openTrainingConfig(envParam); }, 100);
            }
        }
    } catch (error) {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('error').style.display = 'block';
        document.getElementById('error').textContent = `Error: ${error.message}. Make sure the API server is running on port 8000.`;
    }
}

function setupEventListeners() {
    // Back to catalog (full-page detail view)
    const btnBack = document.getElementById('btn-back-catalog');
    if (btnBack) btnBack.addEventListener('click', closeEnvDetailPage);
    
    // Search
    document.getElementById('search-input').addEventListener('input', (e) => {
        filterEnvironments(e.target.value, getActiveCategory());
    });
    
    // Category filters
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            // Financial tag → navigate directly to Delcita Investments & Trading
            if (btn.dataset.category === 'financial') {
                window.location.href = '/financial-console?env=delcita';
                return;
            }
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filterEnvironments(document.getElementById('search-input').value, btn.dataset.category);
        });
    });
    
    // Modal close
    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            if (modal) {
                modal.style.display = 'none';
            }
        });
    });
    
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.style.display = 'none';
        }
    });
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

function openHelpSection() {
    const helpBody = document.getElementById('help-body');
    
    // Collect all systems and workflows from environments
    const systemsMap = {};
    const workflowsByCategory = {};
    
    allEnvironments.forEach(env => {
        const systems = (env.system || 'Multiple').split(',').map(s => s.trim());
        systems.forEach(system => {
            if (!systemsMap[system]) {
                systemsMap[system] = [];
            }
            if (!systemsMap[system].includes(env.name)) {
                systemsMap[system].push(env.name);
            }
        });
        
        const category = env.category || 'other';
        if (!workflowsByCategory[category]) {
            workflowsByCategory[category] = [];
        }
        workflowsByCategory[category].push({
            name: env.name,
            displayName: formatEnvironmentName(env.name),
            description: env.description || 'RL Environment',
            system: env.system || 'Multiple'
        });
    });
    
    helpBody.innerHTML = `
        <h1 style="margin-bottom: 2rem;">📚 Help & Documentation</h1>
        
        <div class="help-section" style="margin-bottom: 3rem;">
            <h2 style="color: var(--primary-color); margin-bottom: 1.5rem; border-bottom: 2px solid var(--border-color); padding-bottom: 0.5rem;">🏢 Integrated Software Systems</h2>
            <p style="margin-bottom: 1.5rem; color: var(--text-secondary);">
                This platform integrates with multiple operational software systems, providing digital twin simulations 
                and RL environments for workflow optimization:
            </p>
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem;">
                ${Object.entries(systemsMap).map(([system, envs]) => `
                    <div style="background: #f8fafc; padding: 1.5rem; border-radius: 8px; border: 1px solid var(--border-color);">
                        <h3 style="color: var(--primary-color); margin-bottom: 0.75rem; font-size: 1.1rem;">${system}</h3>
                        <p style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 1rem;">
                            <strong>${envs.length}</strong> RL environment${envs.length !== 1 ? 's' : ''} available
                        </p>
                        <ul style="font-size: 0.85rem; color: var(--text-primary); list-style: none; padding: 0;">
                            ${envs.slice(0, 5).map(env => `
                                <li style="padding: 0.25rem 0;">• ${formatEnvironmentName(env)}</li>
                            `).join('')}
                            ${envs.length > 5 ? `<li style="padding: 0.25rem 0; color: var(--text-secondary);">+ ${envs.length - 5} more...</li>` : ''}
                        </ul>
                    </div>
                `).join('')}
            </div>
        </div>
        
        <div class="help-section" style="margin-bottom: 3rem;">
            <h2 style="color: var(--primary-color); margin-bottom: 1.5rem; border-bottom: 2px solid var(--border-color); padding-bottom: 0.5rem;">🔄 Workflows by Category</h2>
            <p style="margin-bottom: 1.5rem; color: var(--text-secondary);">
                All ${allEnvironments.length} RL environments organized by workflow category:
            </p>
            ${Object.entries(workflowsByCategory).map(([category, workflows]) => `
                <div style="margin-bottom: 2rem; background: #f8fafc; padding: 1.5rem; border-radius: 8px; border: 1px solid var(--border-color);">
                    <h3 style="color: var(--primary-color); margin-bottom: 1rem; text-transform: capitalize; font-size: 1.2rem;">
                        ${category.replace('_', ' ')} (${workflows.length} environments)
                    </h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem;">
                        ${workflows.map(workflow => `
                            <div style="background: white; padding: 1rem; border-radius: 6px; border: 1px solid var(--border-color);">
                                <h4 style="font-size: 0.95rem; margin-bottom: 0.5rem; color: var(--text-primary);">
                                    ${workflow.displayName}
                                </h4>
                                <p style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.5rem;">
                                    ${workflow.description}
                                </p>
                                <p style="font-size: 0.75rem; color: var(--text-secondary);">
                                    <strong>Software system:</strong> ${workflow.system}
                                </p>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `).join('')}
        </div>
        
        <div class="help-section" style="margin-bottom: 2rem;">
            <h2 style="color: var(--primary-color); margin-bottom: 1.5rem; border-bottom: 2px solid var(--border-color); padding-bottom: 0.5rem;">📖 Quick Start Guide</h2>
            <div style="background: #f0f9ff; padding: 1.5rem; border-radius: 8px; border-left: 4px solid var(--primary-color);">
                <ol style="line-height: 2; padding-left: 1.5rem;">
                    <li><strong>Browse Environments:</strong> Use the search and filter options to find RL environments relevant to your software systems and workflows.</li>
                    <li><strong>View Details:</strong> Click "View Details" on any environment card to learn about its capabilities and use cases.</li>
                    <li><strong>Test with Environment:</strong> Click "🧪 Environment" to open the interactive console and test the environment with your parameters.</li>
                    <li><strong>Train an Agent:</strong> Click "🎓 Start Training" to configure and train an RL agent for production use.</li>
                    <li><strong>Monitor Progress:</strong> Track training progress using the job ID provided after starting training.</li>
                </ol>
            </div>
        </div>
        
        <div class="help-section">
            <h2 style="color: var(--primary-color); margin-bottom: 1.5rem; border-bottom: 2px solid var(--border-color); padding-bottom: 0.5rem;">💡 Training Configuration</h2>
            <div style="background: #fef3c7; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #f59e0b;">
                <p style="margin-bottom: 1rem;"><strong>Three ways to configure training:</strong></p>
                <ul style="line-height: 2; padding-left: 1.5rem;">
                    <li><strong>Manual Entry:</strong> Fill in algorithm, episodes, and configuration parameters directly in the UI.</li>
                    <li><strong>JSON Upload:</strong> Upload a JSON file or paste JSON configuration for batch training setups.</li>
                    <li><strong>API Integration:</strong> Use the REST API endpoints with examples provided in the API tab.</li>
                </ul>
                <p style="margin-top: 1rem; font-size: 0.9rem; color: var(--text-secondary);">
                    See the "🔌 API Example" tab in the training configuration modal for complete code examples in Python, cURL, and more.
                </p>
            </div>
        </div>
    `;
    
    document.getElementById('help-modal').style.display = 'block';
}

function getActiveCategory() {
    const activeBtn = document.querySelector('.filter-btn.active');
    return activeBtn ? activeBtn.dataset.category : 'all';
}

function getActiveSystem() {
    const sel = document.getElementById('system-filter');
    return sel ? sel.value : 'all';
}

function getActiveDomain() {
    const sel = document.getElementById('domain-filter');
    return sel ? sel.value : 'all';
}

function updateFilterButtonsForDomain() {
    const domain = getActiveDomain();
    const container = document.getElementById('filter-buttons');
    if (!container) return;
    container.querySelectorAll('.filter-btn').forEach(btn => {
        const btnDomain = btn.dataset.domain || 'all';
        if (domain === 'all') {
            btn.style.display = '';
        } else {
            btn.style.display = (btnDomain === domain || btn.dataset.category === 'all') ? '' : 'none';
        }
    });
    // If active button is now hidden, reset to "All"
    const activeBtn = container.querySelector('.filter-btn.active');
    if (activeBtn && activeBtn.style.display === 'none') {
        container.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        const allBtn = container.querySelector('.filter-btn[data-category="all"]');
        if (allBtn && allBtn.style.display !== 'none') allBtn.classList.add('active');
    }
}

function updateSystemFilterOptions() {
    const domain = getActiveDomain();
    const systemFilter = document.getElementById('system-filter');
    const systemFilterWrap = document.getElementById('system-filter-wrap');
    if (!systemFilter) return;

    // Hide system filter when no domain is selected (or "All" is selected)
    if (domain === 'all') {
        if (systemFilterWrap) systemFilterWrap.style.display = 'none';
        systemFilter.value = 'all';
        return;
    }

    // Show system filter when a domain is selected
    if (systemFilterWrap) systemFilterWrap.style.display = 'flex';

    const medCategories = ['clinical', 'imaging', 'population_health', 'hospital_operations',
                           'telehealth', 'interoperability', 'clinical_trials', 'cross_workflow'];
    let envsForSystems = allEnvironments;
    if (domain === 'dev-sim') {
        envsForSystems = allEnvironments.filter(env => env.category === 'jira' || (env.system || '').toLowerCase().includes('jira'));
    } else if (domain === 'med-sim') {
        envsForSystems = allEnvironments.filter(env => medCategories.includes(env.category));
    } else if (domain === 'fin-sim') {
        envsForSystems = allEnvironments.filter(env => env.category === 'revenue_cycle' || env.category === 'financial');
    } else if (domain === 'hr-sim') {
        envsForSystems = allEnvironments.filter(env => env.category === 'hr_payroll');
    }

    const systems = new Set();
    envsForSystems.forEach(env => {
        (env.system || '').split(',').forEach(s => {
            const t = s.trim();
            if (t) systems.add(t);
        });
    });
    const systemList = Array.from(systems).sort((a, b) => a.localeCompare(b));
    const currentVal = systemFilter.value;
    systemFilter.innerHTML = '<option value="all">All systems</option>' +
        systemList.map(s => `<option value="${s.replace(/"/g, '&quot;')}">${s}</option>`).join('');
    if (currentVal && systemList.includes(currentVal)) {
        systemFilter.value = currentVal;
    } else if (systemList.length === 1) {
        systemFilter.value = systemList[0];
    }
}

function filterEnvironments(searchTerm, category) {
    const system = getActiveSystem();
    const domain = getActiveDomain();
    filteredEnvironments = allEnvironments.filter(env => {
        const useCaseText = getUseCaseDescription(env.name, env.category || 'other');
        const descText = env.description || getEnvironmentDescription(env.name, env.category || 'other') || '';
        const matchesSearch = !searchTerm ||
            env.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (descText && descText.toLowerCase().includes(searchTerm.toLowerCase())) ||
            (useCaseText && useCaseText.toLowerCase().includes(searchTerm.toLowerCase()));
        
        const matchesCategory = category === 'all' ||
            (category === 'custom' ? (env.isCustom === true || env.source === 'custom') : env.category === category);
        
        const envSystems = (env.system || '').split(',').map(s => s.trim()).filter(Boolean);
        const matchesSystem = system === 'all' || envSystems.includes(system);
        
        let matchesDomain = true;
        // When a specific system is selected, system filter takes precedence over domain
        if (system === 'all') {
            const medCategories = ['clinical', 'imaging', 'population_health', 'hospital_operations',
                                   'telehealth', 'interoperability', 'clinical_trials', 'cross_workflow'];
            if (domain === 'dev-sim') matchesDomain = env.category === 'jira' || (env.system || '').toLowerCase().includes('jira');
            else if (domain === 'med-sim') matchesDomain = medCategories.includes(env.category);
            else if (domain === 'fin-sim') matchesDomain = env.category === 'revenue_cycle' || env.category === 'financial';
            else if (domain === 'hr-sim') matchesDomain = env.category === 'hr_payroll';
        }
        
        return matchesSearch && matchesCategory && matchesSystem && matchesDomain;
    });
    
    renderEnvironments();
}

// Names of environments that should always appear first in the grid
var PINNED_ENV_NAMES = ['ClinKriya Clinic', 'Delcita'];

function renderEnvironments() {
    const grid = document.getElementById('environments-grid');

    if (filteredEnvironments.length === 0) {
        grid.innerHTML = '<div class="error">No environments found matching your criteria.</div>';
        return;
    }

    // Sort: pinned environments first (in order), then the rest
    var pinned = [];
    var rest = [];
    filteredEnvironments.forEach(function(env) {
        var pinIdx = PINNED_ENV_NAMES.indexOf(env.name);
        if (pinIdx !== -1) {
            pinned.push({ env: env, order: pinIdx });
        } else {
            rest.push(env);
        }
    });
    pinned.sort(function(a, b) { return a.order - b.order; });
    var sorted = pinned.map(function(p) { return p.env; }).concat(rest);

    grid.innerHTML = sorted.map(env => createEnvCard(env)).join('');
    
    // Add click listener on entire card for view details
    document.querySelectorAll('.env-card').forEach(card => {
        card.addEventListener('click', (e) => {
            const envName = card.dataset.env;
            if (!envName) return;
            // Financial environments go directly to the simulation console
            const envObj = allEnvironments.find(env => env.name === envName);
            const envDetails = environmentDetails[envName];
            if ((envObj && envObj.category === 'financial')) {
                window.location.href = '/financial-console?env=' + encodeURIComponent(envName);
                return;
            }
            showEnvironmentDetails(envName);
        });
    });

}

var ENV_DISPLAY_NAME_OVERRIDES = {
    'JiraSubtaskManagement': 'IT Operations',
    'clinKriya': 'ClinKriya Clinic',
    'ClinKriya Clinic': 'ClinKriya Clinic',
    'Delcita': 'Delcita Investments & Trading'
};

function formatEnvironmentName(name) {
    if (ENV_DISPLAY_NAME_OVERRIDES[name]) return ENV_DISPLAY_NAME_OVERRIDES[name];
    // Add spaces before capital letters
    return name.replace(/([A-Z])/g, ' $1').trim();
}

// Generate unique, use-case-specific descriptions for each environment
function getEnvironmentDescription(envName, category) {
    const descriptions = {
        // Clinical environments
        'TreatmentPathwayOptimization': 'Optimizes treatment sequences for patients with multiple conditions, balancing clinical outcomes, efficiency, and cost-effectiveness.',
        'SepsisEarlyIntervention': 'Early detection and intervention for sepsis cases using SOFA scores and vital signs monitoring to reduce mortality rates.',
        'ICUResourceAllocation': 'Optimally allocates ICU beds and staff resources based on patient acuity and resource availability to maximize care quality.',
        'SurgicalScheduling': 'Intelligently schedules surgical procedures to optimize OR utilization while minimizing patient wait times and cancellations.',
        'DiagnosticTestSequencing': 'Determines optimal order of diagnostic tests to accelerate diagnosis while minimizing costs and delays.',
        'MedicationDosingOptimization': 'Personalizes medication dosages based on patient characteristics, drug interactions, and therapeutic response.',
        'ReadmissionReduction': 'Identifies high-risk patients and applies targeted interventions to prevent avoidable hospital readmissions.',
        'CareCoordination': 'Coordinates care across multiple providers and departments to ensure seamless patient transitions and continuity.',
        'ChronicDiseaseManagement': 'Manages chronic conditions through proactive monitoring, medication adherence, and lifestyle interventions.',
        'EmergencyTriage': 'Prioritizes emergency department patients based on acuity, resource availability, and clinical urgency.',
        'PainManagementOptimization': 'Optimizes pain management strategies to balance patient comfort with medication safety and opioid reduction goals.',
        'AntibioticStewardship': 'Promotes appropriate antibiotic use to combat resistance while ensuring effective treatment of infections.',
        'OncologyTreatmentSequencing': 'Optimizes cancer treatment sequences including chemotherapy, radiation, and surgery timing for best outcomes.',
        'LabTestPrioritization': 'Prioritizes laboratory tests based on clinical urgency, resource constraints, and diagnostic value.',
        'ICUVentilatorAllocation': 'Allocates mechanical ventilators to critically ill patients based on severity, prognosis, and resource availability.',
        'StrokeInterventionScheduling': 'Schedules stroke interventions including thrombolytics and thrombectomy to minimize time-to-treatment.',
        'CardiacCareOptimization': 'Optimizes cardiac care pathways including cardiac catheterization, bypass surgery, and post-procedure monitoring.',
        'DiabetesMonitoringOptimization': 'Optimizes diabetes monitoring frequency and intervention timing to prevent complications and improve glycemic control.',
        'MentalHealthInterventionSequencing': 'Sequences mental health interventions including therapy, medication, and crisis interventions for optimal outcomes.',
        'PostOperativeFollowupOptimization': 'Optimizes post-operative follow-up schedules to detect complications early while minimizing unnecessary visits.',
        
        // Imaging environments
        'ImagingOrderPrioritization': 'Prioritizes imaging orders based on clinical urgency, equipment availability, and patient needs to reduce wait times.',
        'RadiologyScheduling': 'Schedules radiology appointments to maximize scanner utilization while meeting patient and referring physician needs.',
        'ScanParameterOptimization': 'Optimizes imaging scan parameters to balance image quality, radiation dose, and scan duration.',
        'ImagingWorkflowRouting': 'Routes imaging studies through optimal workflow paths to minimize processing time and maximize throughput.',
        'EquipmentUtilization': 'Maximizes utilization of imaging equipment including CT, MRI, and ultrasound scanners across multiple facilities.',
        'MRIScanScheduling': 'Schedules MRI scans considering patient preparation needs, contrast requirements, and scanner availability.',
        'CTScanPrioritization': 'Prioritizes CT scans based on clinical urgency, contrast requirements, and scanner capacity.',
        'RadiologistTaskAssignment': 'Assigns radiology reading tasks to radiologists based on expertise, workload, and turnaround time requirements.',
        'UltrasoundResourceAllocation': 'Allocates ultrasound resources across departments to balance urgent and routine study needs.',
        'PACSWorkflowOptimization': 'Optimizes Picture Archiving and Communication System workflows to accelerate image retrieval and reporting.',
        'ImagingResultTriage': 'Prioritizes imaging result review and reporting based on clinical urgency and critical finding potential.',
        'AIAssistedDiagnostics': 'Integrates AI-assisted diagnostic tools to prioritize studies requiring immediate attention and flag abnormalities.',
        'ImagingStudyBatchScheduling': 'Batches similar imaging studies to improve efficiency and reduce setup time between scans.',
        'OncologyImagingPathway': 'Optimizes imaging pathways for cancer patients including screening, staging, and treatment response monitoring.',
        'ImagingQualityControl': 'Monitors and optimizes imaging quality metrics to ensure diagnostic accuracy while maintaining efficiency.',
        
        // Population Health environments
        'RiskStratification': 'Stratifies patient populations by risk level to enable targeted interventions and resource allocation.',
        'PreventiveOutreach': 'Identifies patients due for preventive care and optimizes outreach strategies to improve screening rates.',
        'VaccinationAllocation': 'Allocates vaccines across populations to maximize coverage while prioritizing high-risk groups.',
        'HighRiskMonitoring': 'Monitors high-risk patients proactively to prevent adverse events and reduce emergency department visits.',
        'PopulationCostOptimization': 'Optimizes population health spending to maximize outcomes while controlling per-member costs.',
        'ChronicDiseaseOutreach': 'Targets chronic disease patients for proactive interventions to prevent complications and hospitalizations.',
        'TelemonitoringOptimization': 'Optimizes remote patient monitoring programs to balance resource use with patient outcomes.',
        'PreventiveScreeningPolicy': 'Determines optimal screening schedules and eligibility criteria to maximize early detection rates.',
        'HighRiskPatientEngagement': 'Engages high-risk patients through personalized interventions to improve adherence and outcomes.',
        'PopulationHealthCostAllocation': 'Allocates population health resources across programs to maximize population-level outcomes.',
        'CommunityHealthProgramAllocation': 'Allocates community health programs to areas with greatest need and potential impact.',
        'ReadmissionRiskMitigation': 'Identifies and intervenes with patients at high risk for readmission to prevent avoidable returns.',
        'HealthLiteracyIntervention': 'Delivers health literacy interventions to improve patient understanding and self-management capabilities.',
        'LifestyleInterventionSequencing': 'Sequences lifestyle interventions including nutrition, exercise, and smoking cessation programs.',
        'VaccinationDrivePrioritization': 'Prioritizes vaccination drives across communities to maximize coverage and minimize disease spread.',
        
        // Revenue Cycle environments
        'ClaimsRouting': 'Routes insurance claims to appropriate processors for optimal adjudication and payment speed.',
        'DenialIntervention': 'Identifies claim denials and applies targeted interventions to maximize recovery and reduce future denials.',
        'PaymentPlanSequencing': 'Optimizes patient payment plan structures to maximize collection rates while maintaining patient satisfaction.',
        'BillingCodeOptimization': 'Optimizes billing code selection to maximize reimbursement while ensuring compliance and accuracy.',
        'RevenueLeakageDetection': 'Detects and prevents revenue leakage through missed charges, under-coding, and billing errors.',
        'PatientBillingPrioritization': 'Prioritizes patient billing activities to maximize collection rates and minimize bad debt.',
        'ClaimsRejectionRecovery': 'Recovers rejected claims through systematic review, correction, and resubmission strategies.',
        'PreAuthorizationWorkflow': 'Optimizes pre-authorization workflows to minimize delays and denials while ensuring timely care.',
        'DenialAppealsSequencing': 'Prioritizes and sequences denial appeals to maximize recovery rates and minimize appeal costs.',
        'PaymentReconciliation': 'Reconciles payments across multiple systems to ensure accurate posting and identify discrepancies.',
        'CostToCollectOptimization': 'Minimizes cost-to-collect metrics while maximizing net revenue through efficient processes.',
        'ContractComplianceScoring': 'Monitors and optimizes payer contract compliance to maximize reimbursement and minimize penalties.',
        'InsurancePlanMatching': 'Matches patients to optimal insurance plans to maximize coverage and minimize out-of-pocket costs.',
        'RevenueForecastSimulation': 'Forecasts revenue based on patient volumes, payer mix, and collection rates for financial planning.',
        'PatientFinancialCounseling': 'Optimizes financial counseling delivery to improve payment rates and patient satisfaction.',

        // Financial Trading environments
        'StockTrading': 'Single-asset stock trading with risk-adjusted rewards using Differential Sharpe Ratio, transaction costs, and slippage modeling.',
        'PortfolioAllocation': 'Multi-asset portfolio optimization using CRRA utility rewards with dynamic rebalancing and turnover-based transaction costs.',
        'OptionsPricing': 'Options delta hedging environment with Black-Scholes benchmarking, optional stochastic volatility, and hedge error minimization.',

        // Clinical Trials environments
        'TrialPatientMatching': 'Matches patients to appropriate clinical trials based on eligibility criteria and trial requirements.',
        'AdaptiveTrialDesign': 'Adapts trial protocols in real-time based on interim results to maximize efficiency and ethical outcomes.',
        'EnrollmentAcceleration': 'Accelerates patient enrollment in clinical trials through targeted outreach and streamlined processes.',
        'ProtocolDeviationMitigation': 'Identifies and mitigates protocol deviations to maintain trial integrity and regulatory compliance.',
        'DrugDosageTrialSequencing': 'Optimizes drug dosage escalation sequences in Phase I trials to balance safety and efficiency.',
        'AdaptiveCohortAllocation': 'Dynamically allocates patients to trial cohorts based on biomarker responses and safety data.',
        'TrialProtocolOptimization': 'Optimizes trial protocols to balance scientific rigor with patient recruitment and retention.',
        'DrugSupplySequencing': 'Manages drug supply chains for clinical trials to prevent shortages and minimize waste.',
        'TrialSiteResourceAllocation': 'Allocates resources across trial sites to maximize enrollment and data quality.',
        'PatientFollowUpScheduling': 'Optimizes patient follow-up schedules in trials to maximize retention and data completeness.',
        'EnrollmentFunnelOptimization': 'Optimizes the patient enrollment funnel from screening to randomization to maximize throughput.',
        'AdverseEventPrediction': 'Predicts and prevents adverse events in clinical trials through proactive monitoring.',
        'TrialOutcomeForecasting': 'Forecasts trial outcomes based on interim data to inform go/no-go decisions.',
        'PatientRetentionSequencing': 'Optimizes patient retention strategies to minimize dropouts and maximize data quality.',
        'MultiTrialResourceCoordination': 'Coordinates resources across multiple concurrent trials to maximize efficiency.',
        
        // Hospital Operations environments
        'StaffingAllocation': 'Allocates staff across departments to optimize patient care and operational efficiency.',
        'ORUtilization': 'Maximizes operating room utilization while balancing elective and emergency case needs.',
        'SupplyChainInventory': 'Manages medical supply inventory to prevent shortages while minimizing carrying costs.',
        'BedTurnoverOptimization': 'Optimizes bed turnover processes to maximize capacity and minimize patient wait times.',
        'EquipmentMaintenance': 'Schedules equipment maintenance to minimize downtime while ensuring patient safety.',
        
        // Telehealth environments
        'VirtualVisitRouting': 'Routes virtual visits to appropriate providers based on patient needs and provider availability.',
        'EscalationPolicy': 'Determines when to escalate virtual visits to in-person care based on clinical indicators.',
        'ProviderLoadBalancing': 'Balances provider workloads across virtual and in-person care to maximize access.',
        'FollowUpOptimization': 'Optimizes follow-up visit scheduling for telehealth patients to ensure continuity of care.',
        'DigitalAdherenceCoaching': 'Delivers digital coaching interventions to improve medication and treatment adherence.',
        
        // Interoperability environments
        'DataReconciliation': 'Reconciles data across multiple operational systems to ensure data integrity and consistency.',
        'CrossSystemAlertPrioritization': 'Prioritizes alerts from multiple systems to prevent alert fatigue and ensure critical notifications.',
        'DuplicateRecordResolution': 'Identifies and resolves duplicate patient records across systems to maintain data quality.',
        'InterFacilityTransfer': 'Optimizes patient transfers between facilities to ensure continuity of care and data exchange.',
        'HIERouting': 'Routes health information exchange messages to appropriate systems and workflows.',
        
        // Cross-Workflow environments
        'PatientJourneyOptimization': 'Multi-agent optimization across the entire patient care continuum from admission to discharge.',
        'HospitalThroughput': 'Optimizes hospital-wide throughput to maximize capacity utilization and patient flow.',
        'ClinicalFinancialTradeoff': 'Balances clinical quality and financial performance across all hospital operations.',
        'ValueBasedCareOptimization': 'Optimizes value-based care metrics including quality scores and cost efficiency.',
        'MultiHospitalNetworkCoordination': 'Coordinates operations across hospital networks to maximize resource utilization and care quality.',
        'JiraIssueResolution': 'Jira Issue Resolution Flow: resolve issues end-to-end via get_issue_summary_and_description → get_transitions → transition_issue.',
        'JiraStatusUpdate': 'Jira Status Update Workflow: change issue status using get_transitions → transition_issue with valid transition IDs.',
        'JiraCommentManagement': 'Jira Comment Thread Management: add_comment → get_comments for issue comment workflows.',
        'JiraSubtaskManagement': 'IT Operations: get_issue_summary_and_description → create_subtask for adding subtasks to issues.',
        // HR & Payroll (Workday, SAP SuccessFactors, ADP)
        'WorkdayCreateRecord': 'Workday: Create worker record with correct supervisory org placement and compensation plan initialization.',
        'WorkdayBulkImport': 'Workday: Bulk integration with EIB processing and error summary report for worker records.',
        'WorkdayTimeOffExpense': 'Workday: Time-off and expense report approval with balance validation and compliance checks.',
        'SAPSuccessFactorsCreateRecord': 'SAP SuccessFactors: Create employment record with job classification, pay group, and effective-dated position link.',
        'SAPSuccessFactorsBulkImport': 'SAP SuccessFactors: Bulk upsert with validation and merge/insert report for employee data.',
        'SAPSuccessFactorsOnboarding': 'SAP SuccessFactors: Employee onboarding with required forms and hiring manager tasks.',
        'ADPCreateWorker': 'ADP: Create worker with pay group, tax jurisdiction, and organizational assignment.',
        'ADPBulkImport': 'ADP: Bulk worker import with position management and pay calendar validation.',
        'ADPTimeOffPayroll': 'ADP: Time-off request with accrual verification and supervisor approval workflow.'
    };
    
    return descriptions[envName] || (category === 'jira' ? `Jira workflow environment for ${envName.replace(/([A-Z])/g, ' $1').trim().toLowerCase()} optimization.` : category === 'hr_payroll' ? `HR & Payroll workflow environment for ${envName.replace(/([A-Z])/g, ' $1').trim().toLowerCase()}.` : `Reinforcement learning environment for ${category.replace('_', ' ')} optimization and decision support.`);
}

// Generate use-case-specific descriptions
function getUseCaseDescription(envName, category) {
    const useCases = {
        // Clinical
        'TreatmentPathwayOptimization': 'Complex patient cases requiring coordinated multi-step treatment plans across multiple specialties.',
        'SepsisEarlyIntervention': 'Critical care units, emergency departments, and inpatient wards for early sepsis detection.',
        'ICUResourceAllocation': 'Intensive care units managing bed capacity, staff allocation, and patient transfers.',
        'SurgicalScheduling': 'Operating room management, surgical services, and perioperative care coordination.',
        'DiagnosticTestSequencing': 'Clinical decision support for ordering and sequencing diagnostic tests efficiently.',
        'MedicationDosingOptimization': 'Pharmacy services, medication management, and personalized medicine programs.',
        'ReadmissionReduction': 'Care transition programs, discharge planning, and post-acute care coordination.',
        'CareCoordination': 'Care management programs, patient navigation, and multi-provider care coordination.',
        'ChronicDiseaseManagement': 'Primary care, disease management programs, and population health initiatives.',
        'EmergencyTriage': 'Emergency departments, urgent care centers, and triage systems.',
        
        // Imaging
        'ImagingOrderPrioritization': 'Radiology departments, imaging centers, and emergency imaging services.',
        'RadiologyScheduling': 'Radiology scheduling departments and imaging center operations.',
        'ScanParameterOptimization': 'Radiology quality improvement and radiation safety programs.',
        'ImagingWorkflowRouting': 'PACS administrators and imaging workflow optimization teams.',
        'EquipmentUtilization': 'Imaging center operations and multi-site radiology departments.',
        
        // Population Health
        'RiskStratification': 'Population health management, care coordination, and health plan operations.',
        'PreventiveOutreach': 'Primary care practices, health plans, and population health programs.',
        'VaccinationAllocation': 'Public health departments, health systems, and vaccination programs.',
        'HighRiskMonitoring': 'Care management programs, chronic disease management, and patient monitoring services.',
        'PopulationCostOptimization': 'Health plans, accountable care organizations, and population health management.',
        
        // Revenue Cycle
        'ClaimsRouting': 'Revenue cycle management, billing departments, and claims processing centers.',
        'DenialIntervention': 'Revenue cycle management, denial management teams, and billing operations.',
        'PaymentPlanSequencing': 'Patient financial services, billing departments, and revenue cycle management.',
        'BillingCodeOptimization': 'Coding departments, revenue integrity teams, and billing operations.',
        'RevenueLeakageDetection': 'Revenue cycle management, finance departments, and billing operations.',

        // Financial Trading
        'StockTrading': 'Quantitative trading desks, algorithmic trading teams, and financial engineering research.',
        'PortfolioAllocation': 'Portfolio management teams, asset allocation strategists, and wealth management firms.',
        'OptionsPricing': 'Derivatives trading desks, options market makers, and risk management teams.',

        // Clinical Trials
        'TrialPatientMatching': 'Clinical research organizations, trial sites, and research coordinators.',
        'AdaptiveTrialDesign': 'Biostatistics teams, clinical research organizations, and trial sponsors.',
        'EnrollmentAcceleration': 'Clinical trial sites, research coordinators, and patient recruitment teams.',
        'ProtocolDeviationMitigation': 'Clinical research quality assurance and regulatory compliance teams.',
        'DrugDosageTrialSequencing': 'Phase I clinical trial units and early development research teams.',
        
        // Hospital Operations
        'StaffingAllocation': 'Hospital operations, workforce management, and staffing departments.',
        'ORUtilization': 'Operating room management, surgical services, and perioperative departments.',
        'SupplyChainInventory': 'Supply chain management, materials management, and procurement departments.',
        'BedTurnoverOptimization': 'Bed management, patient flow, and capacity management teams.',
        'EquipmentMaintenance': 'Biomedical engineering, facilities management, and equipment maintenance teams.',
        
        // Telehealth
        'VirtualVisitRouting': 'Telehealth platforms, virtual care delivery, and remote patient services.',
        'EscalationPolicy': 'Telehealth triage, care coordination, and virtual care management.',
        'ProviderLoadBalancing': 'Telehealth platforms, provider scheduling, and virtual care operations.',
        'FollowUpOptimization': 'Telehealth care management and virtual care coordination.',
        'DigitalAdherenceCoaching': 'Digital health programs, medication adherence, and patient engagement platforms.',
        
        // Interoperability
        'DataReconciliation': 'Health information exchanges, data integration teams, and interoperability programs.',
        'CrossSystemAlertPrioritization': 'Clinical informatics, alert management, and system integration teams.',
        'DuplicateRecordResolution': 'Health information management, master patient index, and data quality teams.',
        'InterFacilityTransfer': 'Care coordination, transfer centers, and health system operations.',
        'HIERouting': 'Health information exchange operations and interoperability teams.',
        
        // Cross-Workflow
        'PatientJourneyOptimization': 'Care coordination, patient flow optimization, and health system operations.',
        'HospitalThroughput': 'Hospital operations, capacity management, and patient flow optimization.',
        'ClinicalFinancialTradeoff': 'Hospital administration, finance, and clinical operations leadership.',
        'ValueBasedCareOptimization': 'Accountable care organizations, value-based care programs, and health system strategy.',
        'MultiHospitalNetworkCoordination': 'Health system operations, network management, and multi-site coordination.',
        'JiraIssueResolution': 'Issue resolution workflows, ticket closure, and status transitions in Jira.',
        'JiraStatusUpdate': 'Status updates and moving issues (e.g. To Do → In Progress → Done) in Jira.',
        'JiraCommentManagement': 'Adding and retrieving issue comments in Jira.',
        'JiraSubtaskManagement': 'IT Operations: subtask management for existing Jira issues.',
        // HR & Payroll
        'WorkdayCreateRecord': 'HR operations, worker onboarding, and Workday CCX API integration.',
        'WorkdayBulkImport': 'Bulk worker data import and EIB integration in Workday.',
        'WorkdayTimeOffExpense': 'Time-off and expense approval workflows in Workday.',
        'SAPSuccessFactorsCreateRecord': 'Employment records and SAP SuccessFactors OData integration.',
        'SAPSuccessFactorsBulkImport': 'Bulk employee data upsert in SAP SuccessFactors.',
        'SAPSuccessFactorsOnboarding': 'New hire onboarding and hiring manager tasks in SAP SuccessFactors.',
        'ADPCreateWorker': 'Worker creation and ADP HR API integration.',
        'ADPBulkImport': 'Bulk worker import and ADP payroll integration.',
        'ADPTimeOffPayroll': 'Time-off requests and payroll-linked approval in ADP.'
    };
    
    return useCases[envName] || (category === 'jira' ? `Jira workflow: ${envName.replace(/([A-Z])/g, ' $1').trim().toLowerCase()}.` : category === 'hr_payroll' ? `HR & Payroll: ${envName.replace(/([A-Z])/g, ' $1').trim().toLowerCase()}.` : `General ${category.replace('_', ' ')} optimization and decision support applications.`);
}

// Save/favorite management functions
function resetAllSaveCounts() {
    // Reset all save counts to 0 to remove fake random numbers (only run once)
    const savedData = JSON.parse(localStorage.getItem('agentwork_simulator_saves') || '{}');
    const resetFlag = localStorage.getItem('agentwork_simulator_counts_reset');
    
    // Only reset if we haven't done it before
    if (!resetFlag) {
        Object.keys(savedData).forEach(envName => {
            // Reset count to 0 but keep saved state
            if (savedData[envName].count > 4) {
                savedData[envName].count = 0;
            }
        });
        localStorage.setItem('agentwork_simulator_saves', JSON.stringify(savedData));
        localStorage.setItem('agentwork_simulator_counts_reset', 'true');
    }
}

function initializeSaveData(envName) {
    const savedData = JSON.parse(localStorage.getItem('agentwork_simulator_saves') || '{}');
    
    if (!savedData[envName]) {
        // Initialize with 0 count for authentic, legitimate appearance
        savedData[envName] = { 
            saved: false, 
            count: 0 
        };
        localStorage.setItem('agentwork_simulator_saves', JSON.stringify(savedData));
    }
    return savedData;
}

function getSavedCount(envName) {
    const savedData = initializeSaveData(envName);
    return savedData[envName].count;
}

function isSaved(envName) {
    const savedData = JSON.parse(localStorage.getItem('agentwork_simulator_saves') || '{}');
    return savedData[envName]?.saved || false;
}

function toggleSave(envName) {
    const savedData = initializeSaveData(envName);
    
    savedData[envName].saved = !savedData[envName].saved;
    if (savedData[envName].saved) {
        savedData[envName].count += 1;
    } else {
        savedData[envName].count = Math.max(0, savedData[envName].count - 1);
    }
    
    localStorage.setItem('agentwork_simulator_saves', JSON.stringify(savedData));
    updateSaveButton(envName);
}

function updateSaveButton(envName) {
    const saveBtn = document.querySelector(`[data-save-env="${envName}"]`);
    if (saveBtn) {
        const saved = isSaved(envName);
        const count = getSavedCount(envName);
        saveBtn.innerHTML = saved 
            ? `❤️ <span class="save-count">${count}</span>`
            : `🤍 <span class="save-count">${count}</span>`;
        saveBtn.classList.toggle('saved', saved);
    }
}

// Data-driven chip definitions for environment cards.
// Each entry maps a data key to a display format. Order = display priority.
var CARD_CHIP_FIELDS = [
    { key: 'category',      label: null,             format: 'badge',  cssClass: function(e) { return 'category-' + e.category; } },
    { key: 'system',        label: 'System',         format: 'chip',   filter: function(v) { return v && v !== 'Custom' && v !== ''; } },
    { key: 'workflow',      label: 'Workflow',       format: 'chip',   filter: function(v) { return v && v !== 'Cross-Workflow' && v !== ''; } },
    { key: 'actionSpace',   label: 'Actions',        format: 'chip',   filter: function(v) { return v && v !== 'N/A'; } },
    { key: 'stateFeatures', label: 'Features',       format: 'chip',   filter: function(v) { return v && v !== 'N/A'; } },
    { key: 'actionType',    label: 'Type',           format: 'chip',   filter: function(v) { return v && v !== 'Discrete'; } },
    { key: 'multi_agent',   label: 'Multi-Agent',    format: 'flag',   filter: function(v) { return v === true; } }
];

function createEnvCard(env) {
    var displayName = formatEnvironmentName(env.name);
    var isPinned = PINNED_ENV_NAMES.indexOf(env.name) !== -1;

    // Build chip HTML from available metadata
    var chips = '';
    for (var ci = 0; ci < CARD_CHIP_FIELDS.length; ci++) {
        var field = CARD_CHIP_FIELDS[ci];
        var val = env[field.key];
        if (field.filter) { if (!field.filter(val)) continue; }
        else if (val === undefined || val === null || val === '') continue;

        if (field.format === 'badge') {
            chips += '<span class="env-category ' + field.cssClass(env) + '">' + (val || 'other') + '</span>';
        } else if (field.format === 'flag') {
            chips += '<span class="env-chip env-chip--flag">' + field.label + '</span>';
        } else {
            var display = field.label ? field.label + ': ' + val : val;
            chips += '<span class="env-chip">' + display + '</span>';
        }
    }

    var pinnedClass = isPinned ? ' env-card--pinned' : '';
    var pinnedBadge = isPinned ? '<span class="env-pinned-badge">&#11088;</span>' : '';

    return '<div class="env-card' + pinnedClass + '" data-env="' + env.name + '" style="cursor:pointer;">' +
        '<div class="env-card-header"><div>' +
            '<div class="env-name">' + pinnedBadge + displayName + '</div>' +
        '</div></div>' +
        '<div class="env-description">' +
            (env.description || getEnvironmentDescription(env.name, env.category || 'other') || 'Reinforcement learning environment for workflow optimization.') +
        '</div>' +
        '<div class="env-chip-row">' + chips + '</div>' +
    '</div>';
}

function getDefaultWhatItDoes(category, envName) {
    // Generate environment-specific descriptions
    const envSpecificDescriptions = {
        // Clinical
        'TreatmentPathwayOptimization': `
            <p>This RL environment optimizes treatment sequences for patients with multiple conditions. 
            It learns to balance clinical outcomes, efficiency, and cost-effectiveness by determining 
            the optimal order and timing of treatments, medications, and interventions.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Reduces treatment pathway length and complexity</li>
                <li>Improves patient outcomes through optimized sequencing</li>
                <li>Minimizes treatment delays and wait times</li>
                <li>Maximizes cost-effectiveness of care delivery</li>
            </ul>
        `,
        'SepsisEarlyIntervention': `
            <p>This RL environment focuses on early detection and intervention for sepsis cases. 
            It uses SOFA scores, vital signs, and clinical indicators to identify at-risk patients 
            and trigger appropriate interventions before sepsis becomes life-threatening.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Reduces sepsis mortality rates through early detection</li>
                <li>Minimizes time to antibiotic administration</li>
                <li>Improves bundle compliance and protocol adherence</li>
                <li>Prevents progression to severe sepsis and septic shock</li>
            </ul>
        `,
        'ICUResourceAllocation': `
            <p>This RL environment optimally allocates ICU beds and staff resources based on patient 
            acuity, resource availability, and predicted outcomes. It helps balance capacity constraints 
            with patient care needs.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Maximizes ICU bed utilization and efficiency</li>
                <li>Reduces patient wait times for critical care</li>
                <li>Optimizes staff allocation across acuity levels</li>
                <li>Improves patient outcomes through timely ICU access</li>
            </ul>
        `,
        'SurgicalScheduling': `
            <p>This RL environment intelligently schedules surgical procedures to optimize OR utilization 
            while minimizing patient wait times, cancellations, and resource conflicts. It balances 
            elective and emergency cases effectively.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Maximizes operating room utilization rates</li>
                <li>Reduces surgical cancellations and delays</li>
                <li>Minimizes patient wait times for procedures</li>
                <li>Optimizes resource allocation across surgical specialties</li>
            </ul>
        `,
        'DiagnosticTestSequencing': `
            <p>This RL environment determines the optimal order of diagnostic tests to accelerate 
            diagnosis while minimizing costs and delays. It considers test dependencies, urgency, 
            and resource availability.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Accelerates time to diagnosis</li>
                <li>Reduces unnecessary and redundant testing</li>
                <li>Minimizes diagnostic costs</li>
                <li>Improves test result turnaround times</li>
            </ul>
        `,
        'MedicationDosingOptimization': `
            <p>This RL environment personalizes medication dosages based on patient characteristics, 
            drug interactions, therapeutic response, and safety considerations. It optimizes dosing 
            regimens for maximum efficacy and minimum side effects.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Improves therapeutic outcomes through personalized dosing</li>
                <li>Reduces medication-related adverse events</li>
                <li>Minimizes drug interactions and complications</li>
                <li>Optimizes medication costs and resource use</li>
            </ul>
        `,
        'ReadmissionReduction': `
            <p>This RL environment identifies high-risk entities and applies targeted interventions 
            to prevent avoidable repeat work or reprocessing. It optimizes handoffs, follow-up actions, 
            and transition management across the workflow.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Reduces rework and retries</li>
                <li>Improves transition quality between process stages</li>
                <li>Enhances overall outcome quality</li>
                <li>Reduces costs through prevention</li>
            </ul>
        `,
        'CareCoordination': `
            <p>This RL environment coordinates care across multiple providers and departments to 
            ensure seamless patient transitions and continuity. It optimizes communication, handoffs, 
            and care plan execution.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Improves care continuity across providers</li>
                <li>Reduces care gaps and duplications</li>
                <li>Enhances patient satisfaction</li>
                <li>Optimizes resource use across care settings</li>
            </ul>
        `,
        'ChronicDiseaseManagement': `
            <p>This RL environment manages chronic conditions through proactive monitoring, medication 
            adherence support, and lifestyle interventions. It optimizes intervention timing and intensity 
            to prevent complications.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Prevents chronic disease complications</li>
                <li>Improves medication adherence rates</li>
                <li>Reduces emergency department visits</li>
                <li>Enhances patient self-management capabilities</li>
            </ul>
        `,
        'EmergencyTriage': `
            <p>This RL environment prioritizes emergency department patients based on acuity, resource 
            availability, and clinical urgency. It optimizes triage decisions to ensure critical 
            patients receive timely care.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Reduces time to treatment for critical patients</li>
                <li>Improves ED throughput and capacity</li>
                <li>Minimizes patient wait times</li>
                <li>Optimizes resource allocation in emergency settings</li>
            </ul>
        `,
        // Imaging
        'ImagingOrderPrioritization': `
            <p>This RL environment prioritizes imaging orders based on clinical urgency, equipment 
            availability, and patient needs. It reduces wait times for critical studies while 
            maintaining high throughput.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Reduces wait times for urgent imaging studies</li>
                <li>Improves scanner utilization and throughput</li>
                <li>Optimizes scheduling to minimize patient delays</li>
                <li>Enhances revenue through better resource management</li>
            </ul>
        `,
        'RadiologyScheduling': `
            <p>This RL environment schedules radiology appointments to maximize scanner utilization 
            while meeting patient and referring physician needs. It balances routine and urgent studies 
            effectively.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Maximizes scanner utilization rates</li>
                <li>Reduces patient scheduling delays</li>
                <li>Optimizes appointment slot allocation</li>
                <li>Improves patient and provider satisfaction</li>
            </ul>
        `,
        'ScanParameterOptimization': `
            <p>This RL environment optimizes imaging scan parameters to balance image quality, 
            radiation dose, and scan duration. It personalizes scan settings for each patient 
            and study type.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Reduces radiation exposure while maintaining image quality</li>
                <li>Improves diagnostic image quality</li>
                <li>Minimizes scan duration and patient discomfort</li>
                <li>Ensures compliance with radiation safety guidelines</li>
            </ul>
        `,
        'ImagingWorkflowRouting': `
            <p>This RL environment routes imaging studies through optimal workflow paths to minimize 
            processing time and maximize throughput. It optimizes the journey from order to report.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Accelerates imaging study processing</li>
                <li>Reduces time from scan to report</li>
                <li>Optimizes workflow efficiency</li>
                <li>Improves radiologist productivity</li>
            </ul>
        `,
        'EquipmentUtilization': `
            <p>This RL environment maximizes utilization of imaging equipment including CT, MRI, 
            and ultrasound scanners across multiple facilities. It balances demand with capacity 
            effectively.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Maximizes equipment utilization rates</li>
                <li>Reduces equipment idle time</li>
                <li>Optimizes multi-site resource allocation</li>
                <li>Improves return on equipment investment</li>
            </ul>
        `,
        // Population Health
        'RiskStratification': `
            <p>This RL environment stratifies patient populations by risk level to enable targeted 
            interventions and resource allocation. It identifies high-risk patients who would 
            benefit most from proactive care.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Identifies high-risk patients for targeted interventions</li>
                <li>Optimizes resource allocation to highest-need patients</li>
                <li>Improves population health outcomes</li>
                <li>Reduces preventable hospitalizations</li>
            </ul>
        `,
        'PreventiveOutreach': `
            <p>This RL environment identifies patients due for preventive care and optimizes outreach 
            strategies to improve screening rates. It personalizes communication and timing for 
            maximum engagement.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Increases preventive care screening rates</li>
                <li>Improves patient engagement and compliance</li>
                <li>Enables early detection of health issues</li>
                <li>Reduces long-term costs</li>
            </ul>
        `,
        'VaccinationAllocation': `
            <p>This RL environment allocates vaccines across populations to maximize coverage while 
            prioritizing high-risk groups. It optimizes distribution strategies during normal operations 
            and public health emergencies.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Maximizes vaccination coverage rates</li>
                <li>Prioritizes high-risk populations effectively</li>
                <li>Minimizes vaccine waste and expiration</li>
                <li>Improves public health outcomes</li>
            </ul>
        `,
        'HighRiskMonitoring': `
            <p>This RL environment monitors high-risk patients proactively to prevent adverse events 
            and reduce emergency department visits. It optimizes monitoring frequency and 
            intervention timing.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Prevents adverse events through proactive monitoring</li>
                <li>Reduces emergency department visits</li>
                <li>Improves patient outcomes and quality of life</li>
                <li>Optimizes care management resource allocation</li>
            </ul>
        `,
        'PopulationCostOptimization': `
            <p>This RL environment optimizes population health spending to maximize outcomes while 
            controlling per-member costs. It allocates resources across programs and interventions 
            strategically.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Maximizes population health outcomes per dollar spent</li>
                <li>Controls per-member total costs</li>
                <li>Optimizes resource allocation across programs</li>
                <li>Improves value-based care performance</li>
            </ul>
        `,
        // Revenue Cycle
        'ClaimsRouting': `
            <p>This RL environment routes insurance claims to appropriate processors for optimal 
            adjudication and payment speed. It matches claims to processors based on expertise, 
            capacity, and success rates.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Increases first-pass claim approval rates</li>
                <li>Accelerates payment processing times</li>
                <li>Reduces claim denials and rejections</li>
                <li>Improves cash flow and revenue collection</li>
            </ul>
        `,
        'DenialIntervention': `
            <p>This RL environment identifies claim denials and applies targeted interventions to 
            maximize recovery and reduce future denials. It prioritizes high-value denials and 
            optimizes appeal strategies.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Increases denial recovery rates</li>
                <li>Reduces future denial rates through prevention</li>
                <li>Optimizes appeal resource allocation</li>
                <li>Improves net revenue collection</li>
            </ul>
        `,
        'PaymentPlanSequencing': `
            <p>This RL environment optimizes patient payment plan structures to maximize collection 
            rates while maintaining patient satisfaction. It personalizes payment terms based on 
            patient financial capacity.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Increases patient payment collection rates</li>
                <li>Reduces bad debt and write-offs</li>
                <li>Improves patient financial satisfaction</li>
                <li>Optimizes payment plan terms and structures</li>
            </ul>
        `,
        'BillingCodeOptimization': `
            <p>This RL environment optimizes billing code selection to maximize reimbursement while 
            ensuring compliance and accuracy. It helps prevent under-coding and over-coding issues.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Maximizes appropriate reimbursement</li>
                <li>Ensures billing compliance and accuracy</li>
                <li>Reduces audit risk and penalties</li>
                <li>Improves revenue integrity</li>
            </ul>
        `,
        'RevenueLeakageDetection': `
            <p>This RL environment detects and prevents revenue leakage through missed charges, 
            under-coding, and billing errors. It identifies patterns and applies corrective actions.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Identifies and recovers lost revenue</li>
                <li>Prevents future revenue leakage</li>
                <li>Improves charge capture accuracy</li>
                <li>Enhances revenue cycle performance</li>
            </ul>
        `,
        // Clinical Trials
        'TrialPatientMatching': `
            <p>This RL environment matches patients to appropriate clinical trials based on eligibility 
            criteria and trial requirements. It optimizes matching to maximize enrollment and trial 
            success rates.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Accelerates patient enrollment in trials</li>
                <li>Improves patient-trial match quality</li>
                <li>Maximizes trial enrollment rates</li>
                <li>Enhances trial success probability</li>
            </ul>
        `,
        'AdaptiveTrialDesign': `
            <p>This RL environment adapts trial protocols in real-time based on interim results to 
            maximize efficiency and ethical outcomes. It optimizes trial design dynamically.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Accelerates trial completion times</li>
                <li>Improves trial efficiency and cost-effectiveness</li>
                <li>Maximizes patient safety and ethical outcomes</li>
                <li>Enhances trial success rates</li>
            </ul>
        `,
        'EnrollmentAcceleration': `
            <p>This RL environment accelerates patient enrollment in clinical trials through targeted 
            outreach and streamlined processes. It optimizes recruitment strategies and timing.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Reduces time to full enrollment</li>
                <li>Improves patient recruitment rates</li>
                <li>Optimizes recruitment resource allocation</li>
                <li>Enhances trial timeline adherence</li>
            </ul>
        `,
        'ProtocolDeviationMitigation': `
            <p>This RL environment identifies and mitigates protocol deviations to maintain trial 
            integrity and regulatory compliance. It prevents deviations through proactive monitoring.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Reduces protocol deviation rates</li>
                <li>Maintains trial data integrity</li>
                <li>Ensures regulatory compliance</li>
                <li>Improves trial quality and validity</li>
            </ul>
        `,
        'DrugDosageTrialSequencing': `
            <p>This RL environment optimizes drug dosage escalation sequences in Phase I trials to 
            balance safety and efficiency. It determines optimal dose levels and escalation schedules.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Maximizes patient safety in dose-finding trials</li>
                <li>Accelerates identification of optimal doses</li>
                <li>Reduces trial duration and costs</li>
                <li>Improves trial efficiency</li>
            </ul>
        `,
        // Hospital Operations
        'StaffingAllocation': `
            <p>This RL environment allocates staff across departments to optimize patient care and 
            operational efficiency. It balances workload, skill requirements, and cost constraints.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Optimizes staff utilization and productivity</li>
                <li>Reduces staffing costs while maintaining quality</li>
                <li>Improves patient care coverage</li>
                <li>Enhances staff satisfaction through balanced workloads</li>
            </ul>
        `,
        'ORUtilization': `
            <p>This RL environment maximizes operating room utilization while balancing elective and 
            emergency case needs. It optimizes OR scheduling and resource allocation.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Maximizes OR utilization rates</li>
                <li>Reduces OR idle time and inefficiencies</li>
                <li>Balances elective and emergency cases</li>
                <li>Improves surgical services revenue</li>
            </ul>
        `,
        'SupplyChainInventory': `
            <p>This RL environment manages medical supply inventory to prevent shortages while minimizing 
            carrying costs. It optimizes ordering, stocking, and distribution strategies.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Prevents supply shortages and stockouts</li>
                <li>Minimizes inventory carrying costs</li>
                <li>Reduces waste and expiration</li>
                <li>Optimizes supply chain efficiency</li>
            </ul>
        `,
        'BedTurnoverOptimization': `
            <p>This RL environment optimizes bed turnover processes to maximize capacity and minimize 
            patient wait times. It coordinates cleaning, maintenance, and patient flow.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Reduces bed turnover time</li>
                <li>Maximizes bed capacity utilization</li>
                <li>Minimizes patient wait times for admission</li>
                <li>Improves patient flow and throughput</li>
            </ul>
        `,
        'EquipmentMaintenance': `
            <p>This RL environment schedules equipment maintenance to minimize downtime while ensuring 
            patient safety. It balances preventive maintenance with operational needs.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Minimizes equipment downtime</li>
                <li>Prevents equipment failures and safety issues</li>
                <li>Optimizes maintenance scheduling</li>
                <li>Extends equipment lifespan</li>
            </ul>
        `,
        // Telehealth
        'VirtualVisitRouting': `
            <p>This RL environment routes virtual visits to appropriate providers based on patient needs 
            and provider availability. It optimizes matching to maximize access and quality.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Reduces patient wait times for virtual care</li>
                <li>Improves provider-patient matching</li>
                <li>Maximizes provider utilization</li>
                <li>Enhances virtual care quality and satisfaction</li>
            </ul>
        `,
        'EscalationPolicy': `
            <p>This RL environment determines when to escalate virtual visits to in-person care based 
            on clinical indicators. It optimizes escalation decisions to ensure patient safety.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Ensures appropriate care escalation when needed</li>
                <li>Prevents unnecessary in-person visits</li>
                <li>Improves patient safety and outcomes</li>
                <li>Optimizes care delivery efficiency</li>
            </ul>
        `,
        'ProviderLoadBalancing': `
            <p>This RL environment balances provider workloads across virtual and in-person care to 
            maximize access. It optimizes scheduling and assignment strategies.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Balances provider workloads effectively</li>
                <li>Maximizes patient access to care</li>
                <li>Improves provider satisfaction</li>
                <li>Optimizes care delivery capacity</li>
            </ul>
        `,
        'FollowUpOptimization': `
            <p>This RL environment optimizes follow-up visit scheduling for telehealth patients to 
            ensure continuity of care. It personalizes follow-up timing and modality.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Improves care continuity for telehealth patients</li>
                <li>Optimizes follow-up visit timing</li>
                <li>Reduces care gaps and complications</li>
                <li>Enhances patient engagement and outcomes</li>
            </ul>
        `,
        'DigitalAdherenceCoaching': `
            <p>This RL environment delivers digital coaching interventions to improve medication and 
            treatment adherence. It personalizes coaching content, timing, and intensity.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Improves medication and treatment adherence</li>
                <li>Reduces treatment failures and complications</li>
                <li>Enhances patient engagement and self-management</li>
                <li>Optimizes intervention resource allocation</li>
            </ul>
        `,
        // Interoperability
        'DataReconciliation': `
            <p>This RL environment reconciles data across multiple operational systems to ensure data 
            integrity and consistency. It identifies and resolves discrepancies automatically.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Ensures data accuracy across systems</li>
                <li>Reduces data discrepancies and errors</li>
                <li>Improves data quality and reliability</li>
                <li>Enhances interoperability and data exchange</li>
            </ul>
        `,
        'CrossSystemAlertPrioritization': `
            <p>This RL environment prioritizes alerts from multiple systems to prevent alert fatigue 
            and ensure critical notifications. It filters and ranks alerts intelligently.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Reduces alert fatigue for clinicians</li>
                <li>Ensures critical alerts are not missed</li>
                <li>Improves clinical decision-making</li>
                <li>Enhances patient safety</li>
            </ul>
        `,
        'DuplicateRecordResolution': `
            <p>This RL environment identifies and resolves duplicate patient records across systems to 
            maintain data quality. It merges records intelligently while preserving data integrity.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Eliminates duplicate patient records</li>
                <li>Improves data quality and accuracy</li>
                <li>Enhances patient matching and identification</li>
                <li>Reduces data management errors</li>
            </ul>
        `,
        'InterFacilityTransfer': `
            <p>This RL environment optimizes patient transfers between facilities to ensure continuity 
            of care and data exchange. It coordinates transfer logistics and information sharing.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Improves care continuity during transfers</li>
                <li>Accelerates transfer processes</li>
                <li>Ensures complete data exchange</li>
                <li>Enhances patient safety during transitions</li>
            </ul>
        `,
        'HIERouting': `
            <p>This RL environment routes health information exchange messages to appropriate systems 
            and workflows. It optimizes message routing for efficiency and accuracy.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Accelerates health information exchange</li>
                <li>Ensures accurate message routing</li>
                <li>Improves interoperability efficiency</li>
                <li>Enhances data exchange reliability</li>
            </ul>
        `,
        // Cross-Workflow
        'PatientJourneyOptimization': `
            <p>This RL environment uses multi-agent optimization across the entire patient care continuum 
            from admission to discharge. It coordinates care across multiple departments and workflows.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Optimizes entire patient journey end-to-end</li>
                <li>Coordinates care across multiple departments</li>
                <li>Improves patient flow and throughput</li>
                <li>Maximizes care quality and efficiency</li>
            </ul>
        `,
        'HospitalThroughput': `
            <p>This RL environment optimizes hospital-wide throughput to maximize capacity utilization 
            and patient flow. It coordinates operations across all departments and services.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Maximizes hospital capacity utilization</li>
                <li>Improves patient flow and throughput</li>
                <li>Reduces bottlenecks and delays</li>
                <li>Enhances overall operational efficiency</li>
            </ul>
        `,
        'ClinicalFinancialTradeoff': `
            <p>This RL environment balances clinical quality and financial performance across all hospital 
            operations. It optimizes decisions to maximize value and outcomes.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Balances clinical quality with financial performance</li>
                <li>Maximizes value-based care outcomes</li>
                <li>Optimizes resource allocation strategically</li>
                <li>Improves overall hospital performance</li>
            </ul>
        `,
        'ValueBasedCareOptimization': `
            <p>This RL environment optimizes value-based care metrics including quality scores and cost 
            efficiency. It aligns operations with value-based payment models.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Improves quality scores and performance metrics</li>
                <li>Optimizes cost efficiency and resource use</li>
                <li>Maximizes value-based care payments</li>
                <li>Enhances population health outcomes</li>
            </ul>
        `,
        'MultiHospitalNetworkCoordination': `
            <p>This RL environment coordinates operations across hospital networks to maximize resource 
            utilization and care quality. It optimizes network-wide resource allocation and patient flow.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Maximizes network-wide resource utilization</li>
                <li>Improves care quality across facilities</li>
                <li>Optimizes patient transfers and routing</li>
                <li>Enhances network operational efficiency</li>
            </ul>
        `
    };
    
    // Return environment-specific description if available
    if (envSpecificDescriptions[envName]) {
        return envSpecificDescriptions[envName];
    }
    
    // Fallback to category-based descriptions
    const categoryDescriptions = {
        'clinical': `
            <p>This RL environment optimizes decision-making processes in operational settings. 
            It uses reinforcement learning to learn optimal strategies for task handling, resource allocation, 
            and sequencing. The agent learns from trial and error to maximize outcomes 
            while balancing efficiency and cost-effectiveness.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Improves patient outcomes through optimized care pathways</li>
                <li>Reduces treatment delays and wait times</li>
                <li>Maximizes resource utilization efficiency</li>
                <li>Minimizes clinical risks and complications</li>
            </ul>
        `,
        'imaging': `
            <p>This RL environment optimizes medical imaging operations, including order prioritization, 
            scheduling, and resource allocation. The agent learns to balance urgency, resource availability, 
            and operational efficiency to ensure critical imaging studies are completed promptly while 
            maintaining high throughput.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Reduces wait times for urgent imaging studies</li>
                <li>Improves scanner utilization and throughput</li>
                <li>Optimizes scheduling to minimize patient delays</li>
                <li>Enhances revenue through better resource management</li>
            </ul>
        `,
        'revenue_cycle': `
            <p>This RL environment optimizes revenue cycle management processes, including
            claims processing, denial management, and payment collection. The agent learns strategies
            to maximize revenue recovery while minimizing processing costs and delays.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Increases revenue collection rates</li>
                <li>Reduces claim denials and rejections</li>
                <li>Accelerates payment processing</li>
                <li>Improves cash flow and financial performance</li>
            </ul>
        `,
        'StockTrading': `
            <p>This RL environment simulates single-asset stock trading with realistic transaction costs
            and slippage modeling. The agent learns optimal buy/sell/hold strategies using the Differential
            Sharpe Ratio for risk-adjusted reward shaping.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Learns risk-adjusted trading strategies (Sharpe, Sortino, Calmar)</li>
                <li>Models realistic transaction costs and market slippage</li>
                <li>Supports 5 discrete trading actions with position limits</li>
                <li>Tracks portfolio value, drawdown, and trade statistics</li>
            </ul>
        `,
        'PortfolioAllocation': `
            <p>This RL environment optimizes multi-asset portfolio allocation using CRRA utility rewards.
            The agent learns to dynamically rebalance portfolio weights across multiple correlated assets
            while accounting for turnover-based transaction costs.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Dynamic multi-asset portfolio optimization</li>
                <li>CRRA utility reward for risk-aversion-aware decisions</li>
                <li>Handles correlated asset returns and regime changes</li>
                <li>Tracks Sharpe ratio, drawdown, and portfolio volatility</li>
            </ul>
        `,
        'OptionsPricing': `
            <p>This RL environment teaches delta hedging of short call option positions. The agent
            learns to minimize hedging P&L variance while managing transaction costs, with optional
            Heston-like stochastic volatility for realistic market conditions.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Learns adaptive hedging beyond Black-Scholes delta</li>
                <li>Supports stochastic volatility for realistic scenarios</li>
                <li>Benchmarks against analytical Black-Scholes solutions</li>
                <li>Tracks hedge error, P&L volatility, and options Greeks</li>
            </ul>
        `,
        'population_health': `
            <p>This RL environment optimizes population health management strategies, including preventive 
            care interventions, chronic disease management, and care coordination. The agent learns to 
            identify high-risk patients and allocate resources effectively to improve population health outcomes.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Improves population health metrics</li>
                <li>Reduces preventable hospitalizations</li>
                <li>Optimizes preventive care delivery</li>
                <li>Enhances care coordination across providers</li>
            </ul>
        `,
        'hospital_operations': `
            <p>This RL environment optimizes hospital operational processes, including bed management, 
            staff scheduling, and resource allocation. The agent learns to balance patient needs, 
            resource constraints, and operational efficiency to improve overall hospital performance.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Improves bed utilization and patient flow</li>
                <li>Optimizes staff scheduling and allocation</li>
                <li>Reduces operational costs</li>
                <li>Enhances patient satisfaction through reduced wait times</li>
            </ul>
        `,
        'clinical_trials': `
            <p>This RL environment optimizes clinical trial operations including patient matching, 
            enrollment, protocol adherence, and resource allocation. The agent learns to maximize 
            trial efficiency and success rates.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Accelerates trial enrollment and completion</li>
                <li>Improves trial efficiency and cost-effectiveness</li>
                <li>Enhances protocol compliance and data quality</li>
                <li>Maximizes trial success rates</li>
            </ul>
        `,
        'telehealth': `
            <p>This RL environment optimizes telehealth operations including visit routing, provider 
            allocation, escalation decisions, and follow-up scheduling. The agent learns to maximize 
            virtual care quality and efficiency.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Improves virtual care access and quality</li>
                <li>Optimizes provider utilization and workload</li>
                <li>Enhances patient satisfaction with virtual care</li>
                <li>Maximizes telehealth program effectiveness</li>
            </ul>
        `,
        'interoperability': `
            <p>This RL environment optimizes health information exchange and interoperability operations 
            including data reconciliation, alert prioritization, and message routing. The agent learns 
            to maximize data quality and exchange efficiency.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Improves data quality and accuracy</li>
                <li>Enhances interoperability and data exchange</li>
                <li>Reduces data errors and discrepancies</li>
                <li>Optimizes health information exchange efficiency</li>
            </ul>
        `,
        'cross_workflow': `
            <p>This RL environment uses multi-agent optimization to coordinate operations across multiple 
            workflows and departments. Agents collaborate to optimize complex, interconnected 
            enterprise processes.</p>
            <p><strong>Key Benefits:</strong></p>
            <ul>
                <li>Coordinates care across multiple workflows</li>
                <li>Optimizes system-wide operations</li>
                <li>Improves patient journey and outcomes</li>
                <li>Maximizes overall system performance</li>
            </ul>
        `
    };
    
    return categoryDescriptions[category] || `
        <p>This RL environment uses reinforcement learning to optimize operational processes and decision-making. 
        The agent learns optimal strategies through trial and error, maximizing desired outcomes while 
        balancing multiple objectives such as quality, operational efficiency, and financial performance.</p>
    `;
}

function getActionDescription(envName, action) {
    // Provide descriptions for common action patterns
    const actionLower = action.toLowerCase();
    
    // Generic descriptions based on action keywords
    if (actionLower.includes('schedule') || actionLower.includes('prioritize')) {
        if (actionLower.includes('urgent') || actionLower.includes('emergency')) {
            return 'Immediately schedule or prioritize this item due to high urgency or emergency status.';
        } else if (actionLower.includes('elective') || actionLower.includes('routine')) {
            return 'Schedule this item as a routine or elective procedure.';
        } else {
            return 'Schedule this item for processing or execution.';
        }
    } else if (actionLower.includes('defer') || actionLower.includes('delay')) {
        return 'Postpone this action to a later time, allowing more urgent items to be processed first.';
    } else if (actionLower.includes('cancel')) {
        return 'Cancel this item or operation, removing it from the queue.';
    } else if (actionLower.includes('reschedule')) {
        return 'Move this item to a different time slot or priority level.';
    } else if (actionLower.includes('admit')) {
        return 'Admit the patient to the facility or department.';
    } else if (actionLower.includes('discharge')) {
        return 'Discharge the patient from the facility or department.';
    } else if (actionLower.includes('transfer')) {
        return 'Transfer the patient or item to another location or department.';
    } else if (actionLower.includes('optimize') || actionLower.includes('improve')) {
        return 'Apply optimization strategies to improve outcomes or efficiency.';
    } else if (actionLower.includes('coordinate') || actionLower.includes('coordinate')) {
        return 'Coordinate care or resources across multiple departments or systems.';
    } else if (actionLower.includes('no_action') || actionLower.includes('wait') || actionLower.includes('skip')) {
        return 'Take no action at this step, maintaining the current state.';
    } else if (actionLower.includes('allocate') || actionLower.includes('assign')) {
        return 'Allocate or assign resources to this item or patient.';
    } else if (actionLower.includes('route') || actionLower.includes('send')) {
        return 'Route or send this item to a specific destination or processor.';
    } else if (actionLower.includes('intervene') || actionLower.includes('treat')) {
        return 'Apply intervention or treatment to address the current situation.';
    } else if (actionLower.includes('monitor') || actionLower.includes('observe')) {
        return 'Continue monitoring without taking immediate action.';
    } else if (actionLower.includes('escalate')) {
        return 'Escalate this item to a higher priority level or authority.';
    } else if (actionLower.includes('approve') || actionLower.includes('authorize')) {
        return 'Approve or authorize this action or request.';
    } else if (actionLower.includes('deny') || actionLower.includes('reject')) {
        return 'Deny or reject this request or action.';
    }
    
    // Environment-specific descriptions
    const envSpecific = {
        'ImagingOrderPrioritization': {
            'prioritize_urgent': 'Prioritize urgent imaging orders that require immediate attention.',
            'prioritize_routine': 'Process routine imaging orders in standard priority.',
            'defer': 'Defer non-urgent orders to allow urgent cases to be processed first.',
            'cancel': 'Cancel the imaging order.',
            'no_action': 'Take no action, maintaining current queue order.'
        },
        'TreatmentPathwayOptimization': {
            'optimize_pathway': 'Optimize the treatment pathway for better outcomes.',
            'add_intervention': 'Add a new intervention to the treatment plan.',
            'modify_sequence': 'Modify the sequence of treatments.',
            'no_action': 'Continue with current treatment pathway.'
        },
        'SepsisEarlyIntervention': {
            'intervene_immediate': 'Apply immediate intervention for suspected sepsis.',
            'monitor': 'Continue monitoring patient vitals and status.',
            'escalate_care': 'Escalate to higher level of care.',
            'no_action': 'Maintain current care level.'
        }
    };
    
    if (envSpecific[envName] && envSpecific[envName][action]) {
        return envSpecific[envName][action];
    }
    
    // Default: no description if we can't infer one
    return null;
}

function getDefaultHowToUse(category, envName) {
    return `
        <ol>
            <li><strong>Access the Environment:</strong> Click the "🧪 Environment" button to open the interactive environment console.</li>
            <li><strong>Configure Parameters:</strong> Adjust the environment configuration parameters in the left panel to match your workflow setting (e.g., queue sizes, resource availability, urgency levels).</li>
            <li><strong>Select Agent Strategy:</strong> Choose an RL agent strategy (Random, Urgency First, Value First, or Balanced) to see how different approaches perform.</li>
            <li><strong>Initialize:</strong> Click "Initialize" to start a new simulation episode with your configured parameters.</li>
            <li><strong>Run Simulation:</strong> Use "Step Forward" to advance one step at a time, or "Auto Run" to let the simulation run automatically at your selected speed.</li>
            <li><strong>Monitor Metrics:</strong> Watch real-time KPIs, metrics, and recommendations in the right panel to understand performance.</li>
            <li><strong>Analyze Results:</strong> Review the results summary at the bottom to assess clinical outcomes, operational efficiency, financial impact, and ROI.</li>
            <li><strong>Iterate and Optimize:</strong> Adjust parameters and strategies to find optimal configurations for your specific use case.</li>
        </ol>
        <p><strong>Training:</strong> For production use, click "Start Training" to train a custom RL agent on your historical data. The trained model can then be deployed to make real-time decisions.</p>
    `;
}

function closeEnvDetailPage() {
    const page = document.getElementById('env-detail-page');
    const catalog = document.getElementById('catalog-container');
    if (page) page.style.display = 'none';
    if (catalog) catalog.style.display = 'block';
}

// ─── Build Scenarios Section for detail page ───
function buildScenariosSection(envName, envCategory) {
    var cfg = window.TRAINING_CONFIG;
    var allScenarios = (cfg && cfg.scenarios) ? cfg.scenarios : [];
    var filtered = allScenarios.filter(function(s) { return s.category === envCategory; });

    var listHtml = '';
    if (filtered.length) {
        filtered.forEach(function(s, idx) {
            listHtml += '<div class="scenario-card" id="scenario-card-' + idx + '">' +
                '<div class="scenario-card-header">' +
                    '<span class="scenario-card-name">' + s.name + '</span>' +
                    '<span class="scenario-card-badge">' + s.category + '</span>' +
                    '<span class="scenario-card-tasks">' + s.task_count + ' tasks</span>' +
                '</div>' +
                '<p class="scenario-card-desc">' + s.description + '</p>' +
            '</div>';
        });
    } else {
        listHtml = '<p style="color:var(--text-secondary);font-size:0.9rem;">No scenarios configured for this environment category.</p>';
    }

    return '<div class="detail-collapsible" id="section-scenarios">' +
        '<button class="detail-collapsible-header" onclick="toggleDetailSection(\'section-scenarios\')">' +
            '<h2>' +
                '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>' +
                ' Scenarios <span style="font-size:0.75rem;font-weight:400;color:var(--text-secondary);margin-left:6px;">(' + filtered.length + ')</span>' +
            '</h2>' +
            '<svg class="detail-collapsible-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>' +
        '</button>' +
        '<div class="detail-collapsible-body" id="section-scenarios-body">' +
            '<div class="detail-collapsible-content">' +
                '<div class="scenarios-list">' + listHtml + '</div>' +
                '<div style="margin-top:1rem;">' +
                    '<button class="btn btn-outline btn-small" onclick="toggleAddScenarioForm()" id="btn-add-scenario">' +
                        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
                        ' Add Scenario' +
                    '</button>' +
                '</div>' +
                '<div id="add-scenario-form" style="display:none;margin-top:1rem;padding:1rem;background:var(--bg-tertiary);border-radius:8px;border:1px solid var(--border-color);">' +
                    '<h4 style="margin:0 0 0.75rem;font-size:0.9rem;color:var(--text-primary);">New Scenario (JSON)</h4>' +
                    '<textarea id="add-scenario-json" class="add-env-terraform-editor" rows="8" spellcheck="false" placeholder=\'{\n  "name": "My Scenario",\n  "category": "' + envCategory + '",\n  "task_count": 5,\n  "description": "Describe the scenario..."\n}\'></textarea>' +
                    '<div style="margin-top:0.75rem;display:flex;gap:8px;">' +
                        '<button class="btn btn-primary btn-small" onclick="saveNewScenario(\'' + envName.replace(/'/g, "\\'") + '\', \'' + envCategory + '\')">Save Scenario</button>' +
                        '<button class="btn btn-outline btn-small" onclick="toggleAddScenarioForm()">Cancel</button>' +
                    '</div>' +
                '</div>' +
            '</div>' +
        '</div>' +
    '</div>';
}

function toggleAddScenarioForm() {
    var form = document.getElementById('add-scenario-form');
    if (!form) return;
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}
window.toggleAddScenarioForm = toggleAddScenarioForm;

function saveNewScenario(envName, envCategory) {
    var textarea = document.getElementById('add-scenario-json');
    if (!textarea) return;
    try {
        var data = JSON.parse(textarea.value);
        if (!data.name) { showToast('Scenario name is required.', 'error'); return; }
        var newScenario = {
            id: 'sc_custom_' + Date.now(),
            name: data.name,
            category: data.category || envCategory,
            task_count: data.task_count || 1,
            description: data.description || ''
        };
        if (window.TRAINING_CONFIG && window.TRAINING_CONFIG.scenarios) {
            window.TRAINING_CONFIG.scenarios.push(newScenario);
        }
        showToast('Scenario "' + newScenario.name + '" added.', 'success');
        textarea.value = '';
        toggleAddScenarioForm();
        // Re-render the env detail to show updated scenarios
        showEnvironmentDetails(envName);
    } catch (e) {
        showToast('Invalid JSON: ' + e.message, 'error');
    }
}
window.saveNewScenario = saveNewScenario;

// ─── Build Verifiers Section for detail page ───
function buildVerifiersSection(envName, envCategory) {
    var verifierData = window.VERIFIER_DATA;
    var allVerifiers = (verifierData && verifierData.all) ? verifierData.all : [];
    var filtered = allVerifiers.filter(function(v) { return v.environment === envCategory; });

    var listHtml = '';
    if (filtered.length) {
        filtered.forEach(function(v, idx) {
            var typeClass = (v.type || '').replace(/[^a-z0-9-]/gi, '-').toLowerCase();
            var scoringHtml = '';
            if (v.logic && v.logic.scoring && typeof v.logic.scoring === 'object' && !Array.isArray(v.logic.scoring)) {
                var keys = Object.keys(v.logic.scoring);
                scoringHtml = '<div class="verifier-scoring">';
                keys.forEach(function(k) {
                    scoringHtml += '<span class="verifier-score-badge">' + k.replace(/_/g, ' ') + ': ' + v.logic.scoring[k] + '</span>';
                });
                scoringHtml += '</div>';
            }
            var subHtml = '';
            if (v.subVerifiers && v.subVerifiers.length) {
                subHtml = '<div class="verifier-subs"><span style="font-size:0.75rem;color:var(--text-secondary);font-weight:600;">Sub-verifiers:</span>';
                v.subVerifiers.forEach(function(sv) {
                    subHtml += '<span class="verifier-sub-chip" title="' + (sv.description || '') + '">' + sv.name + '</span>';
                });
                subHtml += '</div>';
            }
            listHtml += '<div class="verifier-card" id="verifier-card-' + idx + '">' +
                '<div class="verifier-card-header">' +
                    '<span class="verifier-card-name">' + v.name + '</span>' +
                    '<span class="verifier-card-type type-' + typeClass + '">' + v.type + '</span>' +
                '</div>' +
                '<p class="verifier-card-desc">' + v.description + '</p>' +
                scoringHtml +
                subHtml +
            '</div>';
        });
    } else {
        listHtml = '<p style="color:var(--text-secondary);font-size:0.9rem;">No verifiers configured for this environment category.</p>';
    }

    return '<div class="detail-collapsible" id="section-verifiers">' +
        '<button class="detail-collapsible-header" onclick="toggleDetailSection(\'section-verifiers\')">' +
            '<h2>' +
                '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>' +
                ' Verifiers <span style="font-size:0.75rem;font-weight:400;color:var(--text-secondary);margin-left:6px;">(' + filtered.length + ')</span>' +
            '</h2>' +
            '<svg class="detail-collapsible-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>' +
        '</button>' +
        '<div class="detail-collapsible-body" id="section-verifiers-body">' +
            '<div class="detail-collapsible-content">' +
                '<div class="verifiers-list">' + listHtml + '</div>' +
                '<div style="margin-top:1rem;">' +
                    '<button class="btn btn-outline btn-small" onclick="toggleAddVerifierForm()" id="btn-add-verifier">' +
                        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
                        ' Add Verifier' +
                    '</button>' +
                '</div>' +
                '<div id="add-verifier-form" style="display:none;margin-top:1rem;padding:1rem;background:var(--bg-tertiary);border-radius:8px;border:1px solid var(--border-color);">' +
                    '<h4 style="margin:0 0 0.75rem;font-size:0.9rem;color:var(--text-primary);">New Verifier (JSON)</h4>' +
                    '<textarea id="add-verifier-json" class="add-env-terraform-editor" rows="10" spellcheck="false" placeholder=\'{\n  "name": "My Verifier",\n  "type": "rule-based",\n  "description": "Describe the verifier...",\n  "logic": { "type": "custom_validator", "checks": {} },\n  "scoring": { "accuracy_weight": 0.5, "completeness_weight": 0.5 },\n  "failurePolicy": { "hard_fail": false, "penalty": -0.5 }\n}\'></textarea>' +
                    '<div style="margin-top:0.75rem;display:flex;gap:8px;">' +
                        '<button class="btn btn-primary btn-small" onclick="saveNewVerifier(\'' + envName.replace(/'/g, "\\'") + '\', \'' + envCategory + '\')">Save Verifier</button>' +
                        '<button class="btn btn-outline btn-small" onclick="toggleAddVerifierForm()">Cancel</button>' +
                    '</div>' +
                '</div>' +
            '</div>' +
        '</div>' +
    '</div>';
}

function toggleAddVerifierForm() {
    var form = document.getElementById('add-verifier-form');
    if (!form) return;
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}
window.toggleAddVerifierForm = toggleAddVerifierForm;

function saveNewVerifier(envName, envCategory) {
    var textarea = document.getElementById('add-verifier-json');
    if (!textarea) return;
    try {
        var data = JSON.parse(textarea.value);
        if (!data.name) { showToast('Verifier name is required.', 'error'); return; }
        var newVerifier = {
            id: 'v_custom_' + Date.now(),
            name: data.name,
            type: data.type || 'rule-based',
            system: 'Custom',
            environment: envCategory,
            version: 1,
            status: 'active',
            usedInScenarios: [],
            description: data.description || '',
            metadata: { type: data.type || 'rule-based', environment: envCategory },
            logic: data.logic || {},
            failurePolicy: data.failurePolicy || { hard_fail: false, penalty: -0.5, log_failure: true },
            subVerifiers: data.subVerifiers || []
        };
        if (window.VERIFIER_DATA && window.VERIFIER_DATA.all) {
            window.VERIFIER_DATA.all.push(newVerifier);
        }
        showToast('Verifier "' + newVerifier.name + '" added.', 'success');
        textarea.value = '';
        toggleAddVerifierForm();
        showEnvironmentDetails(envName);
    } catch (e) {
        showToast('Invalid JSON: ' + e.message, 'error');
    }
}
window.saveNewVerifier = saveNewVerifier;

// ─── Build Training Section for detail page ───
function getTrainingRunsForEnv(envCategory) {
    var cfg = window.TRAINING_CONFIG;
    if (!cfg || !cfg.trainingRuns) return [];
    return cfg.trainingRuns.filter(function(r) {
        return r.category === envCategory;
    });
}

function buildTrainingSection(envName, envCategory) {
    var runs = getTrainingRunsForEnv(envCategory);
    var encodedEnv = encodeURIComponent(envName);

    if (!runs.length) {
        // No runs → show collapsible with inline "New Training" button that opens config modal directly
        return '<div class="detail-collapsible" id="section-training">' +
            '<button class="detail-collapsible-header" onclick="toggleDetailSection(\'section-training\')">' +
                '<h2>' +
                    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c6 3 10 3 16 0v-5"/></svg>' +
                    ' Training' +
                '</h2>' +
                '<svg class="detail-collapsible-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>' +
            '</button>' +
            '<div class="detail-collapsible-body" id="section-training-body">' +
                '<div class="detail-collapsible-content">' +
                    '<div class="training-empty-state">' +
                        '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" stroke-width="1.5" style="opacity:0.4;margin-bottom:0.75rem;"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c6 3 10 3 16 0v-5"/></svg>' +
                        '<p style="color:var(--text-secondary);margin-bottom:1rem;font-size:0.9rem;">No training runs yet. Configure and start your first training run.</p>' +
                        '<button class="btn btn-primary" onclick="toggleTrainingInline(\'' + envName + '\')">' +
                            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
                            ' New Training' +
                        '</button>' +
                    '</div>' +
                    '<div id="training-inline-iframe-wrap" style="display:none;margin-top:1rem;">' +
                        '<iframe id="training-inline-iframe" style="width:100%;height:700px;border:none;border-radius:8px;" loading="lazy"></iframe>' +
                    '</div>' +
                '</div>' +
            '</div>' +
        '</div>';
    }

    // Has runs → build collapsible section with tabular run list
    var tableHtml = '<table class="train-runs-table"><thead><tr>' +
        '<th>Name</th><th>Status</th><th>Environment</th><th>Model</th><th>Progress</th><th>Started</th>' +
        '</tr></thead><tbody>';

    runs.forEach(function(r, idx) {
        var statusClass = r.status || 'pending';
        var statusLabel = statusClass.charAt(0).toUpperCase() + statusClass.slice(1);
        var runId = 'training-run-' + (r.id || idx);
        var pct = r.progress || 0;
        var envDisplay = r.environmentDisplay || r.environment || '\u2014';
        var model = r.model || '\u2014';
        var algo = r.algorithm || '';
        var desc = algo ? algo + ' training on ' + envDisplay.toLowerCase().replace(/\s+/g, '-') : '';

        // Store run data for popup rendering
        _trainingRunDataMap[runId] = r;

        tableHtml += '<tr onclick="toggleTrainingRun(\'' + runId + '\')" style="cursor:pointer;">' +
            '<td class="trt-name">' + (r.name || r.id) + (desc ? '<small>' + desc + '</small>' : '') + '</td>' +
            '<td><span class="trt-status ' + statusClass + '">' + statusLabel + '</span></td>' +
            '<td>' + envDisplay + '</td>' +
            '<td>' + model + '</td>' +
            '<td><div class="trt-progress"><div class="trt-bar"><div class="trt-bar-fill ' + statusClass + '" style="width:' + pct + '%"></div></div><span class="trt-pct">' + pct + '%</span></div></td>' +
            '<td>' + (r.started || '\u2014') + '</td>' +
        '</tr>';
    });

    tableHtml += '</tbody></table>';

    return '<div class="detail-collapsible" id="section-training">' +
        '<button class="detail-collapsible-header" onclick="toggleDetailSection(\'section-training\')">' +
            '<h2>' +
                '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c6 3 10 3 16 0v-5"/></svg>' +
                ' Training' +
            '</h2>' +
            '<svg class="detail-collapsible-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>' +
        '</button>' +
        '<div class="detail-collapsible-body" id="section-training-body">' +
            '<div class="detail-collapsible-content">' +
                '<div class="training-inline-header">' +
                    '<span class="training-inline-count">' + runs.length + ' run' + (runs.length !== 1 ? 's' : '') + '</span>' +
                    '<button class="btn btn-primary btn-small train-new-btn" onclick="toggleTrainingInline(\'' + envName + '\')">' +
                        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
                        ' New' +
                    '</button>' +
                '</div>' +
                tableHtml +
                '<div id="training-inline-iframe-wrap" style="display:none;margin-top:1rem;">' +
                    '<iframe id="training-inline-iframe" style="width:100%;height:700px;border:none;border-radius:8px;" loading="lazy"></iframe>' +
                '</div>' +
            '</div>' +
        '</div>' +
    '</div>';
}

// ─── Refresh the Training section in the env detail page after a new run is started ───
function _refreshTrainingSectionInDetail(envName, envCategory) {
    var sectionBody = document.getElementById('section-training-body');
    if (!sectionBody) return; // not on env detail page
    var section = document.getElementById('section-training');
    if (!section) return;
    // Re-build the entire training section HTML and replace
    var newHtml = buildTrainingSection(envName, envCategory);
    var temp = document.createElement('div');
    temp.innerHTML = newHtml;
    var newSection = temp.firstElementChild;
    if (newSection) {
        section.replaceWith(newSection);
        // Ensure the section is expanded so the user sees the new run
        var newBody = document.getElementById('section-training-body');
        if (newBody) newBody.style.display = 'block';
        var newChevron = newBody ? newBody.previousElementSibling.querySelector('.detail-collapsible-chevron') : null;
        if (newChevron) newChevron.style.transform = 'rotate(180deg)';
    }
}
window._refreshTrainingSectionInDetail = _refreshTrainingSectionInDetail;

// ─── Run data map for lazy inline report rendering ───
var _trainingRunDataMap = {};

// ─── Open training run report in a popup ───
function toggleTrainingRun(runId) {
    var run = _trainingRunDataMap[runId];
    if (!run) return;
    _openTrainingReportPopup(run);
}
window.toggleTrainingRun = toggleTrainingRun;

// ─── Training report popup ───
var _trainingReportOverlay = null;

function _openTrainingReportPopup(run) {
    if (!_trainingReportOverlay) {
        _trainingReportOverlay = document.createElement('div');
        _trainingReportOverlay.className = 'detail-popup-overlay training-report-popup';
        _trainingReportOverlay.id = 'training-report-popup-overlay';
        _trainingReportOverlay.onclick = function(e) {
            if (e.target === _trainingReportOverlay) _closeTrainingReportPopup();
        };
        _trainingReportOverlay.innerHTML =
            '<div class="detail-popup-box" onclick="event.stopPropagation()">' +
                '<div class="detail-popup-header">' +
                    '<h3 id="training-report-popup-title"></h3>' +
                    '<button class="detail-popup-close" onclick="_closeTrainingReportPopup()" aria-label="Close">&times;</button>' +
                '</div>' +
                '<div class="detail-popup-body training-report-popup-body" id="training-report-popup-body"></div>' +
            '</div>';
        document.body.appendChild(_trainingReportOverlay);
    }

    var titleEl = document.getElementById('training-report-popup-title');
    var bodyEl = document.getElementById('training-report-popup-body');

    var algo = run.algorithm || '\u2014';
    var name = run.name || run.id || 'Training Run';
    titleEl.innerHTML = '<span class="train-run-algo">' + algo + '</span> ' + name;
    bodyEl.innerHTML = _buildInlineReport(run);

    _trainingReportOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';

    // Render canvas charts after DOM insertion (deferred so canvas has dimensions)
    requestAnimationFrame(function() {
        var progressCanvas = bodyEl.querySelector('.ir-chart-progress');
        var failureCanvas = bodyEl.querySelector('.ir-chart-failures');
        if (progressCanvas) _renderPopupProgressChart(progressCanvas, run);
        if (failureCanvas) _renderPopupFailureChart(failureCanvas, run);
    });
}
window._openTrainingReportPopup = _openTrainingReportPopup;

function _closeTrainingReportPopup() {
    if (_trainingReportOverlay) {
        _trainingReportOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }
}
window._closeTrainingReportPopup = _closeTrainingReportPopup;

// ─── Inline report builder — renders full training report within the env card ───
function _buildInlineReport(run) {
    var results = run.results || {};
    var baseline = run.baseline_results || {};
    var statusClass = run.status || 'pending';
    var reward = (run.avgReward != null) ? run.avgReward.toFixed(2) : '\u2014';
    var episodes = (run.episodes != null) ? run.episodes : '\u2014';
    var model = run.model || '\u2014';
    var started = run.started || '\u2014';
    var completed = run.completed || '\u2014';
    var successRate = (run.successRate != null) ? run.successRate + '%' : '\u2014';
    var pct = run.progress || 0;
    var maxReward = (results.max_reward != null) ? results.max_reward.toFixed(2) : '\u2014';
    var minReward = (results.min_reward != null) ? results.min_reward.toFixed(2) : '\u2014';
    var baselineMean = (baseline.mean_reward != null) ? baseline.mean_reward.toFixed(2) : null;
    var improvementPct = (run.avgReward != null && baseline.mean_reward != null)
        ? '+' + ((run.avgReward - baseline.mean_reward) * 100).toFixed(0) + '%' : null;

    var html = '';

    // Progress bar (running only)
    if (statusClass === 'running') {
        html += '<div class="train-run-progress"><div class="train-run-progress-bar" style="width:' + pct + '%"></div></div>';
    }

    // ── 1. Progress Stepper ──
    html += _buildInlineStepper(run);

    // ── 2. Metric Cards ──
    html += '<div class="train-run-metrics">' +
        _metricCard('Episodes', episodes) +
        _metricCard('Success Rate', successRate) +
        _metricCard('Avg Reward', reward) +
        _metricCard('Improvement', improvementPct || '\u2014', true) +
    '</div>';

    // ── 3. Info Panels — Training Info + Model Config side by side ──
    html += '<div class="ir-panels">';
    html += '<div class="ir-panel">' +
        '<h4>Training Information</h4>' +
        _infoRow('Environment', run.environmentDisplay || run.environment) +
        _infoRow('Algorithm', run.algorithm || '\u2014') +
        _infoRow('Status', statusClass.charAt(0).toUpperCase() + statusClass.slice(1)) +
        _infoRow('Started', started) +
        (completed !== '\u2014' ? _infoRow('Completed', completed) : '') +
        _infoRow('Progress', pct + '%') +
    '</div>';
    html += '<div class="ir-panel">' +
        '<h4>Model &amp; Compute</h4>' +
        _infoRow('Base Model', model) +
        _infoRow('LoRA r', '32') +
        _infoRow('LoRA alpha', '16') +
        _infoRow('Dropout', '0.05') +
        _infoRow('Task Type', 'CAUSAL_LM') +
    '</div>';
    html += '</div>';

    // ── 4. Results + Baseline side by side ──
    if (results.mean_reward != null || baseline.mean_reward != null) {
        html += '<div class="ir-panels">';
        if (results.mean_reward != null) {
            html += '<div class="ir-panel">' +
                '<h4>Results</h4>' +
                _infoRow('Mean Reward', results.mean_reward.toFixed(4)) +
                _infoRow('Max Reward', maxReward) +
                _infoRow('Min Reward', minReward) +
            '</div>';
        }
        if (baseline.mean_reward != null) {
            html += '<div class="ir-panel">' +
                '<h4>Baseline</h4>' +
                _infoRow('Mean Reward', baseline.mean_reward.toFixed(4)) +
                (baseline.max_reward != null ? _infoRow('Max Reward', baseline.max_reward.toFixed(4)) : '') +
                _infoRow('Episodes', baseline.episodes || '\u2014') +
            '</div>';
        }
        html += '</div>';
    }

    // ── 5. Rollout Comparison ──
    if ((run.status === 'completed' || run.status === 'awaiting_human_eval') &&
        (run._mock_baseline_rollout || run._mock_trained_rollout)) {
        html += _buildInlineRolloutComparison(run);
    }

    // ── 5b. State Diagram ──
    if ((run.status === 'completed' || run.status === 'awaiting_human_eval') &&
        (run._mock_trained_rollout || run._mock_baseline_rollout)) {
        html += _buildPopupStateDiagram(run);
    }

    // ── 5c. Charts (Training Progress + Failure Modes) ──
    if (run.status === 'completed' || run.status === 'running') {
        html += '<div class="ir-panels">' +
            '<div class="ir-panel"><h4>Training Progress</h4><canvas class="ir-chart-progress" style="width:100%;height:220px;"></canvas></div>' +
            '<div class="ir-panel"><h4>Failure Modes</h4><canvas class="ir-chart-failures" style="width:100%;height:220px;"></canvas></div>' +
        '</div>';
    }

    // ── 6. Performance + Efficiency ──
    if (run.status === 'completed') {
        html += '<div class="ir-panels">';
        html += '<div class="ir-panel">' +
            '<h4>Performance Improvement</h4>' +
            _perfRow('Task Completion', '23%', successRate, run.successRate != null ? '+' + (run.successRate - 23).toFixed(0) + '%' : '') +
            _perfRow('Avg Steps', '12.4', run._mock_trained_rollout ? String(run._mock_trained_rollout.total_steps) : '7.1', run._mock_trained_rollout ? '-' + Math.round((1 - run._mock_trained_rollout.total_steps / 12.4) * 100) + '%' : '-43%') +
            _perfRow('Error Rate', '31%', '8.2%', '-74%') +
        '</div>';
        html += '<div class="ir-panel">' +
            '<h4>Efficiency Gains</h4>' +
            _perfRow('Tokens per Episode', '1,240', '890', '-28%') +
            _perfRow('Avg Latency', '3.2s', '2.1s', '-34%') +
            _perfRow('Tool Calls per Task', '8.5', run._mock_trained_rollout ? String(run._mock_trained_rollout.total_steps) : '5.2', run._mock_trained_rollout ? '-' + Math.round((1 - run._mock_trained_rollout.total_steps / 8.5) * 100) + '%' : '-39%') +
        '</div>';
        html += '</div>';

        // Trade-off note
        html += '<div class="ir-tradeoff"><strong>Trade-off Note:</strong> While overall success rate improved significantly, the model shows slightly higher latency on multi-step workflows. Consider fine-tuning with trajectory-focused verifiers for complex scenarios.</div>';
    }

    // ── 7. Model Artifact + Download ──
    if (run.status === 'completed' && (run.model_url || run.model_saved)) {
        html += '<div class="ir-panel ir-artifact">' +
            '<h4>Model Artifact</h4>' +
            _infoRow('Status', run.model_saved ? 'Saved' : 'Pending') +
            _infoRow('Format', 'stable-baselines3 (.zip)') +
            _infoRow('Algorithm', run.algorithm || '\u2014') +
            _infoRow('Base Model', model) +
            (run.model_url ? '<a class="train-run-download" href="' + run.model_url + '" style="margin-top:0.5rem;display:inline-flex">' +
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' +
                ' Download Model</a>' : '') +
        '</div>';
    }

    return html;
}

function _buildInlineStepper(run) {
    var steps = ['Configuration', 'Baseline Eval', 'Training', 'Evaluation', 'Complete'];
    var statusMap = {
        'pending': 0, 'configuring': 0,
        'running': 2, 'training': 2,
        'evaluating': 3,
        'completed': 5, 'failed': -1,
        'awaiting_human_eval': 4
    };
    var active = statusMap[run.status] != null ? statusMap[run.status] : 0;
    var html = '<div class="ir-stepper">';
    for (var i = 0; i < steps.length; i++) {
        var cls = (i < active) ? 'done' : (i === active && run.status !== 'failed') ? 'active' : '';
        html += '<div class="ir-stepper-step ' + cls + '">' +
            '<div class="ir-stepper-circle">' + (cls === 'done' ? '\u2713' : (i + 1)) + '</div>' +
            '<span>' + steps[i] + '</span>' +
        '</div>';
        if (i < steps.length - 1) {
            html += '<div class="ir-stepper-line ' + (i < active ? 'done' : '') + '"></div>';
        }
    }
    html += '</div>';
    return html;
}

function _metricCard(label, value, highlight) {
    return '<div class="train-run-metric' + (highlight ? ' highlight' : '') + '"><label>' + label + '</label><span>' + value + '</span></div>';
}

function _infoRow(label, value) {
    return '<div class="ir-info-row"><span class="ir-info-label">' + label + '</span><span class="ir-info-value">' + value + '</span></div>';
}

function _perfRow(label, before, after, delta) {
    var cls = delta && delta.charAt(0) === '+' ? 'positive' : 'negative';
    return '<div class="ir-perf-row">' +
        '<span class="ir-perf-label">' + label + '</span>' +
        '<span class="ir-perf-before">' + before + '</span>' +
        '<span class="ir-perf-arrow">\u2192</span>' +
        '<strong>' + after + '</strong>' +
        '<span class="ir-perf-delta ' + cls + '">' + delta + '</span>' +
    '</div>';
}

function _buildInlineRolloutComparison(run) {
    var bl = run._mock_baseline_rollout;
    var tr = run._mock_trained_rollout;
    if (!bl && !tr) return '';

    var html = '<div class="ir-rollout-section">' +
        '<h4>Rollout Comparison</h4>' +
        '<div class="ir-rollout-meta">' +
            '<span>Scenario: <strong>' + ((bl || tr).scenario_name || '\u2014') + '</strong></span>' +
        '</div>' +
        '<div class="ir-rollout-panels">';

    if (bl) html += _buildRolloutPanel('Pre-trained Policy (Baseline)', bl);
    if (tr) html += _buildRolloutPanel('Trained Policy (' + (run.algorithm || 'RL') + ')', tr);

    html += '</div></div>';
    return html;
}

function _buildRolloutPanel(title, rollout) {
    var html = '<div class="ir-rollout-panel">' +
        '<h5>' + title + '</h5>' +
        '<div class="ir-rollout-header">' +
            '<span>Policy: <strong>' + (rollout.policy_name || '\u2014') + '</strong></span>' +
            '<span>Checkpoint: <code>' + (rollout.checkpoint_label || '\u2014') + '</code></span>' +
            '<span>Reward: <strong>' + (rollout.total_reward != null ? rollout.total_reward.toFixed(2) : '\u2014') + '</strong></span>' +
        '</div>';

    // Timeline events
    html += '<div class="ir-rollout-timeline">';
    (rollout.steps || []).forEach(function(step) {
        (step.timeline_events || []).forEach(function(ev) {
            var ts = (ev.timestamp_ms / 1000).toFixed(3) + 's';
            var evClass = (ev.event_type || '').toLowerCase().replace(/_/g, '-');
            var content = ev.content || '';
            if (ev.tool_name) {
                content = ev.tool_name + '(' + JSON.stringify(ev.tool_args || {}) + ')';
            }
            html += '<div class="ir-timeline-event ' + evClass + '">' +
                '<span class="ir-ts">[ ' + ts + ' ]</span>' +
                '<span class="ir-ev-type">' + (ev.event_type || '') + '</span>' +
                '<span class="ir-ev-content">' + content + '</span>' +
            '</div>';
        });
    });
    html += '</div>';

    // Final state
    if (rollout.final_environment_state) {
        html += '<div class="ir-rollout-final"><h6>Final state</h6><pre>' +
            Object.keys(rollout.final_environment_state).map(function(k) {
                return '  ' + k + ': ' + JSON.stringify(rollout.final_environment_state[k]);
            }).join('\n') +
        '</pre></div>';
    }

    // Verifier results
    if (rollout.verifier_results && rollout.verifier_results.length) {
        html += '<div class="ir-rollout-verifiers"><h6>Verifier results</h6>';
        rollout.verifier_results.forEach(function(v) {
            html += '<div class="ir-verifier ' + (v.passed ? 'pass' : 'fail') + '">' +
                '<span>' + (v.passed ? '\u2713' : '\u2717') + '</span> ' +
                (v.check || v.name || '') +
            '</div>';
        });
        html += '</div>';
    }

    html += '</div>';
    return html;
}

// ─── State Diagram builder for popup ─────────────────────────────────────
function _buildPopupStateDiagram(run) {
    var rollout = run._mock_trained_rollout || run._mock_baseline_rollout || null;
    if (!rollout || !rollout.steps || !rollout.steps.length) return '';

    var NW = 158, NH = 38, BR = 6, PAD = 30, HGAP = 62, VGAP = 52, STACK_GAP = 10;
    var CLR = {
        user:{bg:'#eff6ff',bdr:'#93c5fd',tx:'#1e40af'}, agent:{bg:'#f0fdf4',bdr:'#86efac',tx:'#166534'},
        tool:{bg:'#fefce8',bdr:'#fde68a',tx:'#92400e'}, final:{bg:'#f1f5f9',bdr:'#cbd5e1',tx:'#475569'},
        vPass:{bg:'#f0fdf4',bdr:'#86efac',tx:'#166534'}, vFail:{bg:'#fdf2f8',bdr:'#f9a8d4',tx:'#9d174d'},
        reward:{bg:'#faf5ff',bdr:'#e9d5ff',tx:'#7c3aed'}
    };
    function trunc(s,m){return !s?'':s.length>m?s.slice(0,m-1)+'\u2026':s;}
    function esvg(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

    var gNodes=[], gEdges=[], nMap={};
    function addN(id,kind,label,detail,x,y){var n={id:id,kind:kind,label:label,detail:detail||'',x:x,y:y,w:NW,h:NH};gNodes.push(n);nMap[id]=n;return n;}
    var col=0;
    var s0=rollout.steps[0], uDet='';
    if(s0&&s0.timeline_events){for(var q=0;q<s0.timeline_events.length;q++){if(s0.timeline_events[q].event_type==='SYSTEM'){uDet=s0.timeline_events[q].content||'';break;}}}
    addN('u0','user','User Request',trunc(uDet,26),PAD+col*(NW+HGAP),PAD); col++;

    for(var i=0;i<rollout.steps.length;i++){
        var step=rollout.steps[i], cx=PAD+col*(NW+HGAP);
        addN('a'+i,'agent','Agent (Trained)','Step '+step.step,cx,PAD);
        gEdges.push({f:(i===0?'u0':'a'+(i-1)),t:'a'+i,ty:'solid'});
        var evts=step.timeline_events||[], ti=0;
        for(var j=0;j<evts.length;j++){
            if(evts[j].event_type==='TOOL_CALL'){
                var tName=evts[j].tool_name||'Tool', tArgs='';
                if(evts[j].tool_args){try{tArgs=JSON.stringify(evts[j].tool_args);}catch(e){}}
                var tid='t'+i+'_'+ti, ty=PAD+NH+VGAP+ti*(NH+STACK_GAP);
                addN(tid,'tool',trunc(tName,22),trunc(tArgs,26),cx,ty);
                gEdges.push({f:(ti===0?'a'+i:'t'+i+'_'+(ti-1)),t:tid,ty:'dashed-blue'}); ti++;
            }
        }
        if(step.reward!=null){
            var rid='r'+i, ry=PAD+NH+VGAP+ti*(NH+STACK_GAP);
            addN(rid,'reward','Reward  +'+step.reward.toFixed(2),'',cx,ry);
            gEdges.push({f:(ti>0?'t'+i+'_'+(ti-1):'a'+i),t:rid,ty:'dashed-blue'}); ti++;
        }
        col++;
    }

    var fs=rollout.final_environment_state||{}, fsParts=[];
    for(var fk in fs){if(fs.hasOwnProperty(fk))fsParts.push(fk.replace(/_/g,' ')+': '+fs[fk]);}
    var fx=PAD+col*(NW+HGAP);
    addN('fin','final','Final State',trunc(fsParts.join(', '),26),fx,PAD);
    gEdges.push({f:'a'+(rollout.steps.length-1),t:'fin',ty:'solid'});

    var vrs=rollout.verifier_results||[];
    for(var v=0;v<vrs.length;v++){
        var vr=vrs[v], vKind=vr.passed?'vPass':'vFail', vid='v'+v;
        var vy=PAD+NH+VGAP+v*(NH+STACK_GAP);
        addN(vid,vKind,(vr.passed?'\u2713 ':'\u2717 ')+trunc(vr.check,19),trunc(vr.detail,26),fx,vy);
        gEdges.push({f:'fin',t:vid,ty:'dashed-red'});
    }

    var maxX=0,maxY=0;
    for(var ni=0;ni<gNodes.length;ni++){var nd=gNodes[ni];if(nd.x+nd.w>maxX)maxX=nd.x+nd.w;if(nd.y+nd.h>maxY)maxY=nd.y+nd.h;}
    var svgW=maxX+PAD, svgH=maxY+PAD;

    var svg='<svg xmlns="http://www.w3.org/2000/svg" width="'+svgW+'" height="'+svgH+'" viewBox="0 0 '+svgW+' '+svgH+'" style="font-family:Inter,system-ui,-apple-system,sans-serif;">';
    svg+='<defs>';
    svg+='<marker id="sd-a-s" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0,0L8,3L0,6Z" fill="#64748b"/></marker>';
    svg+='<marker id="sd-a-b" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0,0L8,3L0,6Z" fill="#3b82f6"/></marker>';
    svg+='<marker id="sd-a-r" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0,0L8,3L0,6Z" fill="#f43f5e"/></marker>';
    svg+='<filter id="sd-sh" x="-4%" y="-8%" width="108%" height="120%"><feDropShadow dx="0" dy="1" stdDeviation="2" flood-opacity="0.06"/></filter>';
    svg+='</defs>';

    for(var ei=0;ei<gEdges.length;ei++){
        var ge=gEdges[ei], fn=nMap[ge.f], tn=nMap[ge.t];
        if(!fn||!tn)continue;
        var marker=ge.ty==='dashed-red'?'sd-a-r':(ge.ty==='dashed-blue'?'sd-a-b':'sd-a-s');
        var eCol=ge.ty==='dashed-red'?'#f43f5e':(ge.ty==='dashed-blue'?'#3b82f6':'#64748b');
        var eW=ge.ty==='solid'?1.5:1.2;
        var dash=ge.ty==='solid'?'':' stroke-dasharray="6,3"';
        var horiz=Math.abs(fn.y-tn.y)<5, sameCol=Math.abs(fn.x-tn.x)<5, pth;
        if(horiz){pth='M'+(fn.x+fn.w)+','+(fn.y+fn.h/2)+' L'+tn.x+','+(tn.y+tn.h/2);}
        else if(sameCol){pth='M'+(fn.x+fn.w/2)+','+(fn.y+fn.h)+' L'+(tn.x+tn.w/2)+','+tn.y;}
        else{var sx=fn.x+fn.w/2,sy=fn.y+fn.h,ex=tn.x+tn.w/2,ey=tn.y,my=(sy+ey)/2;pth='M'+sx+','+sy+' C'+sx+','+my+' '+ex+','+my+' '+ex+','+ey;}
        svg+='<path d="'+pth+'" fill="none" stroke="'+eCol+'" stroke-width="'+eW+'"'+dash+' marker-end="url(#'+marker+')"/>';
    }

    for(var ni2=0;ni2<gNodes.length;ni2++){
        var n=gNodes[ni2], c=CLR[n.kind]||CLR.agent;
        svg+='<g filter="url(#sd-sh)">';
        svg+='<rect x="'+n.x+'" y="'+n.y+'" width="'+n.w+'" height="'+n.h+'" rx="'+BR+'" fill="'+c.bg+'" stroke="'+c.bdr+'" stroke-width="1.5"/>';
        if(n.detail){
            svg+='<text x="'+(n.x+10)+'" y="'+(n.y+15)+'" font-size="11" font-weight="600" fill="'+c.tx+'">'+esvg(n.label)+'</text>';
            svg+='<text x="'+(n.x+10)+'" y="'+(n.y+28)+'" font-size="9" fill="#64748b">'+esvg(n.detail)+'</text>';
        }else{
            svg+='<text x="'+(n.x+10)+'" y="'+(n.y+n.h/2+4)+'" font-size="11" font-weight="600" fill="'+c.tx+'">'+esvg(n.label)+'</text>';
        }
        svg+='<title>'+esvg(n.label+(n.detail?': '+n.detail:''))+'</title></g>';
    }
    svg+='</svg>';

    var out='<div class="sd-container" style="margin-top:0.75rem;">';
    out+='<h4 class="sd-title" style="font-size:0.85rem;">Rollout State Diagram</h4>';
    out+='<p class="sd-subtitle">'+((rollout.scenario_name||rollout.environment_name||'')+' \u00b7 Policy: '+(rollout.policy_name||'\u2014')+' \u00b7 '+rollout.total_steps+' steps \u00b7 Reward: '+(rollout.total_reward!=null?rollout.total_reward.toFixed(2):'\u2014'))+'</p>';
    out+='<div class="sd-scroll">'+svg+'</div>';
    out+='<div class="sd-legend">';
    out+='<span class="sd-legend-item"><span class="sd-legend-dot" style="background:#93c5fd"></span> User</span>';
    out+='<span class="sd-legend-item"><span class="sd-legend-dot" style="background:#86efac"></span> Agent</span>';
    out+='<span class="sd-legend-item"><span class="sd-legend-dot" style="background:#fde68a"></span> Tool Call</span>';
    out+='<span class="sd-legend-item"><span class="sd-legend-dot" style="background:#cbd5e1"></span> Final State</span>';
    out+='<span class="sd-legend-item"><span class="sd-legend-dot" style="background:#e9d5ff"></span> Reward</span>';
    out+='<span class="sd-legend-item"><span class="sd-legend-line" style="color:#64748b"></span> Flow</span>';
    out+='<span class="sd-legend-item"><span class="sd-legend-line dashed" style="color:#3b82f6"></span> Tool</span>';
    out+='<span class="sd-legend-item"><span class="sd-legend-line dashed" style="color:#f43f5e"></span> Verify</span>';
    out+='</div></div>';
    return out;
}

// ─── Chart rendering for popup ───────────────────────────────────────────
function _popupSeededRandom(seed) {
    var s = seed;
    return function() { s = (s * 16807 + 0) % 2147483647; return (s - 1) / 2147483646; };
}

function _renderPopupProgressChart(canvas, run) {
    if (!canvas || !canvas.getContext) return;
    var ctx = canvas.getContext('2d');
    var dpr = window.devicePixelRatio || 1;
    var rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr; canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    var w = rect.width, h = rect.height;
    ctx.clearRect(0, 0, w, h);

    var pad = { top: 20, right: 20, bottom: 35, left: 50 };
    var plotW = w - pad.left - pad.right, plotH = h - pad.top - pad.bottom;
    var targetReward = run.avgReward || 0.63, baselineReward = run.baselineReward || 0.22;
    var totalEpisodes = run.episodes || 320, numPoints = 40;
    var rng = _popupSeededRandom(42 + Math.round(targetReward * 1000));

    var pts = [];
    for (var i = 0; i <= numPoints; i++) {
        var t = i / numPoints;
        var base = baselineReward + (targetReward - baselineReward) * (1 - Math.exp(-4 * t));
        var noise = (rng() - 0.5) * 0.04 * (1 - t * 0.6);
        pts.push(Math.max(0, Math.min(1, base + noise)));
    }
    var smoothed = [];
    for (var i = 0; i < pts.length; i++) {
        var sum = 0, cnt = 0;
        for (var j = Math.max(0, i - 2); j <= Math.min(pts.length - 1, i + 2); j++) { sum += pts[j]; cnt++; }
        smoothed.push(sum / cnt);
    }

    var yMin = 0, yMax = 1.0, yRange = yMax - yMin;
    ctx.strokeStyle = '#f0f0f0'; ctx.lineWidth = 1;
    [0, 0.2, 0.4, 0.6, 0.8, 1.0].forEach(function(v) {
        var y = pad.top + plotH - ((v - yMin) / yRange) * plotH;
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(pad.left + plotW, y); ctx.stroke();
    });
    ctx.strokeStyle = '#d1d5db'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(pad.left, pad.top); ctx.lineTo(pad.left, pad.top + plotH); ctx.lineTo(pad.left + plotW, pad.top + plotH); ctx.stroke();
    ctx.fillStyle = '#6b7280'; ctx.font = '11px -apple-system,BlinkMacSystemFont,sans-serif'; ctx.textAlign = 'right';
    [0, 0.2, 0.4, 0.6, 0.8, 1.0].forEach(function(v) { ctx.fillText(v.toFixed(1), pad.left - 6, pad.top + plotH - ((v - yMin) / yRange) * plotH + 4); });
    ctx.textAlign = 'center';
    for (var i = 0; i <= 5; i++) { ctx.fillText(Math.round((i / 5) * totalEpisodes), pad.left + (i / 5) * plotW, pad.top + plotH + 16); }
    ctx.fillStyle = '#9ca3af'; ctx.textAlign = 'center'; ctx.fillText('Episodes', pad.left + plotW / 2, h - 4);
    ctx.save(); ctx.translate(13, pad.top + plotH / 2); ctx.rotate(-Math.PI / 2); ctx.fillText('Mean Reward', 0, 0); ctx.restore();

    var grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + plotH);
    grad.addColorStop(0, 'rgba(192,38,211,0.15)'); grad.addColorStop(1, 'rgba(192,38,211,0.02)');
    ctx.fillStyle = grad; ctx.beginPath(); ctx.moveTo(pad.left, pad.top + plotH);
    smoothed.forEach(function(v, idx) { ctx.lineTo(pad.left + (idx / numPoints) * plotW, pad.top + plotH - ((v - yMin) / yRange) * plotH); });
    ctx.lineTo(pad.left + plotW, pad.top + plotH); ctx.closePath(); ctx.fill();

    ctx.strokeStyle = '#c026d3'; ctx.lineWidth = 2.5; ctx.lineJoin = 'round'; ctx.lineCap = 'round'; ctx.beginPath();
    smoothed.forEach(function(v, idx) { var x = pad.left + (idx / numPoints) * plotW, y = pad.top + plotH - ((v - yMin) / yRange) * plotH; if (idx === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); });
    ctx.stroke();

    var baseY = pad.top + plotH - ((baselineReward - yMin) / yRange) * plotH;
    ctx.strokeStyle = '#9ca3af'; ctx.setLineDash([6, 4]); ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(pad.left, baseY); ctx.lineTo(pad.left + plotW, baseY); ctx.stroke(); ctx.setLineDash([]);

    ctx.font = '11px -apple-system,BlinkMacSystemFont,sans-serif';
    var lx = pad.left + plotW - 120, ly = pad.top + 8;
    ctx.strokeStyle = '#c026d3'; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(lx, ly); ctx.lineTo(lx + 20, ly); ctx.stroke();
    ctx.fillStyle = '#374151'; ctx.textAlign = 'left'; ctx.fillText('Trained', lx + 25, ly + 4);
    ctx.strokeStyle = '#9ca3af'; ctx.setLineDash([6, 4]); ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(lx, ly + 18); ctx.lineTo(lx + 20, ly + 18); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = '#9ca3af'; ctx.fillText('Baseline', lx + 25, ly + 22);
}

function _popupRoundRect(ctx, x, y, w, h, r) {
    ctx.beginPath(); ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r); ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h); ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r); ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath();
}

function _popupLighten(hex, factor) {
    var r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16);
    r = Math.min(255, Math.round(r + (255 - r) * factor)); g = Math.min(255, Math.round(g + (255 - g) * factor)); b = Math.min(255, Math.round(b + (255 - b) * factor));
    return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

function _renderPopupFailureChart(canvas, run) {
    if (!canvas || !canvas.getContext) return;
    var ctx = canvas.getContext('2d');
    var dpr = window.devicePixelRatio || 1;
    var rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr; canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    var w = rect.width, h = rect.height;
    ctx.clearRect(0, 0, w, h);

    var modes = [
        { label: 'Wrong transition', pct: 35, color: '#c026d3' },
        { label: 'Timeout', pct: 25, color: '#7c3aed' },
        { label: 'Missing comment', pct: 20, color: '#3b82f6' },
        { label: 'Invalid status', pct: 12, color: '#06b6d4' },
        { label: 'Other', pct: 8, color: '#9ca3af' }
    ];
    var mpad = { top: 15, right: 50, bottom: 10, left: 115 };
    var plotW = w - mpad.left - mpad.right;
    var barH = Math.min(28, (h - mpad.top - mpad.bottom - (modes.length - 1) * 10) / modes.length);
    var gap = Math.min(12, (h - mpad.top - mpad.bottom - modes.length * barH) / (modes.length - 1));
    var totalH = modes.length * barH + (modes.length - 1) * gap;
    var startY = mpad.top + (h - mpad.top - mpad.bottom - totalH) / 2;

    modes.forEach(function(m, i) {
        var y = startY + i * (barH + gap), bw = (m.pct / 100) * plotW, radius = 4;
        ctx.fillStyle = '#f3f4f6'; _popupRoundRect(ctx, mpad.left, y, plotW, barH, radius); ctx.fill();
        if (bw > 0) {
            var barGrad = ctx.createLinearGradient(mpad.left, y, mpad.left + bw, y);
            barGrad.addColorStop(0, m.color); barGrad.addColorStop(1, _popupLighten(m.color, 0.2));
            ctx.fillStyle = barGrad; _popupRoundRect(ctx, mpad.left, y, Math.max(bw, radius * 2), barH, radius); ctx.fill();
        }
        ctx.fillStyle = '#374151'; ctx.font = '12px -apple-system,BlinkMacSystemFont,sans-serif';
        ctx.textAlign = 'right'; ctx.textBaseline = 'middle'; ctx.fillText(m.label, mpad.left - 10, y + barH / 2);
        ctx.fillStyle = '#6b7280'; ctx.textAlign = 'left'; ctx.fillText(m.pct + '%', mpad.left + bw + 8, y + barH / 2);
    });
    ctx.textBaseline = 'alphabetic';
}

// ─── Configuration Editor Section Builder ───────────────────────────────────
function buildConfigEditorSection(envName, details) {
    var schema = details.configSchema;
    var config = details.configTemplate;
    // Only show config section for envs that have configSchema (custom envs always do)
    if (!schema || !config) return '';

    // Build config parameter fields
    var fieldsHtml = '';
    var fieldKeys = Object.keys(schema);
    for (var i = 0; i < fieldKeys.length; i++) {
        var key = fieldKeys[i];
        var field = schema[key];
        var value = config[key] !== undefined ? config[key] : (field.default || '');
        var fieldHtml = '';

        if (field.type === 'select') {
            var optionsHtml = (field.options || []).map(function(opt) {
                var sel = (String(value) === String(opt)) ? ' selected' : '';
                var display = opt.replace(/_/g, ' ').replace(/\b\w/g, function(l) { return l.toUpperCase(); });
                return '<option value="' + opt + '"' + sel + '>' + display + '</option>';
            }).join('');
            fieldHtml = '<select class="config-editor-input" data-config-key="' + key + '" data-env="' + envName + '">' + optionsHtml + '</select>';
        } else if (field.type === 'range') {
            fieldHtml =
                '<div class="config-range-wrap">' +
                    '<input type="range" class="config-editor-input config-range-input" data-config-key="' + key + '" data-env="' + envName + '" ' +
                        'min="' + (field.min || 0) + '" max="' + (field.max || 100) + '" value="' + value + '" ' +
                        'oninput="this.nextElementSibling.textContent=this.value">' +
                    '<span class="config-range-value">' + value + '</span>' +
                '</div>';
        } else {
            // number or text
            var typeAttr = field.type === 'number' ? 'number' : 'text';
            var minMax = '';
            if (field.min !== undefined) minMax += ' min="' + field.min + '"';
            if (field.max !== undefined) minMax += ' max="' + field.max + '"';
            fieldHtml = '<input type="' + typeAttr + '" class="config-editor-input" data-config-key="' + key + '" data-env="' + envName + '" value="' + value + '"' + minMax + '>';
        }

        fieldsHtml +=
            '<div class="config-editor-field">' +
                '<label>' + (field.label || key) + '</label>' +
                fieldHtml +
            '</div>';
    }

    // Build KPI chips editor
    var kpis = details.kpis || [];
    var kpiChipsHtml = kpis.map(function(kpi, idx) {
        return '<span class="kpi-chip-editable" data-idx="' + idx + '">' +
            kpi +
            '<button class="kpi-remove-btn" onclick="removeCustomKpi(\'' + envName + '\', ' + idx + ')" title="Remove KPI">&times;</button>' +
        '</span>';
    }).join('');

    // Build infrastructure summary
    var sdk = details.sdk || 'gradio';
    var hardware = details.hardware || 'cpu-basic';
    var sdkDef = details.sdkDefaults || SDK_TRAINING_DEFAULTS[sdk] || {};
    var hwDef = details.hardwareDefaults || HARDWARE_TRAINING_DEFAULTS[hardware] || {};
    var sdkLabel = sdk.charAt(0).toUpperCase() + sdk.slice(1);
    var hwLabel = hardware.replace(/-/g, ' ').replace(/\b\w/g, function(l) { return l.toUpperCase(); });

    return '<div class="detail-collapsible" id="section-configuration">' +
        '<button class="detail-collapsible-header" onclick="toggleDetailSection(\'section-configuration\')">' +
            '<h2>' +
                '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>' +
                ' Configuration' +
            '</h2>' +
            '<svg class="detail-collapsible-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>' +
        '</button>' +
        '<div class="detail-collapsible-body" id="section-configuration-body">' +
            '<div class="detail-collapsible-content">' +
                // Config parameters grid
                '<h3 style="margin-bottom:0.75rem;font-size:0.95rem;">Environment Parameters</h3>' +
                '<div class="config-editor-grid">' + fieldsHtml + '</div>' +

                // KPI editor
                '<h3 style="margin-top:1.25rem;margin-bottom:0.75rem;font-size:0.95rem;">KPIs</h3>' +
                '<div class="kpi-chips-editor" id="kpi-chips-editor-' + envName + '">' +
                    kpiChipsHtml +
                    '<div class="kpi-add-row">' +
                        '<input type="text" class="config-editor-input kpi-add-input" id="kpi-add-input-' + envName + '" placeholder="Add KPI..." onkeydown="if(event.key===\'Enter\'){addCustomKpi(\'' + envName + '\');event.preventDefault();}">' +
                        '<button class="btn btn-small kpi-add-btn" onclick="addCustomKpi(\'' + envName + '\')">+</button>' +
                    '</div>' +
                '</div>' +

                // Infrastructure summary
                '<h3 style="margin-top:1.25rem;margin-bottom:0.75rem;font-size:0.95rem;">Infrastructure</h3>' +
                '<div class="config-infra-row">' +
                    '<div class="config-infra-item"><label>SDK</label><span>' + sdkLabel + '</span></div>' +
                    '<div class="config-infra-item"><label>Framework</label><span>' + (sdkDef.framework || 'N/A') + '</span></div>' +
                    '<div class="config-infra-item"><label>Hardware</label><span>' + hwLabel + '</span></div>' +
                    '<div class="config-infra-item"><label>Batch Size</label><span>' + (hwDef.batchSize || 64) + '</span></div>' +
                '</div>' +

                // Save / Reset buttons
                '<div class="config-editor-actions">' +
                    '<button class="btn btn-primary btn-small" onclick="saveEnvConfig(\'' + envName + '\')">Save Configuration</button>' +
                    '<button class="btn btn-small" onclick="resetEnvConfig(\'' + envName + '\')">Reset to Defaults</button>' +
                '</div>' +
            '</div>' +
        '</div>' +
    '</div>';
}

// ─── Save config from the editor UI back to environmentDetails ───
function saveEnvConfig(envName) {
    var details = environmentDetails[envName];
    if (!details) return;

    // Read all config-editor-input fields for this env
    var inputs = document.querySelectorAll('[data-env="' + envName + '"][data-config-key]');
    var newConfig = {};
    inputs.forEach(function(el) {
        var key = el.getAttribute('data-config-key');
        var val = el.value;
        // Try to convert to number if it looks like one
        if (el.type === 'number' || el.type === 'range') {
            val = parseFloat(val);
            if (isNaN(val)) val = el.value;
        }
        newConfig[key] = val;
    });

    details.configTemplate = newConfig;
    console.log('[ConfigEditor] Saved config for', envName, newConfig);

    // Persist to backend
    _persistCustomEnvConfig(envName, details);

    if (window.showToast) showToast('Configuration saved for ' + formatEnvironmentName(envName), 'success');
}
window.saveEnvConfig = saveEnvConfig;

// ─── Reset config to category defaults ───
function resetEnvConfig(envName) {
    var details = environmentDetails[envName];
    if (!details) return;

    var category = details.category || 'cross_workflow';
    var registry = CATEGORY_CONFIG_REGISTRY[category] || CATEGORY_CONFIG_REGISTRY['cross_workflow'];

    // Reset config template
    details.configTemplate = JSON.parse(JSON.stringify(registry.configTemplate));
    details.kpis = registry.kpis.slice();

    console.log('[ConfigEditor] Reset config for', envName, 'to', category, 'defaults');

    // Re-render the config section
    showEnvironmentDetails(envName);

    if (window.showToast) showToast('Configuration reset to ' + category + ' defaults', 'success');
}
window.resetEnvConfig = resetEnvConfig;

// ─── Add a custom KPI chip ───
function addCustomKpi(envName) {
    var input = document.getElementById('kpi-add-input-' + envName);
    if (!input) return;
    var kpiName = input.value.trim();
    if (!kpiName) return;

    var details = environmentDetails[envName];
    if (!details) return;

    if (!details.kpis) details.kpis = [];
    // Avoid duplicates
    if (details.kpis.indexOf(kpiName) !== -1) {
        if (window.showToast) showToast('KPI "' + kpiName + '" already exists.', 'error');
        return;
    }

    details.kpis.push(kpiName);
    input.value = '';

    // Re-render the KPI chips
    _rerenderKpiChips(envName);
}
window.addCustomKpi = addCustomKpi;

// ─── Remove a KPI chip ───
function removeCustomKpi(envName, idx) {
    var details = environmentDetails[envName];
    if (!details || !details.kpis) return;

    details.kpis.splice(idx, 1);
    _rerenderKpiChips(envName);
}
window.removeCustomKpi = removeCustomKpi;

// ─── Re-render KPI chips in the editor ───
function _rerenderKpiChips(envName) {
    var container = document.getElementById('kpi-chips-editor-' + envName);
    if (!container) return;

    var details = environmentDetails[envName];
    var kpis = (details && details.kpis) || [];

    var chipsHtml = kpis.map(function(kpi, idx) {
        return '<span class="kpi-chip-editable" data-idx="' + idx + '">' +
            kpi +
            '<button class="kpi-remove-btn" onclick="removeCustomKpi(\'' + envName + '\', ' + idx + ')" title="Remove KPI">&times;</button>' +
        '</span>';
    }).join('');

    container.innerHTML = chipsHtml +
        '<div class="kpi-add-row">' +
            '<input type="text" class="config-editor-input kpi-add-input" id="kpi-add-input-' + envName + '" placeholder="Add KPI..." onkeydown="if(event.key===\'Enter\'){addCustomKpi(\'' + envName + '\');event.preventDefault();}">' +
            '<button class="btn btn-small kpi-add-btn" onclick="addCustomKpi(\'' + envName + '\')">+</button>' +
        '</div>';

    // Also update the KPI list in the Description section
    var kpiListEl = container.closest('.detail-collapsible-content');
    // The Description section KPI list is separate, update it too
    var descKpiList = document.querySelector('#section-description-body .kpi-list');
    if (descKpiList) {
        descKpiList.innerHTML = kpis.map(function(kpi) {
            return '<span class="kpi-item">' + kpi + '</span>';
        }).join('');
    }
}

// ─── Persist custom env config to backend ───
function _persistCustomEnvConfig(envName, details) {
    fetch(API_BASE + '/api/custom-environments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: envName,
            category: details.category,
            kpis: details.kpis,
            configTemplate: details.configTemplate,
            trainingDefaults: details.trainingDefaults,
            sdk: details.sdk,
            hardware: details.hardware
        })
    }).then(function(res) {
        if (!res.ok) console.warn('[ConfigEditor] Failed to persist config for', envName);
        else console.log('[ConfigEditor] Persisted config for', envName);
    }).catch(function(err) {
        console.warn('[ConfigEditor] Error persisting config:', err);
    });
}

function showEnvironmentDetails(envName) {
    var env = allEnvironments.find(function(e) { return e.name === envName; });
    if (!env) return;

    var details = environmentDetails[envName] || {};

    // Route to source-specific detail views
    if (details.source === 'huggingface' || env.source === 'huggingface') {
        _showHFDetailView(env, details);
        return;
    }
    if ((env.sdk === 'custom' || details.sdk === 'custom') && details.terraformTemplate) {
        _showTerraformDetailView(env, details);
        return;
    }

    // Standard RL environment detail view
    var kpis = details.kpis || ['Clinical Outcomes', 'Operational Efficiency', 'Financial Metrics'];
    var whatItDoes = details.whatItDoes || getDefaultWhatItDoes(env.category, envName);
    var howToUse = details.howToUse || getDefaultHowToUse(env.category, envName);
    var description = details.description || env.description || getEnvironmentDescription(env.name, env.category || 'other');
    var shortDesc = description.length > 200 ? description.slice(0, 197) + '...' : description;
    var useCase = details.useCase || getUseCaseDescription(env.name, env.category || 'other');
    var kpiHtml = kpis.map(function(kpi) { return '<span class="kpi-item">' + kpi + '</span>'; }).join('');
    var actionsHtml;
    if (env.actions && env.actions.length > 0) {
        actionsHtml = '<div class="action-chips">' + env.actions.map(function(action, i) {
            var display = action.replace(/_/g, ' ').replace(/\b\w/g, function(l) { return l.toUpperCase(); });
            return '<span class="action-chip" title="' + (getActionDescription(env.name, action) || '') + '">' + (i + 1) + '. ' + display + '</span>';
        }).join('') + '</div>';
    } else {
        actionsHtml = '<p>' + (env.actionType || 'Discrete') + ' &middot; ' + (env.actionSpace || 'N/A') + ' actions</p>';
    }

    var isCustomEnv = (details.isCustom || env.source === 'custom' || env.source === 'huggingface');
    var deleteBtn = isCustomEnv ?
        '<button class="btn btn-danger btn-small" onclick="deleteEnvironment(\'' + env.name.replace(/'/g, "\\'") + '\')">' +
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14H7L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>' +
            ' Delete' +
        '</button>' : '';

    var detailBody = document.getElementById('env-detail-body');
    detailBody.innerHTML =
        '<div class="detail-hero">' +
            '<div class="detail-hero-left">' +
                '<h1 class="detail-page-title">' + formatEnvironmentName(env.name) + '</h1>' +
                '<span class="howto-popover-wrap">' +
                    '<button class="howto-trigger" aria-label="How to use this environment" tabindex="0">?</button>' +
                    '<div class="howto-popover">' +
                        '<strong style="display:block;margin-bottom:0.5rem;font-size:0.95rem;">How to Use</strong>' +
                        howToUse +
                    '</div>' +
                '</span>' +
                '<span class="env-category category-' + env.category + '">' + env.category + '</span>' +
            '</div>' +
        '</div>' +
        '<div class="detail-collapsible open" id="section-description">' +
            '<button class="detail-collapsible-header" onclick="toggleDetailSection(\'section-description\')">' +
                '<h2><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg> Description</h2>' +
                '<svg class="detail-collapsible-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>' +
            '</button>' +
            '<div class="detail-collapsible-body" id="section-description-body">' +
                '<div class="detail-collapsible-content">' +
                    '<div class="detail-grid">' +
                        '<div class="detail-card"><h3>Overview</h3><p>' + shortDesc + '</p>' +
                            '<p style="margin-top:0.75rem;font-size:0.85rem;"><strong>System:</strong> ' + (env.system || details.system || 'Multiple') + '</p>' +
                            '<p style="margin-top:0.25rem;font-size:0.85rem;"><strong>Use case:</strong> ' + useCase + '</p></div>' +
                        '<div class="detail-card"><h3>Specifications</h3><div class="spec-grid">' +
                            '<div class="spec-item"><label>State features</label><span>' + (details.stateFeatures || env.stateFeatures || 'N/A') + '</span></div>' +
                            '<div class="spec-item"><label>Action type</label><span>' + (details.actionType || env.actionType || 'Discrete') + '</span></div>' +
                            '<div class="spec-item"><label>Actions</label><span>' + (details.actionSpace || env.actionSpace || 'N/A') + '</span></div>' +
                            '<div class="spec-item"><label>Multi-agent</label><span>' + (env.multi_agent ? 'Yes' : 'No') + '</span></div>' +
                        '</div></div>' +
                        '<div class="detail-card"><h3>KPIs</h3><div class="kpi-list">' + kpiHtml + '</div></div>' +
                        '<div class="detail-card"><h3>Action choices</h3>' + actionsHtml + '</div>' +
                    '</div>' +
                    '<div class="detail-section" style="margin-top:1.25rem;"><h3>What it does</h3><div class="info-box">' + whatItDoes + '</div></div>' +
                '</div>' +
            '</div>' +
        '</div>' +
        buildScenariosSection(envName, env.category) +
        buildVerifiersSection(envName, env.category) +
        buildConfigEditorSection(envName, details) +
        '<div class="detail-collapsible" id="section-environment">' +
            '<button class="detail-collapsible-header" onclick="toggleDetailSection(\'section-environment\')">' +
                '<h2><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 3h6v5l5 9H4l5-9V3z"/><line x1="9" y1="3" x2="15" y2="3"/></svg> Simulations</h2>' +
                '<svg class="detail-collapsible-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>' +
            '</button>' +
            '<div class="detail-collapsible-body" id="section-environment-body">' +
                '<div class="detail-collapsible-content" style="padding:0;">' +
                    '<iframe src="/test-console?env=' + encodeURIComponent(envName) + '&embedded=1" style="width:100%;height:700px;border:none;" loading="lazy"></iframe>' +
                '</div>' +
            '</div>' +
        '</div>' +
        buildTrainingSection(envName, env.category) +
        '<div class="detail-popup-overlay" id="detail-popup-overlay" onclick="closeDetailPopup(event)">' +
            '<div class="detail-popup-box" onclick="event.stopPropagation()">' +
                '<div class="detail-popup-header"><h3 id="detail-popup-title">Console</h3>' +
                    '<button class="detail-popup-close" onclick="closeDetailPopup()" aria-label="Close">&times;</button></div>' +
                '<div class="detail-popup-body" id="detail-popup-body"><div class="detail-popup-loading">Loading\u2026</div></div>' +
            '</div>' +
        '</div>' +
        (deleteBtn ? '<div class="env-delete-bottom">' + deleteBtn + '</div>' : '');

    requestAnimationFrame(function() {
        var descBody = document.getElementById('section-description-body');
        if (descBody) {
            descBody.style.maxHeight = descBody.scrollHeight + 'px';
            setTimeout(function() { descBody.style.maxHeight = 'none'; }, 500);
        }
    });

    document.getElementById('catalog-container').style.display = 'none';
    document.getElementById('env-detail-page').style.display = 'block';
}

// ─── HuggingFace Environment Detail View ───
function _showHFDetailView(env, details) {
    var detailBody = document.getElementById('env-detail-body');
    var name = env.name;
    var sdk = details.sdk || env.sdk || 'unknown';
    var hfUrl = details.hf_url || env.hf_url || '';
    var hfOwner = details.hf_owner || env.hf_owner || '';
    var hfRepo = details.hf_repo || env.hf_repo || '';
    // Parse owner/repo from URL if not stored directly
    if ((!hfOwner || !hfRepo) && hfUrl) {
        var _m = hfUrl.match(/huggingface\.co\/spaces\/([^/]+)\/([^/?#]+)/i);
        if (_m) { hfOwner = _m[1]; hfRepo = _m[2]; }
    }
    var author = details.author || hfOwner || '';
    var license = details.license || '';
    var tags = details.tags || [];
    var files = details.files || [];
    var endpoints = details.endpoints || [];
    var models = details.models || {};
    var readme = details.readme || '';
    var openenv = details.openenv || {};
    var pyproject = details.pyproject || {};
    var desc = details.description || env.description || '';

    // Tags HTML
    var tagsHtml = tags.map(function(t) { return '<span class="hf-tag">' + t + '</span>'; }).join('');

    // Metadata grid
    var metaItems = [
        { label: 'SDK', value: sdk },
        { label: 'Runtime', value: openenv.runtime || sdk },
        { label: 'Port', value: openenv.port || (details.frontMatter || {}).app_port || '—' },
        { label: 'Author', value: author },
        { label: 'License', value: license || 'Not specified' },
        { label: 'Likes', value: (details.likes || 0) + '' }
    ];
    var metaHtml = metaItems.map(function(m) {
        return '<div class="hf-meta-item"><span class="hf-meta-label">' + m.label + '</span><span class="hf-meta-value">' + m.value + '</span></div>';
    }).join('');

    // Endpoints HTML
    var endpointsHtml = '';
    if (endpoints.length > 0) {
        endpointsHtml = '<div class="hf-endpoints"><h3>API Endpoints</h3><div class="hf-endpoint-list">' +
            endpoints.map(function(ep) {
                return '<div class="hf-endpoint"><span class="hf-method hf-method-' + ep.method.toLowerCase() + '">' + ep.method + '</span><code>' + ep.path + '</code></div>';
            }).join('') + '</div></div>';
    }

    // Models HTML
    var modelsHtml = '';
    var modelKeys = Object.keys(models);
    if (modelKeys.length > 0) {
        modelsHtml = '<div class="hf-models"><h3>Data Models</h3>' +
            modelKeys.map(function(mk) {
                var m = models[mk];
                var fieldsHtml = m.fields.map(function(f) {
                    if (f.value) return '<div class="hf-model-field"><code>' + f.name + '</code> = <code>"' + f.value + '"</code></div>';
                    return '<div class="hf-model-field"><code>' + f.name + '</code><span class="hf-model-type">' + (f.type || '') + '</span>' +
                        (f.description ? '<span class="hf-model-desc">' + f.description + '</span>' : '') + '</div>';
                }).join('');
                return '<div class="hf-model-card"><h4>' + mk + (m.doc ? ' <span class="hf-model-doc">' + m.doc + '</span>' : '') + '</h4>' + fieldsHtml + '</div>';
            }).join('') + '</div>';
    }

    // Files HTML
    var filesHtml = '';
    if (files.length > 0) {
        filesHtml = files.map(function(f) {
            var sizeStr = f.size < 1024 ? f.size + ' B' : (f.size < 1048576 ? (f.size / 1024).toFixed(1) + ' KB' : (f.size / 1048576).toFixed(1) + ' MB');
            var ext = f.path.split('.').pop().toLowerCase();
            var icon = ext === 'py' ? '🐍' : ext === 'md' ? '📄' : ext === 'yaml' || ext === 'yml' ? '⚙️' : ext === 'toml' ? '📦' : ext === 'json' ? '{}' : ext === 'html' ? '🌐' : '📁';
            return '<div class="hf-file" onclick="viewEnvFile(\'' + name + '\', \'' + f.path.replace(/'/g, "\\'") + '\')">' +
                '<span class="hf-file-icon">' + icon + '</span>' +
                '<span class="hf-file-name">' + f.path + '</span>' +
                '<span class="hf-file-size">' + sizeStr + '</span></div>';
        }).join('');
    }

    // Dependencies
    var depsHtml = '';
    if (pyproject.dependencies && pyproject.dependencies.length > 0) {
        depsHtml = '<div class="hf-deps"><h3>Dependencies</h3><div class="hf-dep-list">' +
            pyproject.dependencies.map(function(d) { return '<span class="hf-dep">' + d + '</span>'; }).join('') +
            '</div></div>';
    }

    // Simple markdown-to-html for README (headers, code blocks, paragraphs)
    var readmeHtml = '';
    if (readme) {
        readmeHtml = _simpleMarkdown(readme);
    }

    var hfDeleteBtn = '<button class="btn btn-danger btn-small" onclick="deleteEnvironment(\'' + name.replace(/'/g, "\\'") + '\')">' +
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14H7L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>' +
        ' Delete</button>';

    detailBody.innerHTML =
        // Hero
        '<div class="detail-hero">' +
            '<div class="detail-hero-left">' +
                '<h1 class="detail-page-title">' + formatEnvironmentName(name) + '</h1>' +
                '<span class="hf-badge hf-badge-sdk">' + sdk + '</span>' +
                (hfUrl ? '<a href="' + hfUrl + '" target="_blank" class="hf-source-link">View on HuggingFace ↗</a>' : '') +
            '</div>' +
        '</div>' +
        (desc ? '<p class="hf-description">' + desc + '</p>' : '') +
        (tagsHtml ? '<div class="hf-tags-row">' + tagsHtml + '</div>' : '') +

        // Metadata grid
        '<div class="hf-meta-grid">' + metaHtml + '</div>' +

        // Tabbed content: App / Files / README / API
        '<div class="hf-tabs" id="hf-tabs">' +
            '<button class="hf-tab active" data-tab="hf-tab-app" onclick="switchHFTab(this)">App</button>' +
            '<button class="hf-tab" data-tab="hf-tab-files" onclick="switchHFTab(this)">Files <span class="hf-tab-count">' + files.length + '</span></button>' +
            '<button class="hf-tab" data-tab="hf-tab-readme" onclick="switchHFTab(this)">README</button>' +
            (endpoints.length > 0 ? '<button class="hf-tab" data-tab="hf-tab-api" onclick="switchHFTab(this)">API</button>' : '') +
        '</div>' +

        // Tab: App (embedded directly via HF Space embed URL)
        '<div class="hf-tab-panel active" id="hf-tab-app">' +
            (hfUrl && hfOwner && hfRepo ?
                '<div class="hf-iframe-wrap"><iframe id="hf-app-iframe" class="hf-iframe" src="https://' + hfOwner + '-' + hfRepo + '.hf.space" allow="accelerometer; camera; encrypted-media; geolocation; gyroscope; microphone" sandbox="allow-scripts allow-same-origin allow-forms allow-popups" loading="lazy"></iframe></div>' +
                '<p style="text-align:center;font-size:0.75rem;color:#888;margin-top:0.5rem;">Embedded from <a href="' + hfUrl + '" target="_blank" style="color:var(--primary-color);">' + hfUrl + '</a></p>' :
            '<div class="hf-empty-state">No live preview available. The environment has been cloned locally.</div>') +
        '</div>' +

        // Tab: Files
        '<div class="hf-tab-panel" id="hf-tab-files">' +
            '<div class="hf-file-browser">' + filesHtml + '</div>' +
            '<div class="hf-file-viewer" id="hf-file-viewer" style="display:none;">' +
                '<div class="hf-file-viewer-header"><span id="hf-file-viewer-title"></span>' +
                    '<button class="hf-file-close-btn" onclick="closeFileViewer()" title="Close (Esc)"><kbd>Esc</kbd></button></div>' +
                '<pre class="hf-file-content" id="hf-file-content"></pre>' +
            '</div>' +
        '</div>' +

        // Tab: README
        '<div class="hf-tab-panel" id="hf-tab-readme">' +
            (readmeHtml ? '<div class="hf-readme">' + readmeHtml + '</div>' : '<div class="hf-empty-state">No README found.</div>') +
        '</div>' +

        // Tab: API
        '<div class="hf-tab-panel" id="hf-tab-api">' +
            endpointsHtml + modelsHtml + depsHtml +
        '</div>' +
        '<div class="env-delete-bottom">' + hfDeleteBtn + '</div>';

    // No proxy needed - iframe uses direct HF Space embed URL

    document.getElementById('catalog-container').style.display = 'none';
    document.getElementById('env-detail-page').style.display = 'block';
}

function switchHFTab(btn) {
    var tabId = btn.getAttribute('data-tab');
    document.querySelectorAll('.hf-tab').forEach(function(t) { t.classList.remove('active'); });
    document.querySelectorAll('.hf-tab-panel').forEach(function(p) { p.classList.remove('active'); });
    btn.classList.add('active');
    var panel = document.getElementById(tabId);
    if (panel) panel.classList.add('active');
}
window.switchHFTab = switchHFTab;

function viewEnvFile(envName, filePath) {
    var viewer = document.getElementById('hf-file-viewer');
    var titleEl = document.getElementById('hf-file-viewer-title');
    var contentEl = document.getElementById('hf-file-content');
    if (!viewer || !contentEl) return;
    viewer.style.display = 'block';
    titleEl.textContent = filePath;
    contentEl.textContent = 'Loading...';
    fetch(API_BASE + '/api/environment/' + encodeURIComponent(envName) + '/file?path=' + encodeURIComponent(filePath))
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.content) contentEl.textContent = data.content;
            else contentEl.textContent = '(File too large or binary)';
        })
        .catch(function() { contentEl.textContent = '(Error loading file)'; });
}
window.viewEnvFile = viewEnvFile;

function closeFileViewer() {
    var v = document.getElementById('hf-file-viewer');
    if (v) v.style.display = 'none';
}
window.closeFileViewer = closeFileViewer;

// Close file viewer on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        var v = document.getElementById('hf-file-viewer');
        if (v && v.style.display !== 'none') {
            v.style.display = 'none';
            e.preventDefault();
        }
    }
});

function _simpleMarkdown(md) {
    // Very simple markdown renderer: headers, code blocks, bold, links, paragraphs
    var html = '';
    var inCode = false;
    var lines = md.split('\n');
    for (var i = 0; i < lines.length; i++) {
        var line = lines[i];
        if (line.startsWith('```')) {
            if (inCode) { html += '</code></pre>'; inCode = false; }
            else { html += '<pre class="hf-code-block"><code>'; inCode = true; }
            continue;
        }
        if (inCode) { html += line.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '\n'; continue; }
        if (line.startsWith('### ')) { html += '<h4>' + line.slice(4) + '</h4>'; continue; }
        if (line.startsWith('## ')) { html += '<h3>' + line.slice(3) + '</h3>'; continue; }
        if (line.startsWith('# ')) { html += '<h2>' + line.slice(2) + '</h2>'; continue; }
        if (line.trim() === '') { html += '<br>'; continue; }
        // Inline formatting
        line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        line = line.replace(/`([^`]+)`/g, '<code class="hf-inline-code">$1</code>');
        line = line.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
        if (line.startsWith('- ')) { html += '<li>' + line.slice(2) + '</li>'; continue; }
        html += '<p>' + line + '</p>';
    }
    if (inCode) html += '</code></pre>';
    return html;
}

// ─── Terraform/Custom Environment Detail View ───
function _showTerraformDetailView(env, details) {
    var detailBody = document.getElementById('env-detail-body');
    var name = env.name;
    var desc = details.description || env.description || '';
    var tf = details.terraformTemplate || '';
    var sdk = details.sdk || 'custom';
    var hardware = details.hardware || env.hardware || 'cpu-basic';

    var tfDeleteBtn = '<button class="btn btn-danger btn-small" onclick="deleteEnvironment(\'' + name.replace(/'/g, "\\'") + '\')">' +
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-2 14H7L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>' +
        ' Delete</button>';

    detailBody.innerHTML =
        '<div class="detail-hero">' +
            '<div class="detail-hero-left">' +
                '<h1 class="detail-page-title">' + formatEnvironmentName(name) + '</h1>' +
                '<span class="hf-badge hf-badge-sdk">Terraform</span>' +
                '<span class="hf-badge" style="background:#444;color:#fff;">' + hardware + '</span>' +
            '</div>' +
        '</div>' +
        (desc ? '<p class="hf-description" style="color:#333;">' + desc + '</p>' : '') +

        // Tabs: Infrastructure / Container / Configuration
        '<div class="hf-tabs" id="tf-tabs">' +
            '<button class="hf-tab active" data-tab="tf-tab-infra" onclick="switchHFTab(this)">Infrastructure</button>' +
            '<button class="hf-tab" data-tab="tf-tab-container" onclick="switchHFTab(this)">Container</button>' +
            '<button class="hf-tab" data-tab="tf-tab-config" onclick="switchHFTab(this)">Configuration</button>' +
        '</div>' +

        '<div class="hf-tab-panel active" id="tf-tab-infra">' +
            '<div class="tf-code-wrap">' +
                '<div class="tf-code-header"><span>main.tf</span></div>' +
                '<pre class="hf-code-block"><code>' + tf.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</code></pre>' +
            '</div>' +
        '</div>' +

        // Simulated mini-container
        '<div class="hf-tab-panel" id="tf-tab-container">' +
            '<div class="sim-container">' +
                '<div class="sim-container-header">' +
                    '<div class="sim-container-status"><span class="sim-status-dot"></span> Running</div>' +
                    '<span class="sim-container-id">' + name.toLowerCase().replace(/[^a-z0-9]/g, '') + '-' + Math.random().toString(36).slice(2, 8) + '</span>' +
                '</div>' +
                '<div class="sim-terminal" id="sim-terminal">' +
                    '<div class="sim-terminal-line sim-line-system">RL Environment Container Runtime v0.1.0</div>' +
                    '<div class="sim-terminal-line sim-line-system">Initializing environment: <span style="color:#7dd3fc;">' + formatEnvironmentName(name) + '</span></div>' +
                    '<div class="sim-terminal-line sim-line-system">Hardware: ' + hardware + '</div>' +
                    '<div class="sim-terminal-line sim-line-system">---</div>' +
                '</div>' +
                '<div class="sim-input-row">' +
                    '<span class="sim-prompt">$</span>' +
                    '<input type="text" class="sim-input" id="sim-cmd-input" placeholder="Type a command..." autocomplete="off">' +
                '</div>' +
            '</div>' +
        '</div>' +

        '<div class="hf-tab-panel" id="tf-tab-config">' +
            '<div class="hf-empty-state" style="color:#555;">Custom configuration will be defined by the environment workflow.<br>No RL parameters apply to this environment.</div>' +
        '</div>' +
        '<div class="env-delete-bottom">' + tfDeleteBtn + '</div>';

    // Wire up simulated terminal
    _initSimTerminal(name, hardware);

    document.getElementById('catalog-container').style.display = 'none';
    document.getElementById('env-detail-page').style.display = 'block';
}

function _initSimTerminal(envName, hardware) {
    var input = document.getElementById('sim-cmd-input');
    var terminal = document.getElementById('sim-terminal');
    if (!input || !terminal) return;

    var envState = { step: 0, reward: 0, done: false };

    input.addEventListener('keydown', function(e) {
        if (e.key !== 'Enter') return;
        var cmd = input.value.trim();
        if (!cmd) return;
        input.value = '';

        // Echo command
        var cmdLine = document.createElement('div');
        cmdLine.className = 'sim-terminal-line';
        cmdLine.innerHTML = '<span class="sim-prompt-echo">$ </span>' + cmd.replace(/</g, '&lt;');
        terminal.appendChild(cmdLine);

        // Process command
        var output = _processSimCmd(cmd, envName, hardware, envState);
        output.forEach(function(line) {
            var outLine = document.createElement('div');
            outLine.className = 'sim-terminal-line ' + (line.cls || '');
            outLine.innerHTML = line.text;
            terminal.appendChild(outLine);
        });

        terminal.scrollTop = terminal.scrollHeight;
    });

    // Auto-focus when container tab is shown
    input.focus();
}

function _processSimCmd(cmd, envName, hardware, state) {
    var parts = cmd.toLowerCase().split(/\s+/);
    var action = parts[0];

    if (action === 'help') {
        return [
            { text: 'Available commands:', cls: 'sim-line-info' },
            { text: '  status    — Show container status' },
            { text: '  env       — Show environment info' },
            { text: '  reset     — Reset environment state' },
            { text: '  step [n]  — Advance simulation by n steps' },
            { text: '  observe   — Get current observation' },
            { text: '  act <id>  — Take an action (0-3)' },
            { text: '  logs      — View recent logs' },
            { text: '  clear     — Clear terminal' },
            { text: '  help      — Show this help' }
        ];
    }
    if (action === 'clear') {
        var terminal = document.getElementById('sim-terminal');
        if (terminal) terminal.innerHTML = '<div class="sim-terminal-line sim-line-system">Terminal cleared.</div>';
        return [];
    }
    if (action === 'status') {
        return [
            { text: 'Container: <span style="color:#4ade80;">RUNNING</span>', cls: 'sim-line-info' },
            { text: 'Uptime: ' + Math.floor(Math.random() * 3600) + 's' },
            { text: 'Memory: ' + (Math.random() * 200 + 50).toFixed(0) + ' MB / ' + (hardware.includes('32') ? '32 GB' : '16 GB') },
            { text: 'CPU: ' + (Math.random() * 15 + 1).toFixed(1) + '%' }
        ];
    }
    if (action === 'env') {
        return [
            { text: 'Environment: ' + envName, cls: 'sim-line-info' },
            { text: 'SDK: custom (terraform)' },
            { text: 'Hardware: ' + hardware },
            { text: 'Step: ' + state.step + '  Reward: ' + state.reward.toFixed(2) + '  Done: ' + state.done }
        ];
    }
    if (action === 'reset') {
        state.step = 0; state.reward = 0; state.done = false;
        return [{ text: 'Environment reset. Step=0, Reward=0.00', cls: 'sim-line-success' }];
    }
    if (action === 'step') {
        var n = parseInt(parts[1]) || 1;
        for (var i = 0; i < n && !state.done; i++) {
            state.step++;
            var r = (Math.random() - 0.3) * 2;
            state.reward += r;
            if (state.step >= 50) state.done = true;
        }
        return [
            { text: 'Advanced ' + n + ' step(s).', cls: 'sim-line-info' },
            { text: 'Step: ' + state.step + '  Reward: ' + state.reward.toFixed(2) + (state.done ? '  [DONE]' : '') }
        ];
    }
    if (action === 'observe') {
        var obs = [];
        for (var j = 0; j < 4; j++) obs.push((Math.random() * 2 - 1).toFixed(3));
        return [{ text: 'Observation: [' + obs.join(', ') + ']', cls: 'sim-line-info' }];
    }
    if (action === 'act') {
        var aid = parseInt(parts[1]);
        if (isNaN(aid) || aid < 0 || aid > 3) return [{ text: 'Invalid action. Use 0-3.', cls: 'sim-line-error' }];
        state.step++;
        var rw = (Math.random() - 0.2) * 2;
        state.reward += rw;
        if (state.step >= 50) state.done = true;
        return [
            { text: 'Action ' + aid + ' executed.', cls: 'sim-line-info' },
            { text: 'Reward: ' + rw.toFixed(3) + '  Total: ' + state.reward.toFixed(2) + '  Step: ' + state.step + (state.done ? '  [DONE]' : '') }
        ];
    }
    if (action === 'logs') {
        var ts = new Date().toISOString().slice(11, 19);
        return [
            { text: '[' + ts + '] INFO  Container started', cls: 'sim-line-dim' },
            { text: '[' + ts + '] INFO  Environment loaded: ' + envName, cls: 'sim-line-dim' },
            { text: '[' + ts + '] INFO  Waiting for agent commands...', cls: 'sim-line-dim' }
        ];
    }
    return [{ text: 'Unknown command: ' + cmd + '. Type "help" for available commands.', cls: 'sim-line-error' }];
}
window._initSimTerminal = _initSimTerminal;

// ─── Toggle collapsible detail sections ───
function toggleDetailSection(sectionId) {
    var section = document.getElementById(sectionId);
    if (!section) return;
    var body = document.getElementById(sectionId + '-body');
    if (!body) return;

    if (section.classList.contains('open')) {
        // Collapse: set explicit height first, then transition to 0
        body.style.maxHeight = body.scrollHeight + 'px';
        body.offsetHeight; // force reflow
        body.style.maxHeight = '0';
        section.classList.remove('open');
    } else {
        // Expand: set max-height to scrollHeight, then switch to none after transition
        section.classList.add('open');
        body.style.maxHeight = body.scrollHeight + 'px';
        setTimeout(function() {
            if (section.classList.contains('open')) {
                body.style.maxHeight = 'none';
            }
        }, 400);
    }
}

// ─── Open/Close Detail Popup (for Environment / Training) ───
function openDetailPopup(id, src, title) {
    var overlay = document.getElementById('detail-popup-overlay');
    var titleEl = document.getElementById('detail-popup-title');
    var bodyEl  = document.getElementById('detail-popup-body');
    if (!overlay || !bodyEl) return;

    titleEl.textContent = title || 'Console';
    // Clear previous content and show loading
    bodyEl.innerHTML = '';
    var loadingDiv = document.createElement('div');
    loadingDiv.className = 'detail-popup-loading';
    loadingDiv.textContent = 'Loading\u2026';
    bodyEl.appendChild(loadingDiv);

    overlay.classList.add('active');
    document.body.style.overflow = 'hidden'; // prevent background scroll

    // Create iframe
    var iframe = document.createElement('iframe');
    iframe.setAttribute('title', title || 'Console');
    iframe.style.opacity = '0';
    iframe.onload = function() {
        // Remove loading text, reveal iframe
        if (loadingDiv.parentNode) loadingDiv.remove();
        iframe.style.opacity = '1';
    };
    bodyEl.appendChild(iframe);
    // Set src AFTER appending to DOM to ensure proper loading
    iframe.src = src;
}

function closeDetailPopup(event) {
    // If called from overlay click, only close if clicking the overlay itself
    if (event && event.target !== document.getElementById('detail-popup-overlay')) return;

    var overlay = document.getElementById('detail-popup-overlay');
    if (!overlay) return;
    overlay.classList.remove('active');
    document.body.style.overflow = '';

    // Clean up iframe to stop any running content
    var bodyEl = document.getElementById('detail-popup-body');
    if (bodyEl) bodyEl.innerHTML = '';
}

// Close popup on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        if (_trainingReportOverlay && _trainingReportOverlay.classList.contains('active')) {
            _closeTrainingReportPopup();
            return;
        }
        var overlay = document.getElementById('detail-popup-overlay');
        if (overlay && overlay.classList.contains('active')) {
            closeDetailPopup();
        }
    }
});

async function testEnvironment(envName) {
    try {
        const response = await fetch(`${API_BASE}/kpis/${envName}`);
        if (!response.ok) throw new Error('Failed to test environment');
        
        const data = await response.json();
        
        showToast('Environment test completed successfully.', 'success');
    } catch (error) {
        showToast('Error testing environment: ' + error.message + '. Make sure the API server is running.', 'error');
    }
}

const JIRA_ENV_VERIFIERS = [
    { value: 'jira_workflow:issue_resolution', label: 'Jira Issue Resolution' },
    { value: 'jira_workflow:status_update', label: 'Jira Status Update' },
    { value: 'jira_workflow:comment_management', label: 'Jira Comment Management' },
    { value: 'jira_workflow:subtask_management', label: 'Jira Task Management' }
];
const JIRA_ENVS = ['JiraIssueResolution', 'JiraStatusUpdate', 'JiraCommentManagement', 'JiraSubtaskManagement'];
const JIRA_ENV_TO_WORKFLOW = { JiraIssueResolution: 'issue_resolution', JiraStatusUpdate: 'status_update', JiraCommentManagement: 'comment_management', JiraSubtaskManagement: 'subtask_management' };

function openTrainingConfig(envName) {
    // Navigate to Training Console with environment pre-selected
    window.location.href = '/training-console?env=' + encodeURIComponent(envName);
}

function openTrainingConfigPopup(envName) {
    // Open the new training-console UI inside a modal iframe
    var existing = document.getElementById('training-config-modal');
    if (existing) existing.remove();

    var overlay = document.createElement('div');
    overlay.className = 'modal training-config-modal';
    overlay.id = 'training-config-modal';
    overlay.style.cssText = 'display:flex;align-items:center;justify-content:center;position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.6);backdrop-filter:blur(2px);';
    overlay.onclick = function(e) { if (e.target === overlay) closeTrainingConfig(); };

    var container = document.createElement('div');
    container.style.cssText = 'position:relative;width:92vw;max-width:1200px;height:88vh;border-radius:12px;overflow:hidden;background:var(--bg-primary,#fff);box-shadow:0 25px 60px rgba(0,0,0,0.3);';

    var closeBtn = document.createElement('button');
    closeBtn.innerHTML = '&times;';
    closeBtn.style.cssText = 'position:absolute;top:8px;right:12px;z-index:10;background:none;border:none;font-size:1.6rem;cursor:pointer;color:var(--text-secondary,#666);line-height:1;padding:4px 8px;border-radius:4px;';
    closeBtn.onclick = closeTrainingConfig;
    closeBtn.onmouseover = function() { this.style.background = 'var(--bg-hover,#f0f0f0)'; };
    closeBtn.onmouseout = function() { this.style.background = 'none'; };

    var iframe = document.createElement('iframe');
    iframe.src = '/training-console?env=' + encodeURIComponent(envName) + '&embedded=1';
    iframe.style.cssText = 'width:100%;height:100%;border:none;';

    container.appendChild(closeBtn);
    container.appendChild(iframe);
    overlay.appendChild(container);
    document.body.appendChild(overlay);
}
window.openTrainingConfigPopup = openTrainingConfigPopup;

function toggleTrainingInline(envName) {
    var wrap = document.getElementById('training-inline-iframe-wrap');
    if (!wrap) return;
    var iframe = document.getElementById('training-inline-iframe');
    if (wrap.style.display === 'none' || !wrap.style.display) {
        // Show inline iframe — expand the training section if collapsed
        var section = document.getElementById('section-training');
        if (section && !section.classList.contains('open')) {
            toggleDetailSection('section-training');
        }
        if (iframe && !iframe.src.includes('/training-console')) {
            iframe.src = '/training-console?env=' + encodeURIComponent(envName) + '&embedded=1';
        }
        wrap.style.display = 'block';
    } else {
        // Hide inline iframe
        wrap.style.display = 'none';
    }
}
window.toggleTrainingInline = toggleTrainingInline;

function _openTrainingConfigModal(envName) {
    const env = allEnvironments.find(e => e.name === envName);
    const exampleConfig = getExampleConfig(envName);
    const systemStr = (env && env.system) ? env.system : 'Multiple';
    const envSystemsList = systemStr.split(',').map(s => s.trim()).filter(Boolean);
    const hasMultiple = envSystemsList.length > 1;
    const isJiraEnv = JIRA_ENVS.includes(envName);

    // Read custom training defaults from environmentDetails (for custom environments)
    const envDetails = environmentDetails[envName] || {};
    const trainingDefaults = envDetails.trainingDefaults || {};
    const hwDefaults = envDetails.hardwareDefaults || {};
    const sdkDefaults = envDetails.sdkDefaults || {};
    const defaultAlgorithm = trainingDefaults.algorithm || 'PPO';
    const defaultEpisodes = trainingDefaults.episodes || 100;
    const defaultMaxSteps = trainingDefaults.maxSteps || 1000;
    const defaultJiraWorkflow = JIRA_ENV_TO_WORKFLOW[envName] || 'issue_resolution';
    const hasVerifierForWorkflow = JIRA_ENV_VERIFIERS.some(v => v.value === 'jira_workflow:' + defaultJiraWorkflow);
    const verifierOptionsHtml = isJiraEnv
        ? JIRA_ENV_VERIFIERS.map(v => `<option value="${v.value}"${v.value === 'jira_workflow:' + defaultJiraWorkflow ? ' selected' : ''}>${v.label}</option>`).join('') +
            `<option value="default"${!hasVerifierForWorkflow ? ' selected' : ''}>Default (Environment Built-in)</option>`
        : `<option value="ensemble" selected>Ensemble (Default)</option>
                            <option value="clinical">Clinical Verifier</option>
                            <option value="operational">Operational Verifier</option>
                            <option value="financial">Financial Verifier</option>
                            <option value="compliance">Compliance Verifier</option>
                            <option value="human_evaluation">Human Evaluation</option>
                            <option value="default">Default (Environment Built-in)</option>`;

    const configModal = document.createElement('div');
    configModal.className = 'modal training-config-modal';
    configModal.id = 'training-config-modal';
    configModal.innerHTML = `
        <div class="modal-content">
            <span class="close" onclick="closeTrainingConfig()">&times;</span>
            <h2 style="margin-bottom: 0.5rem; font-size: 1.35rem;">🎓 Configure Training: ${formatEnvironmentName(envName)}</h2>
            
            <div class="training-system-block">
                <label>Software system <span class="tooltip-icon" title="Select the software system this training is for. Verifier and weights will be suggested based on the selected system.">ℹ️</span></label>
                <select id="training-software-system" class="system-filter-select" style="min-width: 200px;" onchange="updateTrainingVerifierForSystem(); var v=document.getElementById('training-system-header-value'); if(v) v.textContent=this.options[this.selectedIndex].text;">
                    ${envSystemsList.length === 1
                        ? `<option value="${envSystemsList[0].replace(/"/g, '&quot;')}" selected>${envSystemsList[0]}</option>`
                        : `<option value="all">All (${systemStr})</option>` + envSystemsList.map(s => `<option value="${s.replace(/"/g, '&quot;')}">${s}</option>`).join('')}
                </select>
                <small>Training context for this run. Verifier suggestions update when you change the system.</small>
            </div>
            
            <div class="config-tabs">
                <button class="config-tab active" onclick="switchConfigTab('manual')" id="tab-manual">📝 Manual Entry</button>
                <button class="config-tab" onclick="switchConfigTab('json')" id="tab-json">📄 JSON Upload</button>
                <button class="config-tab" onclick="switchConfigTab('api')" id="tab-api">🔌 API Example</button>
            </div>
            
            <div id="config-manual" class="config-tab-content">
                <section class="training-section">
                    <span class="training-section-title">Agent model</span>
                    <div class="form-group">
                        <label>Agent model</label>
                        <select id="training-algorithm" onchange="updateModelInfo()">
                            <option value="PPO"${defaultAlgorithm === 'PPO' ? ' selected' : ''}>PPO (Proximal Policy Optimization)</option>
                            <option value="DQN"${defaultAlgorithm === 'DQN' ? ' selected' : ''}>DQN (Deep Q-Network)</option>
                            <option value="A2C"${defaultAlgorithm === 'A2C' ? ' selected' : ''}>A2C (Advantage Actor-Critic)</option>
                            <option value="SAC"${defaultAlgorithm === 'SAC' ? ' selected' : ''}>SAC (Soft Actor-Critic)</option>
                            <option value="SLM"${defaultAlgorithm === 'SLM' ? ' selected' : ''}>SLM (Small Language Model – Jira)</option>
                        </select>
                        <small id="model-info">PPO uses an MLP policy network with separate actor and critic. Default: [64, 64] hidden layers.</small>
                    </div>
                </section>
                
                <section class="training-section">
                    <span class="training-section-title">Reward verifier</span>
                    <div id="training-verifier-section">
                        <div class="verifier-compact-controls">
                            <select id="training-verifier-system-select" class="verifier-compact-select" title="System"></select>
                            <select id="training-verifier-type-filter" class="verifier-compact-select" title="Type filter">
                                <option value="all">All types</option>
                                <option value="rule-based">Rule-based</option>
                                <option value="trajectory-based">Trajectory</option>
                                <option value="llm-judge">LLM Judge</option>
                                <option value="human-eval">Human Eval</option>
                            </select>
                        </div>
                        <select id="training-verifier-dropdown" class="verifier-main-dropdown">
                            <option value="">-- Select verifier --</option>
                        </select>
                        <div id="training-verifier-info-row" class="verifier-info-row" style="display:none;"></div>
                        <div id="training-verifier-sub-filter" class="verifier-sub-filter" style="display:none;"></div>
                        <div id="training-hil-notice" class="hil-notice" style="display:none;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2" style="flex-shrink:0;"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                            <span>Human evaluation required.</span>
                        </div>
                        <small style="display:block;margin-top:0.25rem;color:var(--text-secondary);font-size:0.78rem;">Select a verifier to define the reward signal for training.</small>
                    </div>
                    <div class="form-group" id="training-verifier-weights-group" style="display: none;">
                        <label>Verifier weights (JSON)</label>
                        <textarea id="training-verifier-weights" rows="3" placeholder='{"clinical": 0.4, "operational": 0.3, "financial": 0.2, "compliance": 0.1}'></textarea>
                    </div>
                </section>
                
                <section class="training-section">
                    <span class="training-section-title">Training parameters</span>
                    <div class="form-group">
                        <label>Dataset URL (optional)</label>
                        <input type="url" id="training-dataset-url" placeholder="https://example.com/dataset.csv" />
                        <small>URL to training data (CSV/JSON). Omit for synthetic data.</small>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Episodes</label>
                            <input type="number" id="training-episodes" value="${defaultEpisodes}" min="10" max="10000" />
                            <small>More episodes = longer training.</small>
                        </div>
                        <div class="form-group">
                            <label>Max steps per episode</label>
                            <input type="number" id="training-max-steps" value="${defaultMaxSteps}" min="100" max="10000" />
                            <small>Steps before episode ends.</small>
                        </div>
                    </div>
                </section>
                
                <section class="training-section" id="jira-scenario-section" style="display: ${envName === 'JiraStatusUpdate' ? 'block' : 'none'};">
                    <span class="training-section-title">Jira scenario</span>
                    <div class="form-group">
                        <label>Scenario <span class="tooltip-icon" title="Select the status update scenario. Agent runs across all Jira issues in mock data.">ℹ️</span></label>
                        <select id="training-jira-scenario">
                            <option value="in_progress_to_blocked" ${(exampleConfig.scenario_id || 'in_progress_to_blocked') === 'in_progress_to_blocked' ? 'selected' : ''}>Change from in-progress to blocked</option>
                            <option value="in_progress_to_done" ${exampleConfig.scenario_id === 'in_progress_to_done' ? 'selected' : ''}>Change from in-progress to done</option>
                        </select>
                        <small>Agent runs across all mock Jira issues. No live Jira instance required.</small>
                    </div>
                </section>
                <section class="training-section" id="jira-subtask-scenario-section" style="display: ${envName === 'JiraSubtaskManagement' ? 'block' : 'none'};">
                    <span class="training-section-title">Jira sub-task scenario</span>
                    <div class="form-group">
                        <label>Scenario <span class="tooltip-icon" title="Select the sub-task scenario. Agent runs across all Jira issues in mock data.">ℹ️</span></label>
                        <select id="training-jira-subtask-scenario">
                            <option value="create_subtask" ${(exampleConfig.scenario_id || 'create_subtask') === 'create_subtask' ? 'selected' : ''}>Create sub-task</option>
                            <option value="delete_subtask" ${exampleConfig.scenario_id === 'delete_subtask' ? 'selected' : ''}>Delete sub task</option>
                        </select>
                        <small>Agent runs across all mock Jira issues. No live Jira instance required.</small>
                    </div>
                </section>
                <section class="training-section">
                    <span class="training-section-title">Environment configuration</span>
                    <div class="form-group">
                        <label>Config (JSON)</label>
                        <textarea id="training-config-json" rows="6" placeholder='{"queue_size": 15, "high_urgency_pct": 30}' style="min-height: 120px;">${JSON.stringify(exampleConfig, null, 2)}</textarea>
                        <small>Optional. Environment-specific parameters. Include scenario_id for Jira Status Update. Agent runs across all issues.</small>
                    </div>
                </section>
                
                ${envDetails.isCustom ? `
                <div class="training-hw-profile">
                    <h4>⚡ Hardware Profile</h4>
                    <div class="config-infra-row" style="margin-top:0.5rem;">
                        <div class="config-infra-item"><label>SDK</label><span>${(envDetails.sdk || 'gradio').charAt(0).toUpperCase() + (envDetails.sdk || 'gradio').slice(1)}</span></div>
                        <div class="config-infra-item"><label>Framework</label><span>${sdkDefaults.framework || 'stable-baselines3'}</span></div>
                        <div class="config-infra-item"><label>Hardware</label><span>${(envDetails.hardware || 'cpu-basic').replace(/-/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase())}</span></div>
                        <div class="config-infra-item"><label>Batch Size</label><span>${hwDefaults.batchSize || 64}</span></div>
                    </div>
                </div>
                ` : ''}

                <div class="model-storage-block">
                    <h4>📦 Model storage & usage</h4>
                    <ul style="padding-left: 1.25rem; margin: 0;">
                        <li><strong>Location:</strong> <code>./models/&lt;algorithm&gt;/</code></li>
                        <li><strong>Download:</strong> <code>GET /models/ppo/&lt;filename&gt;</code></li>
                        <li><strong>Load:</strong> <code>model = PPO.load("model.zip")</code> then <code>model.predict(observation)</code></li>
                    </ul>
                </div>
            </div>
            
            <!-- JSON Upload Tab -->
            <div id="config-json" class="config-tab-content" style="display: none;">
                <div class="form-group">
                    <label>Upload Configuration JSON File:</label>
                    <input type="file" id="config-file-input" accept=".json" onchange="handleConfigFileUpload(event)" />
                    <small>Select a JSON file with your training configuration</small>
                </div>
                <div class="form-group">
                    <label>Or Paste JSON Configuration:</label>
                    <textarea id="config-json-paste" rows="12" placeholder='Paste your JSON configuration here...'>${JSON.stringify({
                        algorithm: 'PPO',
                        num_episodes: 100,
                        max_steps: 1000,
                        dataset_url: null,
                        config: exampleConfig,
                        verifier_config: {
                            type: 'ensemble',
                            verifiers: {
                                clinical: { weights: { risk_improvement: 0.5, vital_stability: 0.5 } },
                                operational: { weights: { pathway_efficiency: 1.0 } },
                                financial: { weights: { cost_effectiveness: 1.0 } },
                                compliance: { weights: { rule_compliance: 1.0 } }
                            }
                        }
                    }, null, 2)}</textarea>
                    <small>Include <code>"dataset_url"</code> field to provide training data URL, and <code>"verifier_config"</code> to configure reward verifiers</small>
                </div>
                <div id="json-validation" style="margin-top: 1rem;"></div>
            </div>
            
            <!-- API Example Tab -->
            <div id="config-api" class="config-tab-content" style="display: none;">
                <h3>API Endpoint:</h3>
                <code style="display: block; background: #f1f5f9; padding: 1rem; border-radius: 6px; margin-bottom: 1rem;">
                    POST ${API_BASE}/train/${envName}
                </code>
                
                <h3>Request Body Example:</h3>
                <pre style="background: #f1f5f9; padding: 1rem; border-radius: 6px; overflow-x: auto;"><code>${JSON.stringify({
                    environment_name: envName,
                    algorithm: 'PPO',
                    num_episodes: 100,
                    max_steps: 1000,
                    dataset_url: 'https://example.com/training_data.csv',
                    config: exampleConfig,
                    verifier_config: {
                        type: 'ensemble',
                        verifiers: {
                            clinical: { weights: { risk_improvement: 0.5, vital_stability: 0.5 } },
                            operational: { weights: { pathway_efficiency: 1.0 } },
                            financial: { weights: { cost_effectiveness: 1.0 } },
                            compliance: { weights: { rule_compliance: 1.0 } }
                        }
                    }
                }, null, 2)}</code></pre>
                
                <h3>Model Information:</h3>
                <div style="background: #f0f9ff; padding: 1rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.9rem;">
                    <p><strong>Model Architecture:</strong> Uses stable-baselines3 with MLP policy network</p>
                    <p><strong>Model Location:</strong> <code>./models/ppo/{envName}_{job_id}.zip</code></p>
                    <p><strong>Download Model:</strong> <code>GET ${API_BASE}/models/ppo/{'{model_filename}'}</code></p>
                </div>
                
                <h3>cURL Example:</h3>
                <pre style="background: #f1f5f9; padding: 1rem; border-radius: 6px; overflow-x: auto;"><code>curl -X POST "${API_BASE}/train/${envName}" \\
  -H "Content-Type: application/json" \\
  -d '${JSON.stringify({
                    environment_name: envName,
                    algorithm: 'PPO',
                    num_episodes: 100,
                    max_steps: 1000,
                    dataset_url: 'https://example.com/training_data.csv',
                    config: exampleConfig,
                    verifier_config: {
                        type: 'ensemble'
                    }
                })}'</code></pre>
                
                <h3>Python Example:</h3>
                <pre style="background: #f1f5f9; padding: 1rem; border-radius: 6px; overflow-x: auto;"><code>import requests
from stable_baselines3 import PPO

# Start training with verifier configuration
response = requests.post(
    "${API_BASE}/train/${envName}",
    json={
        "environment_name": "${envName}",
        "algorithm": "PPO",
        "num_episodes": 100,
        "max_steps": 1000,
        "dataset_url": "https://example.com/training_data.csv",
        "config": ${JSON.stringify(exampleConfig)},
        "verifier_config": {
            "type": "ensemble",
            "verifiers": {
                "clinical": {"weights": {"risk_improvement": 0.5, "vital_stability": 0.5}},
                "operational": {"weights": {"pathway_efficiency": 1.0}},
                "financial": {"weights": {"cost_effectiveness": 1.0}},
                "compliance": {"weights": {"rule_compliance": 1.0}}
            }
        }
    }
)

job_data = response.json()
print(f"Training started: {job_data['job_id']}")

# After training completes, download and use model
# model_response = requests.get(f"${API_BASE}/models/ppo/{model_filename}")
# with open("model.zip", "wb") as f:
#     f.write(model_response.content)
# 
# # Load and use model
# model = PPO.load("model.zip")
# action, _ = model.predict(observation)</code></pre>
            </div>
            
            <div style="margin-top: 2rem; display: flex; gap: 1rem; justify-content: flex-end;">
                <button class="btn btn-secondary" onclick="closeTrainingConfig()">Cancel</button>
                <button class="btn btn-primary" onclick="submitTrainingConfig('${envName}')">🚀 Start Training</button>
            </div>
        </div>
    `;
    document.body.appendChild(configModal);
    configModal.style.display = 'block';
    const systemSelect = document.getElementById('training-software-system');
    if (systemSelect && envSystemsList.length > 0) {
        systemSelect.value = envSystemsList.length === 1 ? envSystemsList[0] : 'all';
        const headerVal = document.getElementById('training-system-header-value');
        if (headerVal) headerVal.textContent = systemSelect.options[systemSelect.selectedIndex].text;
    }
    // Initialize rich verifier cascade if VERIFIER_DATA is available
    if (window.VERIFIER_DATA) {
        _initTrainingVerifier(envName);
    }
    updateModelInfo();
}

function getExampleConfig(envName) {
    const examples = {
        'ImagingOrderPrioritization': {
            queue_size: 15,
            high_urgency_pct: 30,
            avg_order_value: 500,
            ct_availability: 70,
            mri_availability: 60,
            xray_availability: 80
        },
        'TreatmentPathwayOptimization': {
            patient_severity: 'moderate',
            num_conditions: 2,
            initial_risk: 50
        },
        'SepsisEarlyIntervention': {
            sepsis_probability: 60,
            initial_sofa: 8,
            time_since_admission: 2
        },
        'ICUResourceAllocation': {
            icu_beds: 20,
            stepdown_beds: 30,
            patient_queue: 5
        },
        'JiraStatusUpdate': {
            scenario_id: 'in_progress_to_blocked'
        },
        'JiraIssueResolution': {},
        'JiraCommentManagement': {},
        'JiraSubtaskManagement': {
            scenario_id: 'create_subtask'
        }
    };
    if (examples[envName]) return examples[envName];
    // For custom environments, use their generated config template
    var det = environmentDetails[envName];
    if (det && det.configTemplate) return JSON.parse(JSON.stringify(det.configTemplate));
    return { queue_size: 10, resource_availability: 70 };
}

function switchConfigTab(tab) {
    document.querySelectorAll('.config-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.config-tab-content').forEach(c => c.style.display = 'none');

    document.getElementById(`tab-${tab}`).classList.add('active');
    document.getElementById(`config-${tab}`).style.display = 'block';
}

function handleConfigFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const config = JSON.parse(e.target.result);
            document.getElementById('config-json-paste').value = JSON.stringify(config, null, 2);
            validateJSON(JSON.stringify(config, null, 2));
        } catch (error) {
            document.getElementById('json-validation').innerHTML = 
                `<div style="color: var(--danger-color);">❌ Invalid JSON: ${error.message}</div>`;
        }
    };
    reader.readAsText(file);
}

function validateJSON(jsonString) {
    const validationDiv = document.getElementById('json-validation');
    try {
        const parsed = JSON.parse(jsonString);
        validationDiv.innerHTML = `<div style="color: var(--secondary-color);">✅ Valid JSON configuration</div>`;
        return parsed;
    } catch (error) {
        validationDiv.innerHTML = `<div style="color: var(--danger-color);">❌ Invalid JSON: ${error.message}</div>`;
        return null;
    }
}

function closeTrainingConfig() {
    const modal = document.getElementById('training-config-modal');
    if (modal) {
        modal.remove();
    }
}

// ── Training Verifier Cascade (mirrors simulation-console.js) ───────────

var _tvActiveSystem = null;
var _tvActiveTypeFilter = 'all';
var _tvSelectedVerifierId = null;

function _initTrainingVerifier(envName) {
    if (!window.VERIFIER_DATA) return;
    var env = allEnvironments.find(function(e) { return e.name === envName; });
    var category = env ? (env.category || '') : '';
    var system = window.VERIFIER_DATA.getSystemForCategory(category);
    _tvActiveSystem = system || (window.VERIFIER_DATA.systems && window.VERIFIER_DATA.systems[0] ? window.VERIFIER_DATA.systems[0].system : null);
    _tvActiveTypeFilter = 'all';
    _tvSelectedVerifierId = null;
    _tvPopulateSystemDropdown(_tvActiveSystem);
    _tvPopulateVerifierDropdown(_tvActiveSystem, 'all');
    _tvSetupListeners();
    _tvUpdateInfoRow();
}

function _tvPopulateSystemDropdown(activeSystem) {
    var sel = document.getElementById('training-verifier-system-select');
    if (!sel || !window.VERIFIER_DATA) return;
    var groups = window.VERIFIER_DATA.getGroups();
    sel.innerHTML = groups.map(function(g) {
        return '<option value="' + g.system.replace(/"/g, '&quot;') + '"' +
            (g.system === activeSystem ? ' selected' : '') + '>' +
            g.system + ' (' + g.count + ')</option>';
    }).join('');
}

function _tvPopulateVerifierDropdown(system, typeFilter) {
    var sel = document.getElementById('training-verifier-dropdown');
    if (!sel || !window.VERIFIER_DATA) return;
    var verifiers = window.VERIFIER_DATA.getBySystem(system);
    if (typeFilter && typeFilter !== 'all') {
        verifiers = verifiers.filter(function(v) { return v.type === typeFilter; });
    }
    sel.innerHTML = '<option value="">-- Select verifier (' + verifiers.length + ') --</option>';
    verifiers.forEach(function(v) {
        var badge = v.type === 'human-eval' ? ' [HIL]' : '';
        var statusTag = v.status === 'disabled' ? ' (disabled)' : '';
        sel.innerHTML += '<option value="' + v.id.replace(/"/g, '&quot;') + '"' +
            (v.status === 'disabled' ? ' disabled' : '') +
            (v.id === _tvSelectedVerifierId ? ' selected' : '') + '>' +
            v.name + badge + statusTag + '</option>';
    });
}

function _tvSetupListeners() {
    var systemSel = document.getElementById('training-verifier-system-select');
    var verifierSel = document.getElementById('training-verifier-dropdown');
    var typeSel = document.getElementById('training-verifier-type-filter');

    if (systemSel) systemSel.onchange = function() {
        _tvActiveSystem = systemSel.value;
        _tvSelectedVerifierId = null;
        _tvPopulateVerifierDropdown(_tvActiveSystem, typeSel ? typeSel.value : 'all');
        _tvUpdateInfoRow();
    };
    if (typeSel) typeSel.onchange = function() {
        _tvActiveTypeFilter = typeSel.value;
        _tvPopulateVerifierDropdown(_tvActiveSystem, typeSel.value);
    };
    if (verifierSel) verifierSel.onchange = function() {
        _tvSelectedVerifierId = verifierSel.value || null;
        _tvUpdateInfoRow();
        _tvUpdateSubFilter();
        _tvUpdateHilNotice();
    };
}

function _tvUpdateInfoRow() {
    var row = document.getElementById('training-verifier-info-row');
    if (!row) return;
    if (!_tvSelectedVerifierId || !window.VERIFIER_DATA) { row.style.display = 'none'; return; }
    var v = window.VERIFIER_DATA.getById(_tvSelectedVerifierId);
    if (!v) { row.style.display = 'none'; return; }
    row.style.display = '';
    var typeCls = 'vtype-' + v.type;
    row.innerHTML = '<span class="verifier-type-badge ' + typeCls + '">' + v.type + '</span> ' +
        '<span style="color:var(--text-secondary);font-size:0.78rem;">' + v.system + ' &middot; v' + v.version + ' &middot; ' + v.status + '</span>';
}

function _tvUpdateSubFilter() {
    var container = document.getElementById('training-verifier-sub-filter');
    if (!container) return;
    if (!_tvSelectedVerifierId || !window.VERIFIER_DATA) { container.style.display = 'none'; return; }
    var v = window.VERIFIER_DATA.getById(_tvSelectedVerifierId);
    if (!v || !v.subVerifiers || v.subVerifiers.length === 0) { container.style.display = 'none'; return; }
    container.style.display = '';
    container.innerHTML = v.subVerifiers.map(function(sv) {
        return '<label class="sub-verifier-chip' + (sv.enabled ? ' active' : '') + '" title="' + (sv.description || '').replace(/"/g, '&quot;') + '">' +
            '<input type="checkbox"' + (sv.enabled ? ' checked' : '') + ' data-sv-id="' + sv.id + '"> ' + sv.name + '</label>';
    }).join('');
    container.querySelectorAll('input[type="checkbox"]').forEach(function(cb) {
        cb.addEventListener('change', function() {
            var svId = cb.getAttribute('data-sv-id');
            var sv = v.subVerifiers.find(function(s) { return s.id === svId; });
            if (sv) sv.enabled = cb.checked;
            cb.parentElement.classList.toggle('active', cb.checked);
        });
    });
}

function _tvUpdateHilNotice() {
    var notice = document.getElementById('training-hil-notice');
    if (!notice) return;
    if (!_tvSelectedVerifierId || !window.VERIFIER_DATA) { notice.style.display = 'none'; return; }
    var v = window.VERIFIER_DATA.getById(_tvSelectedVerifierId);
    notice.style.display = (v && v.type === 'human-eval') ? '' : 'none';
}

function _tvGetSelectedVerifierConfig() {
    if (!_tvSelectedVerifierId || !window.VERIFIER_DATA) return null;
    var v = window.VERIFIER_DATA.getById(_tvSelectedVerifierId);
    if (!v) return null;
    return {
        type: v.type,
        id: v.id,
        name: v.name,
        system: v.system,
        failurePolicy: v.failurePolicy,
        logic: v.logic
    };
}

function updateModelInfo() {
    const algorithm = document.getElementById('training-algorithm').value;
    const modelInfo = document.getElementById('model-info');
    const modelDescriptions = {
        'PPO': '<strong>Model Architecture:</strong> PPO uses a Multi-Layer Perceptron (MLP) policy network with separate actor and critic networks. Default: [64, 64] hidden layers with tanh activation.',
        'DQN': '<strong>Model Architecture:</strong> DQN uses a deep Q-network with MLP architecture. Default: [64, 64] hidden layers with ReLU activation.',
        'A2C': '<strong>Model Architecture:</strong> A2C uses an MLP policy network with shared feature extractor. Default: [64, 64] hidden layers.',
        'SAC': '<strong>Model Architecture:</strong> SAC uses twin Q-networks and a policy network. Default: [256, 256] hidden layers for better performance.',
        'SLM': '<strong>Jira SLM:</strong> Uses a Small Language Model (e.g. Qwen2.5-0.5B-Instruct) to predict the next workflow tool from state. Recommended for Jira Issue Resolution, Status Update, and Comment Management. Install: pip install transformers accelerate.'
    };
    if (modelInfo) {
        modelInfo.innerHTML = modelDescriptions[algorithm] || modelDescriptions['PPO'];
    }
}

function updateVerifierWeightsVisibility() {
    const verifierType = document.getElementById('training-verifier-type');
    const verifierWeightsGroup = document.getElementById('training-verifier-weights-group');

    if (verifierType && verifierWeightsGroup) {
        const isEnsemble = verifierType.value === 'ensemble';
        const isJiraWorkflow = verifierType.value.startsWith('jira_workflow:');
        verifierWeightsGroup.style.display = (isEnsemble && !isJiraWorkflow) ? 'block' : 'none';
    }
}

// Recommended verifier type and weights by software system (consistent across card, simulation, training)
function getVerifierRecommendationForSystem(system) {
    if (!system || system === 'all') {
        return { type: 'ensemble', weights: { clinical: 0.35, operational: 0.3, financial: 0.2, compliance: 0.15 }, hint: 'Balanced for all systems' };
    }
    const s = system.toLowerCase();
    if (s.includes('epic') || s.includes('cerner') || s.includes('allscripts') || s.includes('meditech')) {
        return { type: 'ensemble', weights: { clinical: 0.45, operational: 0.25, financial: 0.15, compliance: 0.15 }, hint: 'Clinical EHR focus' };
    }
    if (s.includes('philips') || s.includes('ge ')) {
        return { type: 'ensemble', weights: { clinical: 0.3, operational: 0.45, financial: 0.15, compliance: 0.1 }, hint: 'Imaging workflow focus' };
    }
    if (s.includes('change ')) {
        return { type: 'ensemble', weights: { clinical: 0.15, operational: 0.2, financial: 0.45, compliance: 0.2 }, hint: 'Revenue cycle focus' };
    }
    if (s.includes('veeva') || s.includes('iqvia')) {
        return { type: 'ensemble', weights: { clinical: 0.4, operational: 0.2, financial: 0.2, compliance: 0.2 }, hint: 'Clinical trials focus' };
    }
    if (s.includes('health catalyst') || s.includes('innovaccer')) {
        return { type: 'ensemble', weights: { clinical: 0.4, operational: 0.35, financial: 0.15, compliance: 0.1 }, hint: 'Population health focus' };
    }
    if (s.includes('teladoc') || s.includes('amwell')) {
        return { type: 'ensemble', weights: { clinical: 0.35, operational: 0.4, financial: 0.15, compliance: 0.1 }, hint: 'Telehealth focus' };
    }
    if (s.includes('intersystems') || s.includes('orion health')) {
        return { type: 'ensemble', weights: { clinical: 0.25, operational: 0.35, financial: 0.15, compliance: 0.25 }, hint: 'Interoperability focus' };
    }
    return { type: 'ensemble', weights: { clinical: 0.35, operational: 0.3, financial: 0.2, compliance: 0.15 }, hint: 'Balanced default' };
}

function updateTrainingVerifierForSystem() {
    const systemSelect = document.getElementById('training-software-system');
    const verifierTypeSelect = document.getElementById('training-verifier-type');
    const verifierWeightsInput = document.getElementById('training-verifier-weights');
    const verifierHintEl = document.getElementById('training-verifier-hint');
    if (!systemSelect || !verifierTypeSelect) return;
    const system = systemSelect.value;
    const rec = getVerifierRecommendationForSystem(system);
    // Preserve Jira verifier choice when system is Jira and user already selected a Jira verifier
    const isJiraSystem = system && (system.toLowerCase().includes('jira') || system.toLowerCase().includes('atlassian'));
    if (!(isJiraSystem && verifierTypeSelect.value.startsWith('jira_workflow:'))) {
        verifierTypeSelect.value = rec.type;
        if (verifierWeightsInput) verifierWeightsInput.value = JSON.stringify(rec.weights || {}, null, 2);
    }
    updateVerifierWeightsVisibility();
    if (verifierHintEl) verifierHintEl.textContent = rec.hint ? `Suggested for selected system: ${rec.hint}` : '';
}

async function submitTrainingConfig(envName) {
    const activeTab = document.querySelector('.config-tab.active').id.replace('tab-', '');
    let config = null;
    let algorithm = 'PPO';
    let numEpisodes = 100;
    let maxSteps = 1000;
    let datasetUrl = null;
    let verifierConfig = null;
    
    if (activeTab === 'manual') {
        algorithm = document.getElementById('training-algorithm').value;
        numEpisodes = parseInt(document.getElementById('training-episodes').value);
        maxSteps = parseInt(document.getElementById('training-max-steps').value);
        datasetUrl = document.getElementById('training-dataset-url').value.trim() || null;
        
        // Get verifier configuration from rich cascade dropdown
        if (window.VERIFIER_DATA && _tvSelectedVerifierId) {
            verifierConfig = _tvGetSelectedVerifierConfig();
            // Add weights if provided
            var wInput = document.getElementById('training-verifier-weights');
            if (wInput && wInput.value.trim() && verifierConfig) {
                try { verifierConfig.weights = JSON.parse(wInput.value); } catch(e) {}
            }
        } else {
            // Fallback to old dropdown if VERIFIER_DATA not available
            var verifierType = document.getElementById('training-verifier-type');
            if (verifierType && verifierType.value !== 'default') {
                if (verifierType.value.startsWith('jira_workflow:')) {
                    verifierConfig = { type: 'jira_workflow', metadata: { workflow_id: verifierType.value.split(':')[1] } };
                } else {
                    verifierConfig = { type: verifierType.value };
                }
            }
        }

        const configJson = document.getElementById('training-config-json').value.trim();
        if (configJson) {
            try {
                config = JSON.parse(configJson);
            } catch (e) {
                showToast('Invalid JSON in configuration: ' + e.message, 'error');
                return;
            }
        }
        // Merge Jira scenario from dropdown for JiraStatusUpdate
        if (envName === 'JiraStatusUpdate') {
            const scenarioEl = document.getElementById('training-jira-scenario');
            if (scenarioEl) {
                config = config || {};
                config.scenario_id = scenarioEl.value;
            }
        }
        // Merge Jira subtask scenario from dropdown for JiraSubtaskManagement
        if (envName === 'JiraSubtaskManagement') {
            const subtaskScenarioEl = document.getElementById('training-jira-subtask-scenario');
            if (subtaskScenarioEl) {
                config = config || {};
                config.scenario_id = subtaskScenarioEl.value;
            }
        }
    } else if (activeTab === 'json') {
        const jsonPaste = document.getElementById('config-json-paste').value.trim();
        if (!jsonPaste) {
            showToast('Please provide a JSON configuration', 'warning');
            return;
        }
        const parsed = validateJSON(jsonPaste);
        if (!parsed) return;
        
        algorithm = parsed.algorithm || 'PPO';
        numEpisodes = parsed.num_episodes || 100;
        maxSteps = parsed.max_steps || 1000;
        datasetUrl = parsed.dataset_url || null;
        verifierConfig = parsed.verifier_config || null;
        config = parsed.config || parsed;
    }
    
    closeTrainingConfig();
    await startTraining(envName, algorithm, numEpisodes, maxSteps, config, datasetUrl, verifierConfig);
}

async function startTraining(envName, algorithm = 'PPO', numEpisodes = 100, maxSteps = 1000, config = null, datasetUrl = null, verifierConfig = null) {
    try {
        // HIL guard: if verifier is human-eval type, warn user before proceeding
        if (verifierConfig && (verifierConfig.type === 'human_evaluation' || verifierConfig.type === 'human-eval')) {
            const hilConfirmed = confirm(
                '⚠️ Human Evaluation (HIL) Verifier Selected\n\n' +
                'This training job uses a Human-in-the-Loop verifier. After training completes, ' +
                'the job will enter "awaiting_human_eval" status and will NOT be marked as finished ' +
                'until a human reviewer completes the evaluation.\n\n' +
                'You will need to:\n' +
                '1. Wait for training episodes to finish\n' +
                '2. Open the Human Evaluation console\n' +
                '3. Review agent behavior and submit your evaluation\n' +
                '4. Only then will the training job be finalized\n\n' +
                'Do you want to proceed with HIL-gated training?'
            );
            if (!hilConfirmed) {
                showToast('Training cancelled — HIL verifier requires human review commitment.', 'info');
                return;
            }
        }

        const envObj = allEnvironments.find(e => e.name === envName);
        const envCategory = envObj ? (envObj.category || '') : '';
        const requestBody = {
            environment_name: envName,
            algorithm: algorithm,
            num_episodes: numEpisodes,
            max_steps: maxSteps,
            dataset_url: datasetUrl,
            config: config,
            category: envCategory
        };

        // Add verifier config if provided
        if (verifierConfig) {
            requestBody.verifier_config = verifierConfig;
        }

        const response = await fetch(`${API_BASE}/train/${envName}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            let errorMessage = 'Failed to start training';
            try {
                const errorData = JSON.parse(errorText);
                errorMessage = errorData.detail || errorMessage;
            } catch (e) {
                errorMessage = errorText || errorMessage;
            }
            throw new Error(errorMessage);
        }
        
        const data = await response.json();

        // Add the new run to TRAINING_CONFIG so it appears in training lists immediately
        const newRun = {
            id: data.job_id,
            job_id: data.job_id,
            name: data.run_name || (algorithm + ' — ' + formatEnvironmentName(envName)),
            description: algorithm + ' training on ' + formatEnvironmentName(envName),
            status: 'running',
            environment: envName,
            environmentDisplay: formatEnvironmentName(envName),
            category: envCategory,
            model: algorithm,
            algorithm: algorithm,
            progress: 0,
            started: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
            episodes: 0,
            successRate: null,
            avgReward: null,
            baselineReward: null,
            results: null,
            baseline_results: null,
            model_saved: false,
            model_url: null,
            hil_required: verifierConfig && (verifierConfig.type === 'human_evaluation' || verifierConfig.type === 'human-eval'),
            human_evaluations: []
        };
        if (window.TRAINING_CONFIG && window.TRAINING_CONFIG.trainingRuns) {
            window.TRAINING_CONFIG.trainingRuns.unshift(newRun);
        }

        // Refresh the training section in the env detail page if visible
        _refreshTrainingSectionInDetail(envName, envCategory);

        const modelInfo = `
📦 Model Information:
• Model will be saved to: ./models/${algorithm.toLowerCase()}/${envName}_{job_id}.zip
• Download after training: ${API_BASE}/models/${algorithm.toLowerCase()}/{model_filename}
• Load in Python: from stable_baselines3 import ${algorithm}; model = ${algorithm}.load("path/to/model.zip")
• Use for predictions: action, _ = model.predict(observation)
        `.trim();

        const isHilJob = verifierConfig && (verifierConfig.type === 'human_evaluation' || verifierConfig.type === 'human-eval');
        const hilReminder = isHilJob ? `\n⚠️ HIL REQUIRED: This job will pause for human evaluation after training episodes complete. Open /human-eval?job_id=${data.job_id} to review.\n` : '';
        const monitorMessage = `Would you like to open the Training Monitor to track this job's progress?`;
        const openMonitor = confirm(`✅ Training started successfully!\n\n` +
              `Job ID: ${data.job_id}\n` +
              `Status: ${data.status}\n` +
              `Environment: ${formatEnvironmentName(envName)}\n` +
              `Algorithm: ${algorithm}\n` +
              `Episodes: ${numEpisodes}\n` +
              `Max Steps: ${maxSteps}\n` +
              (datasetUrl ? `Dataset: ${datasetUrl}\n` : ``) +
              hilReminder +
              `\n${modelInfo}\n\n` +
              `Monitor progress at: ${API_BASE}/training/${data.job_id}\n\n` +
              `Once training completes, check the job status to get the model download URL.\n\n` +
              monitorMessage);

        if (openMonitor) {
            openTrainingMonitor(data.job_id);
        }
    } catch (error) {
        console.error('Training error:', error);
        showToast('Error starting training: ' + error.message + '. Make sure the API server is running.', 'error');
    }
}

let trainingMonitorInterval = null;

function openTrainingMonitor(jobIdToFocus = null) {
    const monitorBody = document.getElementById('training-monitor-body');
    monitorBody.innerHTML = `
        <h2 style="margin-bottom: 1.5rem;">📊 Training Monitor</h2>
        <div style="margin-bottom: 1rem;">
            <input type="text" id="monitor-job-id" placeholder="Enter Job ID to monitor (optional)" 
                   value="${jobIdToFocus || ''}" 
                   style="width: 100%; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 6px; font-size: 0.9rem;" />
            <button class="btn btn-primary" onclick="loadTrainingJob()" style="margin-top: 0.5rem; width: 100%;">
                🔍 Load Job Status
            </button>
        </div>
        <div id="training-jobs-list" style="margin-top: 2rem;">
            <div style="text-align: center; padding: 2rem; color: var(--text-secondary);">
                Enter a Job ID above or wait for jobs to load...
            </div>
        </div>
    `;
    
    document.getElementById('training-monitor-modal').style.display = 'block';
    
    // Load all training jobs
    loadAllTrainingJobs();
    
    // Auto-refresh every 3 seconds
    if (trainingMonitorInterval) {
        clearInterval(trainingMonitorInterval);
    }
    trainingMonitorInterval = setInterval(loadAllTrainingJobs, 3000);
    
    // If jobIdToFocus is provided, load it immediately
    if (jobIdToFocus) {
        setTimeout(() => loadTrainingJob(jobIdToFocus), 500);
    }
}

async function loadTrainingJob(jobId = null) {
    const jobIdInput = document.getElementById('monitor-job-id');
    const targetJobId = jobId || jobIdInput.value.trim();
    
    if (!targetJobId) {
        showToast('Please enter a Job ID', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/training/${targetJobId}`);
        if (!response.ok) {
            throw new Error('Job not found');
        }
        
        const jobData = await response.json();
        displayTrainingJob(jobData);
    } catch (error) {
        showToast('Error loading job: ' + error.message + '. Make sure the Job ID is correct.', 'error');
    }
}

async function loadAllTrainingJobs() {
    // Note: In a real implementation, you'd have an endpoint to list all jobs
    // For now, we'll show a message that users need to enter a Job ID
    const jobsList = document.getElementById('training-jobs-list');
    if (!jobsList) return;
    
    // If there's a job ID in the input, try to load it
    const jobIdInput = document.getElementById('monitor-job-id');
    if (jobIdInput && jobIdInput.value.trim()) {
        try {
            const response = await fetch(`${API_BASE}/training/${jobIdInput.value.trim()}`);
            if (response.ok) {
                const jobData = await response.json();
                displayTrainingJob(jobData);
                return;
            }
        } catch (e) {
            // Job not found, continue
        }
    }
    
    // Show placeholder if no job is being monitored
    if (!jobsList.querySelector('.training-job-card')) {
        jobsList.innerHTML = `
            <div style="text-align: center; padding: 2rem; color: var(--text-secondary);">
                <p>Enter a Job ID above to monitor a specific training job.</p>
                <p style="font-size: 0.85rem; margin-top: 0.5rem;">The monitor will auto-refresh every 3 seconds.</p>
            </div>
        `;
    }
}

function displayTrainingJob(jobData) {
    const jobsList = document.getElementById('training-jobs-list');
    if (!jobsList) return;
    
    const statusColors = {
        'running': '#3b82f6',
        'completed': '#10b981',
        'failed': '#ef4444',
        'pending': '#f59e0b',
        'awaiting_human_eval': '#d97706'
    };
    
    const statusIcons = {
        'running': '🔄',
        'completed': '✅',
        'failed': '❌',
        'pending': '⏳',
        'awaiting_human_eval': '👤'
    };
    
    const statusColor = statusColors[jobData.status] || '#64748b';
    const statusIcon = statusIcons[jobData.status] || '📊';
    
    const progressBar = jobData.status === 'running' ? `
        <div style="background: #e2e8f0; border-radius: 10px; height: 20px; margin: 0.5rem 0; overflow: hidden;">
            <div style="background: ${statusColor}; height: 100%; width: ${jobData.progress || 0}%; transition: width 0.3s; display: flex; align-items: center; justify-content: center; color: white; font-size: 0.75rem; font-weight: 600;">
                ${jobData.progress || 0}%
            </div>
        </div>
    ` : '';
    
    const baseline = jobData.baseline_results;
    const results = jobData.results;
    const hasComparison = baseline && results && typeof baseline.mean_reward === 'number' && typeof results.mean_reward === 'number';
    const comparisonSection = hasComparison ? (() => {
        const preMean = baseline.mean_reward;
        const postMean = results.mean_reward;
        const delta = postMean - preMean;
        const deltaPct = preMean !== 0 ? ((delta / Math.abs(preMean)) * 100).toFixed(1) : (delta !== 0 ? (delta > 0 ? '+' : '') : '0');
        const humanDecision = jobData.human_eval_decision ? (jobData.human_eval_decision === 'yes' ? '✅ Human approved' : '❌ Human rejected') : (jobData.status === 'awaiting_human_eval' ? '⏳ Pending human evaluation' : '');
        return `
        <div style="background: #f5f3ff; padding: 1rem; border-radius: 6px; margin-top: 1rem; border-left: 4px solid #7c3aed;">
            <h4 style="margin-bottom: 0.75rem; color: #5b21b6;">📊 Pre vs Post Training</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; font-size: 0.9rem;">
                <div style="padding: 0.75rem; background: rgba(255,255,255,0.7); border-radius: 6px;">
                    <strong style="color: var(--text-secondary); font-size: 0.8rem;">Pre-training (baseline)</strong>
                    <div style="margin-top: 0.35rem;">Mean reward: <strong>${preMean.toFixed(3)}</strong></div>
                    <div>Episodes: ${baseline.episodes || '—'}</div>
                </div>
                <div style="padding: 0.75rem; background: rgba(255,255,255,0.7); border-radius: 6px;">
                    <strong style="color: var(--text-secondary); font-size: 0.8rem;">Post-training</strong>
                    <div style="margin-top: 0.35rem;">Mean reward: <strong>${postMean.toFixed(3)}</strong></div>
                    <div>Episodes: ${results.episodes_completed ?? results.total_episodes ?? '—'}</div>
                    ${humanDecision ? `<div style="margin-top: 0.5rem; font-size: 0.85rem;">${humanDecision}</div>` : ''}
                </div>
            </div>
            <div style="margin-top: 0.75rem; padding: 0.5rem 0.75rem; background: rgba(124,58,237,0.1); border-radius: 6px; font-size: 0.85rem;">
                <strong>Change:</strong> ${delta >= 0 ? '+' : ''}${delta.toFixed(3)} mean reward (${deltaPct}% vs baseline)
            </div>
            ${jobData.baseline_rollout_id && jobData.trained_rollout_id ? `
            <div style="margin-top: 0.75rem;">
                <button class="btn btn-primary" style="font-size:0.85rem;" onclick="openRolloutComparisonFromJob('${jobData.job_id}', '${jobData.environment_name}')">
                    🔍 View Rollout Comparison
                </button>
            </div>` : ''}
        </div>
    `;
    })() : '';

    const resultsSection = results ? (() => {
        const meanR = results.mean_reward;
        const maxR = results.max_reward;
        const minR = results.min_reward;
        const eps = results.total_episodes || jobData.num_episodes || 0;
        const completed = results.episodes_completed ?? eps;
        
        let summaryText = '';
        if (typeof meanR === 'number') {
            const spread = (typeof maxR === 'number' && typeof minR === 'number') ? (maxR - minR) : null;
            summaryText = 'Mean reward (' + meanR.toFixed(2) + ') is the average return per episode — higher means the agent learned better policies. ';
            if (typeof maxR === 'number') summaryText += 'Max (' + maxR.toFixed(2) + ') is the best single episode. ';
            if (typeof minR === 'number') summaryText += 'Min (' + minR.toFixed(2) + ') is the worst. ';
            if (spread !== null) summaryText += 'A narrow spread suggests stable learning; a wide spread means more variance. ';
            summaryText += 'Episodes (' + completed + '/' + eps + ') shows how many runs completed. More episodes generally improve learning.';
        } else {
            summaryText = 'Run training to see reward metrics. Mean reward indicates average performance per episode; max/min show best and worst runs.';
        }
        
        return `
        <div style="background: #f0f9ff; padding: 1rem; border-radius: 6px; margin-top: 1rem;">
            <h4 style="margin-bottom: 0.75rem; color: var(--primary-color);">📈 Training Results</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; font-size: 0.9rem;">
                <div>
                    <strong>Mean Reward:</strong><br/>
                    <span style="color: var(--primary-color); font-size: 1.1rem; font-weight: 600;">
                        ${results.mean_reward?.toFixed(2) ?? 'N/A'}
                    </span>
                </div>
                <div>
                    <strong>Max Reward:</strong><br/>
                    <span style="color: var(--secondary-color); font-size: 1.1rem; font-weight: 600;">
                        ${results.max_reward?.toFixed(2) ?? 'N/A'}
                    </span>
                </div>
                <div>
                    <strong>Min Reward:</strong><br/>
                    <span style="color: var(--text-secondary); font-size: 1.1rem; font-weight: 600;">
                        ${results.min_reward?.toFixed(2) ?? 'N/A'}
                    </span>
                </div>
                <div>
                    <strong>Episodes:</strong><br/>
                    <span style="color: var(--text-primary); font-size: 1.1rem; font-weight: 600;">
                        ${completed} / ${results.total_episodes || jobData.num_episodes || 'N/A'}
                    </span>
                </div>
            </div>
            <div style="margin-top: 0.75rem; padding: 0.6rem 0.75rem; background: rgba(37,99,235,0.08); border-radius: 6px; font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5;">
                <strong style="color: var(--text-primary);">Why these values:</strong> ${summaryText}
            </div>
        </div>
    `;
    })() : '';
    
    const modelSection = ((jobData.status === 'completed' || jobData.status === 'awaiting_human_eval') && jobData.model_url) ? `
        <div style="background: #dcfce7; padding: 1rem; border-radius: 6px; margin-top: 1rem; border-left: 4px solid var(--secondary-color);">
            <h4 style="margin-bottom: 0.75rem; color: #166534;">📦 Trained Model Available</h4>
            <p style="font-size: 0.9rem; margin-bottom: 0.75rem; color: var(--text-secondary);">
                Your model has been trained and is ready for download.
                ${jobData.human_eval_decision ? ` <strong>Model output is final after human evaluation: ${jobData.human_eval_decision === 'yes' ? 'Approved' : 'Rejected'}.</strong>` : (jobData.status === 'awaiting_human_eval' ? ' Complete human evaluation to finalize.' : '')}
            </p>
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <a href="${API_BASE}${jobData.model_url}" class="btn btn-primary" download style="text-decoration: none;">
                    ⬇️ Download Model
                </a>
                <button class="btn btn-outline" onclick="copyModelInfo('${jobData.job_id}', '${jobData.algorithm}', '${jobData.model_url}')">
                    📋 Copy Model Info
                </button>
            </div>
            <div style="margin-top: 0.75rem; padding: 0.75rem; background: white; border-radius: 4px; font-size: 0.85rem; font-family: monospace; color: var(--text-secondary);">
                <strong>Model Path:</strong> ${jobData.model_path || 'N/A'}<br/>
                <strong>Download URL:</strong> ${API_BASE}${jobData.model_url}
            </div>
        </div>
    ` : '';

    const subtaskSection = (jobData.status === 'completed'
        && jobData.environment_name === 'JiraSubtaskManagement'
        && jobData.subtask_log_url) ? `
        <div style="background: #f5f3ff; padding: 1rem; border-radius: 6px; margin-top: 1rem; border-left: 4px solid #9d7b8f;">
            <h4 style="margin-bottom: 0.75rem; color: #1d4ed8;">🧾 Subtask Action Log</h4>
            <p style="font-size: 0.9rem; margin-bottom: 0.75rem; color: var(--text-secondary);">
                Download a JSON log of episodes where the agent created Jira subtasks
                (<code>create_subtask</code>) during training.
            </p>
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <a href="${API_BASE}${jobData.subtask_log_url}" class="btn btn-outline" download style="text-decoration: none;">
                    ⬇️ Download Subtask Log
                </a>
            </div>
            <div style="margin-top: 0.75rem; padding: 0.75rem; background: white; border-radius: 4px; font-size: 0.85rem; font-family: monospace; color: var(--text-secondary);">
                <strong>Log URL:</strong> ${API_BASE}${jobData.subtask_log_url}
            </div>
        </div>
    ` : '';
    
    const errorSection = (jobData.status === 'failed' && jobData.error) ? `
        <div style="background: #fee2e2; padding: 1rem; border-radius: 6px; margin-top: 1rem; border-left: 4px solid var(--danger-color);">
            <h4 style="margin-bottom: 0.75rem; color: var(--danger-color);">❌ Training Error</h4>
            <pre style="background: white; padding: 0.75rem; border-radius: 4px; font-size: 0.85rem; overflow-x: auto; color: var(--text-primary);">${jobData.error}</pre>
        </div>
    ` : '';

    const lastEval = jobData.last_human_evaluation;
    const awaitingHumanEval = jobData.status === 'awaiting_human_eval';
    const humanEvalSection = (awaitingHumanEval || lastEval || true) ? `
        <div id="job-card-human-eval" style="background: #fef3c7; padding: 1rem; border-radius: 6px; margin-top: 1rem; border-left: 4px solid #d97706; ${awaitingHumanEval ? 'border: 2px solid #d97706;' : ''}">
            <h4 style="margin-bottom: 0.75rem; color: #92400e;">👤 Human Evaluation ${awaitingHumanEval ? '— Required to complete training' : ''}</h4>
            <p style="font-size: 0.9rem; margin-bottom: 0.75rem; color: var(--text-secondary);">
                ${awaitingHumanEval ? 'Training is finished. Open the Human Evaluation console to approve or reject this run. Training will be marked complete after you submit your evaluation.' : 'Record your approval or rejection for this run (for RLHF / model selection).'}
            </p>
            ${lastEval ? `
            <div style="margin-bottom: 0.75rem; padding: 0.5rem; background: white; border-radius: 4px; font-size: 0.85rem;">
                <strong>Last evaluation:</strong> ${lastEval.decision === 'yes' ? '✅ Yes' : '❌ No'}
                ${lastEval.comments ? ` — ${(lastEval.comments || '').replace(/</g, '&lt;').substring(0, 80)}${(lastEval.comments || '').length > 80 ? '…' : ''}` : ''}
                <br/><span style="color: var(--text-secondary);">${lastEval.timestamp ? new Date(lastEval.timestamp).toLocaleString() : ''}</span>
                ${(jobData.human_evaluations && jobData.human_evaluations.length > 1) ? `<br/><span style="font-size: 0.8rem;">Total evaluations: ${jobData.human_evaluations.length}</span>` : ''}
            </div>
            ` : ''}
            <a href="${API_BASE}/static/human-eval.html?job_id=${jobData.job_id}" target="_blank" rel="noopener" class="btn btn-primary" style="display: inline-block; text-decoration: none;">
                ${lastEval ? '✏️ Open Human Evaluation' : (awaitingHumanEval ? '👤 Complete Human Evaluation' : '👤 Open Human Evaluation')}
            </a>
        </div>
    ` : '';

    const ctx = jobData.slm_training_context || {};
    const ex = jobData.slm_explainability || {};
    const slmExplainabilitySection = (jobData.algorithm === 'SLM') ? `
        <div style="background: #f0f9ff; padding: 1rem; border-radius: 6px; margin-top: 1rem; border-left: 4px solid #0284c7;">
            <h4 style="margin-bottom: 0.75rem; color: #0369a1;">🔍 SLM Explainability</h4>
            ${(ctx.description || jobData.environment_name) ? `
            <div style="margin-bottom: 1rem;">
                <strong style="color: var(--text-primary);">What the model is training on</strong>
                <p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.35rem;">${ctx.description || 'The Jira SLM receives the current workflow state (step index, last tool used) as a short text prompt and predicts the next tool name. Actions: 0 = correct next tool (rewarded), 1..n = wrong tool index.'}</p>
                ${ctx.observation_space ? `
                <div style="margin-top: 0.5rem; font-size: 0.85rem;">
                    <strong>Observation:</strong> ${ctx.observation_space.features ? ctx.observation_space.features.join('; ') : '—'}<br/>
                    <strong>Tool order:</strong> ${(ctx.observation_space && ctx.observation_space.expected_tool_order) ? ctx.observation_space.expected_tool_order.join(' → ') : '—'}
                </div>` : ''}
                ${ctx.prompt_format ? `<div style="margin-top: 0.5rem; font-size: 0.85rem;"><strong>Prompt format:</strong> <code style="background: rgba(255,255,255,0.7); padding: 0.2rem 0.4rem; border-radius: 4px;">${ctx.prompt_format}</code></div>` : ''}
                ${ctx.action_space ? `<div style="margin-top: 0.5rem; font-size: 0.85rem;"><strong>Actions:</strong> 0 = correct next tool; 1..n = wrong tool index</div>` : ''}
                ${ctx.model_id ? `<div style="margin-top: 0.35rem; font-size: 0.8rem; color: var(--text-secondary);">Model: ${ctx.model_id}${ctx.uses_slm ? ' (loaded)' : ' (rule-based fallback)'}</div>` : ''}
            </div>` : ''}
            ${ex.prompt ? `
            <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid rgba(2,132,199,0.3);">
                <strong style="color: var(--text-primary);">Example step (episode ${ex.episode || '?'}, step ${ex.step || '?'})</strong>
                <div style="margin-top: 0.35rem; font-size: 0.85rem;"><strong>Prompt sent to model:</strong><br/><code style="display: block; background: rgba(255,255,255,0.8); padding: 0.5rem; border-radius: 4px; margin-top: 0.25rem; word-break: break-all;">${(ex.prompt || '').replace(/</g, '&lt;')}</code></div>
                ${ex.raw_output != null ? `<div style="margin-top: 0.35rem; font-size: 0.85rem;"><strong>Model output:</strong> <code style="background: rgba(255,255,255,0.8); padding: 0.2rem 0.4rem;">${String(ex.raw_output).replace(/</g, '&lt;')}</code></div>` : ''}
                <div style="margin-top: 0.35rem; font-size: 0.85rem;"><strong>Parsed tool:</strong> ${ex.parsed_tool || '—'} | <strong>Correct next:</strong> ${ex.correct_next || '—'} | <strong>Action:</strong> ${ex.action}</div>
                ${ex.explanation ? `<div style="margin-top: 0.35rem; font-size: 0.85rem; color: var(--text-secondary);">${ex.explanation}</div>` : ''}
            </div>` : ''}
        </div>
    ` : '';

    jobsList.innerHTML = `
        <div class="training-job-card" style="background: white; border: 2px solid ${statusColor}; border-radius: 8px; padding: 1.5rem; margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                <div>
                    <h3 style="margin-bottom: 0.5rem; color: var(--text-primary);">
                        ${formatEnvironmentName(jobData.environment_name || 'Unknown')}
                    </h3>
                    <div style="display: flex; gap: 1rem; flex-wrap: wrap; font-size: 0.85rem; color: var(--text-secondary);">
                        <span><strong>Job ID:</strong> <code style="background: #f1f5f9; padding: 0.25rem 0.5rem; border-radius: 4px;">${jobData.job_id}</code></span>
                        <span><strong>Algorithm:</strong> ${jobData.algorithm || 'N/A'}</span>
                        <span><strong>Status:</strong> <span style="color: ${statusColor}; font-weight: 600;">${(jobData.status === 'awaiting_human_eval' ? 'AWAITING HUMAN EVALUATION' : jobData.status).toUpperCase()}</span></span>
                    </div>
                </div>
                <button class="btn btn-outline" onclick="refreshJobStatus('${jobData.job_id}')" style="padding: 0.5rem 1rem; font-size: 0.85rem;">
                    🔄 Refresh
                </button>
            </div>
            
            ${progressBar}
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem; font-size: 0.9rem;">
                <div>
                    <strong>Episodes:</strong> ${jobData.num_episodes || 'N/A'}
                </div>
                ${jobData.dataset_url ? `<div><strong>Dataset:</strong> <a href="${jobData.dataset_url}" target="_blank" style="color: var(--primary-color);">View</a></div>` : ''}
                <div>
                    <strong>Started:</strong> ${new Date().toLocaleString()}
                </div>
            </div>
            
            ${comparisonSection}
            ${resultsSection}
            ${slmExplainabilitySection}
            ${modelSection}
            ${subtaskSection}
            ${errorSection}
            ${humanEvalSection}
        </div>
    `;
}

async function refreshJobStatus(jobId) {
    try {
        const response = await fetch(`${API_BASE}/training/${jobId}`);
        if (!response.ok) throw new Error('Job not found');
        const jobData = await response.json();
        displayTrainingJob(jobData);
    } catch (error) {
        showToast('Error refreshing job: ' + error.message, 'error');
    }
}

function copyModelInfo(jobId, algorithm, modelUrl) {
    const modelInfo = `
Training Job: ${jobId}
Algorithm: ${algorithm}
Model URL: ${API_BASE}${modelUrl}

Python Usage:
from stable_baselines3 import ${algorithm}
model = ${algorithm}.load("path/to/downloaded/model.zip")
action, _ = model.predict(observation)
    `.trim();
    
    navigator.clipboard.writeText(modelInfo).then(() => {
        showToast('Model information copied to clipboard!', 'success');
    }).catch(() => {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = modelInfo;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast('Model information copied to clipboard!', 'success');
    });
}

// Clean up interval when modal is closed
function closeTrainingMonitor() {
    if (trainingMonitorInterval) {
        clearInterval(trainingMonitorInterval);
        trainingMonitorInterval = null;
    }
    closeModal('training-monitor-modal');
}

window.closeTrainingMonitor = closeTrainingMonitor;

// Make functions available globally
window.testEnvironment = testEnvironment;
window.startTraining = startTraining;
window.openTrainingConfig = openTrainingConfig;
window.closeTrainingConfig = closeTrainingConfig;
window.switchConfigTab = switchConfigTab;
window.handleConfigFileUpload = handleConfigFileUpload;
window.submitTrainingConfig = submitTrainingConfig;
window.openHelpSection = openHelpSection;
window.closeModal = closeModal;
window.updateModelInfo = updateModelInfo;
window.updateVerifierWeightsVisibility = updateVerifierWeightsVisibility;
window.openTrainingMonitor = openTrainingMonitor;
window.loadTrainingJob = loadTrainingJob;
window.refreshJobStatus = refreshJobStatus;
window.copyModelInfo = copyModelInfo;
window.toggleSave = toggleSave;

// ── Rollout Comparison from Training Monitor ────────────────────

async function openRolloutComparisonFromJob(jobId, envName) {
    var jobsList = document.getElementById('training-jobs-list');
    if (!jobsList) return;
    jobsList.innerHTML = '<div style="text-align:center;padding:2rem;color:var(--text-secondary);">Loading rollout comparison...</div>';

    try {
        var resp = await fetch(API_BASE + '/api/rollout-comparison/' + encodeURIComponent(envName) + '?job_id=' + encodeURIComponent(jobId));
        if (!resp.ok) throw new Error('Failed to load comparison data');
        var data = await resp.json();

        var backBtn = '<button class="btn btn-secondary btn-small" onclick="loadTrainingJob(\'' + jobId + '\')" style="margin-bottom:1rem;">← Back to job</button>';
        jobsList.innerHTML = backBtn + '<div id="rc-training-container"></div>';

        var container = document.getElementById('rc-training-container');
        if (window.renderRolloutComparison) {
            window.renderRolloutComparison(container, data.baseline, data.trained, {
                scenarioName: formatEnvironmentName(envName),
                envName: envName,
                trainedLabel: 'Trained Policy (' + ((data.trained && data.trained.policy_name) || 'PPO') + (data.trained && data.trained.checkpoint_label ? ' \u00b7 ' + data.trained.checkpoint_label : '') + ')'
            });
        } else {
            container.innerHTML = '<p style="color:var(--text-secondary);">Rollout comparison component not loaded.</p>';
        }
    } catch (err) {
        jobsList.innerHTML = '<div style="padding:1rem;"><button class="btn btn-secondary btn-small" onclick="loadTrainingJob(\'' + jobId + '\')" style="margin-bottom:1rem;">← Back to job</button><p style="color:#ef4444;">Error loading comparison: ' + err.message + '</p></div>';
    }
}
window.openRolloutComparisonFromJob = openRolloutComparisonFromJob;

// ─── Add Environment Page Functions ──────────────────────────────────
function showAddEnvironmentPage() {
    document.getElementById('catalog-container').style.display = 'none';
    document.getElementById('env-detail-page').style.display = 'none';
    document.getElementById('add-env-page').style.display = 'block';
    window.scrollTo(0, 0);
    renderSdkTemplateGrid('gradio');
}
window.showAddEnvironmentPage = showAddEnvironmentPage;

function closeAddEnvironmentPage() {
    document.getElementById('add-env-page').style.display = 'none';
    document.getElementById('catalog-container').style.display = 'block';
}
window.closeAddEnvironmentPage = closeAddEnvironmentPage;

function switchAddEnvTab(tab) {
    var tabs = document.querySelectorAll('.add-env-tab');
    tabs.forEach(function(t) {
        t.classList.toggle('active', t.getAttribute('data-tab') === tab);
    });
    document.getElementById('add-env-panel-form').style.display = (tab === 'form') ? 'block' : 'none';
    document.getElementById('add-env-panel-import').style.display = (tab === 'import') ? 'block' : 'none';
}
window.switchAddEnvTab = switchAddEnvTab;

// ─── Segmented control selector ───
function selectEnvSegment(btn, group) {
    var seg = btn.parentElement;
    seg.querySelectorAll('.add-env-seg-btn').forEach(function(c) { c.classList.remove('selected'); });
    btn.classList.add('selected');
    var hiddenId = (group === 'sdk') ? 'add-env-sdk' : 'add-env-hardware';
    var hidden = document.getElementById(hiddenId);
    if (hidden) hidden.value = btn.getAttribute('data-value');
    if (group === 'sdk') renderSdkTemplateGrid(btn.getAttribute('data-value'));
}
window.selectEnvSegment = selectEnvSegment;

// ─── SDK Template (dropdown select) ───
function renderSdkTemplateGrid(sdkValue) {
    var container = document.getElementById('add-env-template-container');
    if (!container) return;
    container.innerHTML = '';
    var hiddenTemplate = document.getElementById('add-env-template');
    if (hiddenTemplate) hiddenTemplate.value = 'blank';

    if (sdkValue === 'custom') {
        container.innerHTML = _renderTerraformImportArea();
        container.style.display = 'block';
        var tfTextarea = document.getElementById('add-env-terraform-content');
        if (tfTextarea) tfTextarea.value = DEFAULT_TERRAFORM_TEMPLATE;
        return;
    }

    var templates = SDK_TEMPLATES[sdkValue];
    if (!templates || templates.length === 0) { container.style.display = 'none'; return; }

    var label = document.createElement('label');
    label.textContent = 'Template';
    label.className = 'add-env-inline-label';
    label.setAttribute('for', 'add-env-template-select');

    var select = document.createElement('select');
    select.id = 'add-env-template-select';
    select.className = 'add-env-template-select';
    var defaultOpt = document.createElement('option');
    defaultOpt.value = '';
    defaultOpt.textContent = '-- select --';
    defaultOpt.disabled = true;
    defaultOpt.selected = true;
    select.appendChild(defaultOpt);
    templates.forEach(function(tmpl) {
        var opt = document.createElement('option');
        opt.value = tmpl.id;
        opt.textContent = tmpl.name;
        select.appendChild(opt);
    });
    select.onchange = function() {
        if (hiddenTemplate) hiddenTemplate.value = select.value;
    };

    container.appendChild(label);
    container.appendChild(select);
    container.style.display = 'block';
}
window.renderSdkTemplateGrid = renderSdkTemplateGrid;

function _renderTerraformImportArea() {
    return '' +
        '<label class="add-env-template-label">Terraform Template</label>' +
        '<div class="add-env-terraform-area">' +
            '<div class="add-env-terraform-info">' +
                '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--primary-color)" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>' +
                '<span>Import your own Terraform template (.tf) or use the built-in default template below.</span>' +
            '</div>' +
            '<div class="add-env-terraform-actions">' +
                '<label class="btn btn-outline btn-small add-env-terraform-upload-btn">' +
                    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>' +
                    ' Import .tf file' +
                    '<input type="file" id="add-env-terraform-file" accept=".tf,.tf.json" style="display:none;" onchange="handleTerraformFileImport(this)">' +
                '</label>' +
                '<button type="button" class="btn btn-outline btn-small" onclick="resetTerraformToDefault()">Reset to Default</button>' +
            '</div>' +
            '<textarea id="add-env-terraform-content" class="add-env-terraform-editor" rows="12" spellcheck="false" placeholder="Paste or import your Terraform template..."></textarea>' +
        '</div>';
}

function handleTerraformFileImport(input) {
    if (!input.files || !input.files[0]) return;
    var file = input.files[0];
    var reader = new FileReader();
    reader.onload = function(e) {
        var tfTextarea = document.getElementById('add-env-terraform-content');
        if (tfTextarea) tfTextarea.value = e.target.result;
        if (window.showToast) showToast('Terraform template "' + file.name + '" loaded.', 'success');
    };
    reader.readAsText(file);
}
window.handleTerraformFileImport = handleTerraformFileImport;

function resetTerraformToDefault() {
    var tfTextarea = document.getElementById('add-env-terraform-content');
    if (tfTextarea) tfTextarea.value = DEFAULT_TERRAFORM_TEMPLATE;
    if (window.showToast) showToast('Reset to default template.', 'info');
}
window.resetTerraformToDefault = resetTerraformToDefault;

// ─── Domain-to-category mapping for new environments ───
var _categoryToDomain = {
    jira: 'dev-sim', clinical: 'med-sim', imaging: 'med-sim', revenue_cycle: 'fin-sim',
    hr_payroll: 'hr-sim', population_health: 'med-sim', clinical_trials: 'med-sim',
    hospital_operations: 'med-sim', telehealth: 'med-sim', interoperability: 'med-sim',
    cross_workflow: 'med-sim', financial: 'fin-sim'
};

function _addEnvironmentToGrid(envData) {
    // Add to allEnvironments array so filters work
    allEnvironments.push(envData);
    // Re-run current filter to include the new environment in the grid
    var searchInput = document.getElementById('search-input');
    var searchTerm = searchInput ? searchInput.value.trim() : '';
    var activeCategory = 'all';
    var activeBtn = document.querySelector('.filter-btn.active');
    if (activeBtn) activeCategory = activeBtn.getAttribute('data-category') || 'all';
    filterEnvironments(searchTerm, activeCategory);
    // Update total count
    var totalEl = document.getElementById('total-envs');
    if (totalEl) totalEl.textContent = allEnvironments.length;
}

function submitAddEnvironment(event) {
    event.preventDefault();

    var name = document.getElementById('add-env-name').value.trim();
    var owner = document.getElementById('add-env-owner').value.trim() || 'centific';
    var desc = document.getElementById('add-env-desc').value.trim();
    var license = document.getElementById('add-env-license').value;
    var category = 'custom';
    var system = 'Custom';
    var sdk = document.getElementById('add-env-sdk').value;
    var hardware = document.getElementById('add-env-hardware').value;
    var template = document.getElementById('add-env-template') ? document.getElementById('add-env-template').value : 'blank';
    var terraformContent = '';
    if (sdk === 'custom') {
        var tfEl = document.getElementById('add-env-terraform-content');
        terraformContent = tfEl ? tfEl.value : '';
    }
    var stateFeatures = 10;
    var actionSpace = 4;
    var actionType = 'Discrete';

    if (!name) {
        if (window.showToast) showToast('Please enter an environment name.', 'error');
        else alert('Please enter an environment name.');
        return;
    }

    var newEnv = {
        name: name,
        description: desc || 'Custom environment created by ' + owner,
        category: category,
        system: system,
        domain: _categoryToDomain[category] || 'med-sim',
        sdk: sdk,
        hardware: hardware,
        template: template,
        terraformTemplate: terraformContent || null,
        stateFeatures: stateFeatures,
        actionSpace: actionSpace,
        actionType: actionType,
        actions: [],
        owner: owner,
        license: license,
        source: 'custom'
    };

    console.log('[AddEnvironment] Creating environment:', newEnv);

    var generated = generateEnvironmentDetails(newEnv);
    environmentDetails[name] = generated;
    console.log('[AddEnvironment] Generated environmentDetails for:', name, generated);

    _addEnvironmentToGrid(newEnv);

    // Persist to backend (auto-classifies on save) then update local state
    fetch(API_BASE + '/api/custom-environments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newEnv)
    }).then(function() {
        // Fetch classification to update local grid/details
        return fetch(API_BASE + '/api/classify-environment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, description: desc || '', sdk: sdk, template: template })
        });
    }).then(function(r) { return r && r.ok ? r.json() : null; })
    .then(function(cls) {
        if (cls && cls.category) {
            newEnv.category = cls.category;
            newEnv.system = cls.system;
            newEnv.domain = cls.domain;
            newEnv.workflow = cls.workflow;
            newEnv.tags = cls.tags;
            environmentDetails[name] = generateEnvironmentDetails(newEnv);
            // Refresh catalog grid to show updated tags
            if (typeof filterEnvironments === 'function') {
                var searchVal = document.getElementById('env-search') ? document.getElementById('env-search').value : '';
                var catVal = document.querySelector('.catalog-tab.active') ? document.querySelector('.catalog-tab.active').getAttribute('data-category') || 'all' : 'all';
                filterEnvironments(searchVal, catVal);
            }
            console.log('[AddEnvironment] Classified:', name, cls);
        }
    }).catch(function(err) { console.warn('[AddEnvironment] Backend persist/classify failed:', err); });

    if (window.showToast) showToast('Environment "' + owner + '/' + name + '" created successfully!', 'success');

    // Reset form
    document.getElementById('add-env-form').reset();
    document.getElementById('add-env-owner').value = 'centific';
    document.getElementById('add-env-sdk').value = 'gradio';
    document.getElementById('add-env-hardware').value = 'cpu-basic';
    document.querySelectorAll('#add-env-sdk-seg .add-env-seg-btn').forEach(function(c, i) {
        c.classList.toggle('selected', i === 0);
    });
    document.querySelectorAll('#add-env-hw-seg .add-env-seg-btn').forEach(function(c, i) {
        c.classList.toggle('selected', i === 0);
    });
    renderSdkTemplateGrid('gradio');

    setTimeout(function() { closeAddEnvironmentPage(); }, 800);
}
window.submitAddEnvironment = submitAddEnvironment;

// ─── HuggingFace Import Functions ───
var _hfImportedMeta = null;

function _parseHuggingFaceUrl(url) {
    // Parse: https://huggingface.co/spaces/org/repo-name
    var match = url.match(/huggingface\.co\/spaces\/([^\/]+)\/([^\/\?#]+)/);
    if (match) return { owner: match[1], repo: match[2] };
    return null;
}

function previewHuggingFaceSpace() {
    var urlInput = document.getElementById('add-env-import-path');
    var url = urlInput ? urlInput.value.trim() : '';
    if (!url) {
        if (window.showToast) showToast('Please enter a HuggingFace Environment URL.', 'error');
        return;
    }
    var parsed = _parseHuggingFaceUrl(url);
    if (!parsed) {
        if (window.showToast) showToast('Invalid HuggingFace Environment URL. Expected format: https://huggingface.co/spaces/owner/env-name', 'error');
        return;
    }

    // Show loading status
    var statusEl = document.getElementById('add-env-import-status');
    var statusText = document.getElementById('add-env-import-status-text');
    if (statusEl) statusEl.style.display = 'block';
    if (statusText) statusText.textContent = 'Fetching environment metadata from HuggingFace...';

    // Call backend API to fetch space metadata
    fetch(API_BASE + '/api/huggingface/space-info?owner=' + encodeURIComponent(parsed.owner) + '&repo=' + encodeURIComponent(parsed.repo))
        .then(function(res) {
            if (!res.ok) throw new Error('Failed to fetch space info (HTTP ' + res.status + ')');
            return res.json();
        })
        .then(function(data) {
            _hfImportedMeta = data;
            if (statusEl) statusEl.style.display = 'none';
            _showHFPreview(data, url);
            // Show step 2
            var step2 = document.getElementById('import-step-details');
            if (step2) step2.style.display = 'block';
            // Auto-fill name from repo slug
            var parsed2 = _parseHuggingFaceUrl(url);
            if (parsed2) {
                var nameInput = document.getElementById('add-env-import-name');
                if (nameInput && !nameInput.value) nameInput.value = parsed2.repo;
            }
        })
        .catch(function(err) {
            if (statusEl) statusEl.style.display = 'none';
            console.error('[HF Import] Error:', err);
            if (window.showToast) showToast('Error fetching space: ' + err.message, 'error');
        });
}
window.previewHuggingFaceSpace = previewHuggingFaceSpace;

function _showHFPreview(data, url) {
    var preview = document.getElementById('add-env-import-preview');
    var metaEl = document.getElementById('add-env-import-meta');
    if (!preview || !metaEl) return;

    var tags = (data.tags || []).map(function(t) { return '<span class="add-env-import-tag">' + t + '</span>'; }).join('');
    var html = '' +
        '<div class="add-env-import-meta-row"><span class="add-env-import-meta-label">Environment</span><span class="add-env-import-meta-value"><a href="' + url + '" target="_blank">' + (data.id || data.owner + '/' + data.repo) + '</a></span></div>' +
        '<div class="add-env-import-meta-row"><span class="add-env-import-meta-label">Author</span><span class="add-env-import-meta-value">' + (data.author || data.owner || '—') + '</span></div>' +
        '<div class="add-env-import-meta-row"><span class="add-env-import-meta-label">SDK</span><span class="add-env-import-meta-value">' + (data.sdk || 'Unknown') + '</span></div>' +
        '<div class="add-env-import-meta-row"><span class="add-env-import-meta-label">License</span><span class="add-env-import-meta-value">' + (data.license || 'Not specified') + '</span></div>' +
        (data.likes !== undefined ? '<div class="add-env-import-meta-row"><span class="add-env-import-meta-label">Likes</span><span class="add-env-import-meta-value">' + data.likes + '</span></div>' : '') +
        (tags ? '<div class="add-env-import-meta-row"><span class="add-env-import-meta-label">Tags</span><span class="add-env-import-meta-value"><div class="add-env-import-tags">' + tags + '</div></span></div>' : '') +
        (data.last_modified ? '<div class="add-env-import-meta-row"><span class="add-env-import-meta-label">Updated</span><span class="add-env-import-meta-value">' + new Date(data.last_modified).toLocaleDateString() + '</span></div>' : '');

    metaEl.innerHTML = html;
}

// ─── Import source selector ───
var _importSource = 'huggingface';

function selectImportSource(btn) {
    var seg = btn.parentElement;
    seg.querySelectorAll('.add-env-seg-btn').forEach(function(c) { c.classList.remove('selected'); });
    btn.classList.add('selected');
    _importSource = btn.getAttribute('data-value');

    var urlInput = document.getElementById('add-env-import-path');
    var hint = document.getElementById('import-url-hint');
    var title = document.getElementById('import-step1-title');
    var fetchBtn = document.getElementById('btn-preview-hf');
    var step2 = document.getElementById('import-step-details');

    // Reset step 2 when source changes
    if (step2) step2.style.display = 'none';

    if (_importSource === 'huggingface') {
        if (urlInput) urlInput.placeholder = 'https://huggingface.co/spaces/org/env-name';
        if (hint) hint.textContent = 'Paste the full URL of a public HuggingFace Space';
        if (title) title.textContent = 'Enter HuggingFace URL';
        if (fetchBtn) fetchBtn.style.display = '';
    } else if (_importSource === 'github') {
        if (urlInput) urlInput.placeholder = 'https://github.com/owner/repo';
        if (hint) hint.textContent = 'Paste the URL of a public GitHub repository';
        if (title) title.textContent = 'Enter GitHub URL';
        if (fetchBtn) fetchBtn.style.display = 'none';
        if (step2) step2.style.display = 'block';
    } else {
        if (urlInput) urlInput.placeholder = 'https://example.com/my-environment';
        if (hint) hint.textContent = 'Paste a URL to any publicly accessible environment';
        if (title) title.textContent = 'Enter URL';
        if (fetchBtn) fetchBtn.style.display = 'none';
        if (step2) step2.style.display = 'block';
    }
}
window.selectImportSource = selectImportSource;

function fetchImportSource() {
    if (_importSource === 'huggingface') {
        previewHuggingFaceSpace();
    }
}
window.fetchImportSource = fetchImportSource;

function clearEnvImport() {
    var metaEl = document.getElementById('add-env-import-meta');
    var statusEl = document.getElementById('add-env-import-status');
    var step2 = document.getElementById('import-step-details');
    if (metaEl) metaEl.innerHTML = '';
    if (statusEl) statusEl.style.display = 'none';
    if (step2) step2.style.display = 'none';
    var nameInput = document.getElementById('add-env-import-name');
    var descInput = document.getElementById('add-env-import-desc');
    var urlInput = document.getElementById('add-env-import-path');
    if (nameInput) nameInput.value = '';
    if (descInput) descInput.value = '';
    if (urlInput) urlInput.value = '';
    _hfImportedMeta = null;
    // Reset source selector to HuggingFace
    _importSource = 'huggingface';
    var srcBtns = document.querySelectorAll('#add-env-import-source-seg .add-env-seg-btn');
    srcBtns.forEach(function(b, i) { b.classList.toggle('selected', i === 0); });
    var fetchBtn = document.getElementById('btn-preview-hf');
    if (fetchBtn) fetchBtn.style.display = '';
    var hint = document.getElementById('import-url-hint');
    if (hint) hint.textContent = 'Paste the full URL of a public HuggingFace Space';
    var title = document.getElementById('import-step1-title');
    if (title) title.textContent = 'Enter HuggingFace URL';
}
window.clearEnvImport = clearEnvImport;

function submitImportedEnvironment() {
    var nameInput = document.getElementById('add-env-import-name');
    var descInput = document.getElementById('add-env-import-desc');
    var urlInput = document.getElementById('add-env-import-path');
    var name = nameInput ? nameInput.value.trim() : '';
    var desc = descInput ? descInput.value.trim() : '';
    var url = urlInput ? urlInput.value.trim() : '';

    if (!name) {
        if (window.showToast) showToast('Please enter an environment name.', 'error');
        return;
    }
    if (!url) {
        if (window.showToast) showToast('Please enter a URL.', 'error');
        return;
    }

    // Branch by import source
    if (_importSource === 'github' || _importSource === 'url') {
        // Direct import — no clone, just persist as custom env with source_url
        var newEnv = {
            name: name,
            description: desc || 'Imported from ' + (_importSource === 'github' ? 'GitHub' : 'URL'),
            category: 'custom',
            system: 'Custom',
            domain: 'custom',
            sdk: 'custom',
            actions: [],
            source: _importSource,
            source_url: url,
            isCustom: true
        };
        environmentDetails[name] = generateEnvironmentDetails(newEnv);
        _addEnvironmentToGrid(newEnv);
        // Persist (auto-classifies) then update local state
        fetch(API_BASE + '/api/custom-environments', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newEnv)
        }).then(function() {
            return fetch(API_BASE + '/api/classify-environment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name, description: desc || '' })
            });
        }).then(function(r) { return r && r.ok ? r.json() : null; })
        .then(function(cls) {
            if (cls && cls.category) {
                newEnv.category = cls.category;
                newEnv.system = cls.system;
                newEnv.domain = cls.domain;
                newEnv.workflow = cls.workflow;
                newEnv.tags = cls.tags;
                environmentDetails[name] = generateEnvironmentDetails(newEnv);
                if (typeof filterEnvironments === 'function') {
                    var searchVal = document.getElementById('env-search') ? document.getElementById('env-search').value : '';
                    var catVal = document.querySelector('.catalog-tab.active') ? document.querySelector('.catalog-tab.active').getAttribute('data-category') || 'all' : 'all';
                    filterEnvironments(searchVal, catVal);
                }
                console.log('[Import] Classified:', name, cls);
            }
        }).catch(function(err) { console.warn('[Import] Backend persist/classify failed:', err); });
        if (window.showToast) showToast('Environment "' + name + '" imported from ' + (_importSource === 'github' ? 'GitHub' : 'URL') + '!', 'success');
        clearEnvImport();
        setTimeout(function() { closeAddEnvironmentPage(); }, 800);
        return;
    }

    // HuggingFace import (existing flow)
    var parsed = _parseHuggingFaceUrl(url);
    if (!parsed) {
        if (window.showToast) showToast('Invalid HuggingFace URL. Expected: https://huggingface.co/spaces/owner/repo', 'error');
        return;
    }

    var statusEl = document.getElementById('add-env-import-status');
    var statusText = document.getElementById('add-env-import-status-text');
    if (statusEl) statusEl.style.display = 'block';
    if (statusText) statusText.textContent = 'Cloning HuggingFace environment and setting up locally...';

    fetch(API_BASE + '/api/huggingface/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: name,
            description: desc,
            hf_url: url,
            hf_owner: parsed.owner,
            hf_repo: parsed.repo
        })
    })
    .then(function(res) {
        if (!res.ok) return res.json().then(function(d) { throw new Error(d.detail || 'Import failed'); });
        return res.json();
    })
    .then(function(data) {
        if (statusText) statusText.textContent = 'Analyzing environment structure...';

        var newEnv = {
            name: name,
            description: desc || (data.description || 'Imported from HuggingFace'),
            category: 'custom',
            system: 'Custom',
            domain: 'custom',
            sdk: data.sdk || (_hfImportedMeta ? _hfImportedMeta.sdk : 'gradio'),
            actions: [],
            source: 'huggingface',
            hf_url: url,
            isCustom: true
        };

        return fetch(API_BASE + '/api/environment/' + encodeURIComponent(name) + '/analyze')
            .then(function(r) { return r.ok ? r.json() : null; })
            .then(function(analysis) {
                if (statusEl) statusEl.style.display = 'none';

                var hfMeta = _hfImportedMeta || {};
                var details = {
                    source: 'huggingface',
                    isCustom: true,
                    hf_url: url,
                    hf_owner: parsed.owner,
                    hf_repo: parsed.repo,
                    sdk: newEnv.sdk,
                    description: newEnv.description,
                    author: hfMeta.author || parsed.owner,
                    license: hfMeta.license || 'Not specified',
                    tags: hfMeta.tags || [],
                    likes: hfMeta.likes || 0,
                    lastModified: hfMeta.last_modified || '',
                    readme: analysis ? analysis.readme_raw : '',
                    frontMatter: analysis ? analysis.front_matter : {},
                    openenv: analysis ? analysis.openenv : {},
                    pyproject: analysis ? analysis.pyproject : {},
                    files: analysis ? analysis.files : [],
                    endpoints: analysis ? analysis.endpoints : [],
                    models: analysis ? analysis.models : {},
                    localPath: analysis ? analysis.local_path : ''
                };
                environmentDetails[name] = details;

                _addEnvironmentToGrid(newEnv);

                // Async classify the imported environment
                fetch(API_BASE + '/api/classify-environment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name, description: newEnv.description })
                }).then(function(r) { return r.ok ? r.json() : null; })
                .then(function(cls) {
                    if (cls && cls.category) {
                        newEnv.category = cls.category;
                        newEnv.system = cls.system;
                        newEnv.domain = cls.domain;
                        newEnv.workflow = cls.workflow;
                        newEnv.tags = cls.tags;
                        // Re-persist with classified fields
                        fetch(API_BASE + '/api/custom-environments', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(newEnv)
                        });
                        if (typeof filterEnvironments === 'function') {
                            var searchVal = document.getElementById('env-search') ? document.getElementById('env-search').value : '';
                            var catVal = document.querySelector('.catalog-tab.active') ? document.querySelector('.catalog-tab.active').getAttribute('data-category') || 'all' : 'all';
                            filterEnvironments(searchVal, catVal);
                        }
                        console.log('[HF Import] Classified:', name, cls);
                    }
                }).catch(function(err) { console.warn('[HF Import] Classify failed:', err); });

                if (window.showToast) showToast('Environment "' + name + '" imported from HuggingFace!', 'success');
                clearEnvImport();
                setTimeout(function() { closeAddEnvironmentPage(); }, 800);
            });
    })
    .catch(function(err) {
        if (statusEl) statusEl.style.display = 'none';
        console.error('[HF Import] Error:', err);
        if (window.showToast) showToast('Import failed: ' + err.message, 'error');
    });
}
window.submitImportedEnvironment = submitImportedEnvironment;

// ─── Delete Environment ───
function deleteEnvironment(envName) {
    if (!confirm('Are you sure you want to delete the environment "' + envName + '"? This action cannot be undone.')) {
        return;
    }
    fetch(API_BASE + '/api/custom-environments/' + encodeURIComponent(envName), { method: 'DELETE' })
        .then(function(res) {
            if (!res.ok) return res.json().then(function(d) { throw new Error(d.detail || 'Delete failed'); });
            return res.json();
        })
        .then(function() {
            // Remove from local arrays
            allEnvironments = allEnvironments.filter(function(e) { return e.name !== envName; });
            delete environmentDetails[envName];
            if (window.showToast) showToast('Environment "' + envName + '" deleted.', 'success');
            // Go back to catalog
            document.getElementById('env-detail-page').style.display = 'none';
            document.getElementById('catalog-container').style.display = 'block';
            var totalEl = document.getElementById('total-envs');
            if (totalEl) totalEl.textContent = allEnvironments.length;
            var searchInput = document.getElementById('search-input');
            filterEnvironments(searchInput ? searchInput.value.trim() : '', getActiveCategory());
        })
        .catch(function(err) {
            if (window.showToast) showToast('Delete failed: ' + err.message, 'error');
        });
}
window.deleteEnvironment = deleteEnvironment;
