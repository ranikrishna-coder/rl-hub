// Generic Simulation Console for All RL Environments

// API Base URL - auto-detected or set by config.js
const API_BASE = window.API_BASE || (() => {
    // Fallback detection if window.API_BASE wasn't set
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return 'http://localhost:8000';
    } else if (hostname.includes('onrender.com')) {
        return `${protocol}//${hostname}`;
    } else if (hostname.includes('github.io')) {
        return 'https://rl-hub-api.onrender.com';
    } else {
        return 'https://rl-hub-api.onrender.com';
    }
})();

console.log('📡 Using API Base URL:', API_BASE);
let currentEnvironment = null;
let simulationState = null;
let simulationInterval = null;
let stepCount = 0;
let metricsHistory = [];
let allEnvironments = [];
let jiraMockData = null;
let jiraIssueIndex = 0;  // Cycles through all issues on each Initialize (agent runs across all)
let jiraSubtaskLog = []; // Collects all subtasks created in simulation for download

// Environment-specific configurations
const environmentConfigs = {
    // Clinical environments
    'TreatmentPathwayOptimization': {
        configFields: [
            { id: 'patient-severity', label: 'Patient Condition Severity:', type: 'select', options: ['mild', 'moderate', 'severe', 'critical'], value: 'moderate' },
            { id: 'num-conditions', label: 'Number of Conditions:', type: 'number', value: 2, min: 1, max: 5 },
            { id: 'initial-risk', label: 'Initial Risk Score:', type: 'range', value: 50, min: 0, max: 100 }
        ],
        generateState: (config) => generatePatientState(config),
        processStep: (state, action) => processTreatmentStep(state, action)
    },
    'SepsisEarlyIntervention': {
        configFields: [
            { id: 'sepsis-probability', label: 'Sepsis Probability:', type: 'range', value: 60, min: 30, max: 90 },
            { id: 'initial-sofa', label: 'Initial SOFA Score:', type: 'range', value: 8, min: 0, max: 24 },
            { id: 'time-since-admission', label: 'Hours Since Admission:', type: 'number', value: 2, min: 0, max: 24 }
        ],
        generateState: (config) => generateSepsisState(config),
        processStep: (state, action) => processSepsisStep(state, action)
    },
    'ICUResourceAllocation': {
        configFields: [
            { id: 'icu-beds', label: 'ICU Beds Available:', type: 'number', value: 20, min: 5, max: 50 },
            { id: 'stepdown-beds', label: 'Step-Down Beds:', type: 'number', value: 30, min: 10, max: 60 },
            { id: 'patient-queue', label: 'Patients in Queue:', type: 'number', value: 5, min: 0, max: 20 }
        ],
        generateState: (config) => generateICUState(config),
        processStep: (state, action) => processICUStep(state, action)
    },
    'SurgicalScheduling': {
        configFields: [
            { id: 'surgery-queue', label: 'Surgeries in Queue:', type: 'number', value: 10, min: 1, max: 30 },
            { id: 'urgent-pct', label: 'Urgent Surgeries (%):', type: 'range', value: 25, min: 0, max: 100 },
            { id: 'or-rooms', label: 'OR Rooms Available:', type: 'number', value: 10, min: 2, max: 20 }
        ],
        generateState: (config) => generateSurgeryState(config),
        processStep: (state, action) => processSurgeryStep(state, action)
    },
    // Imaging environments
    'ImagingOrderPrioritization': {
        configFields: [
            { id: 'queue-size', label: 'Number of Orders in Queue:', type: 'number', value: 15, min: 1, max: 50 },
            { id: 'high-urgency-pct', label: 'High Urgency Orders (%):', type: 'number', value: 30, min: 0, max: 100 },
            { id: 'avg-order-value', label: 'Average Order Value ($):', type: 'number', value: 500, min: 100, max: 5000 },
            { id: 'ct-availability', label: 'CT Scanner Availability:', type: 'range', value: 80, min: 0, max: 100 },
            { id: 'mri-availability', label: 'MRI Availability:', type: 'range', value: 70, min: 0, max: 100 },
            { id: 'xray-availability', label: 'X-Ray Availability:', type: 'range', value: 90, min: 0, max: 100 }
        ],
        generateState: (config) => generateImagingQueue(config),
        processStep: (state, action) => processImagingStep(state, action)
    },
    'RadiologyScheduling': {
        configFields: [
            { id: 'appointments', label: 'Appointments to Schedule:', type: 'number', value: 20, min: 5, max: 50 },
            { id: 'morning-slots', label: 'Morning Slots:', type: 'number', value: 10, min: 5, max: 20 },
            { id: 'afternoon-slots', label: 'Afternoon Slots:', type: 'number', value: 10, min: 5, max: 20 }
        ],
        generateState: (config) => generateScheduleState(config),
        processStep: (state, action) => processScheduleStep(state, action)
    },
    // Jira sample use cases (mock data from /jira-mock-data)
    'JiraIssueResolution': {
        configFields: [],
        generateState: (config) => generateJiraIssueResolutionState(config),
        processStep: (state, action) => processJiraIssueResolutionStep(state, action)
    },
    'JiraStatusUpdate': {
        configFields: [
            { id: 'jira-scenario-status', label: 'Scenario:', type: 'select', options: ['in_progress_to_blocked', 'in_progress_to_done'], value: 'in_progress_to_blocked', scenarioLabels: { 'in_progress_to_blocked': 'Change from in-progress to blocked', 'in_progress_to_done': 'Change from in-progress to done' } }
        ],
        generateState: (config) => generateJiraStatusUpdateState(config),
        processStep: (state, action) => processJiraStatusUpdateStep(state, action)
    },
    'JiraCommentManagement': {
        configFields: [],
        generateState: (config) => generateJiraCommentManagementState(config),
        processStep: (state, action) => processJiraCommentManagementStep(state, action)
    },
    'JiraSubtaskManagement': {
        configFields: [
            { id: 'jira-subtask-summary', label: 'Subtask summary:', type: 'text', value: '', placeholder: 'e.g. Reproduce SSO 500 error' },
            { id: 'jira-subtask-description', label: 'Subtask description (optional):', type: 'text', value: '', placeholder: 'Additional context for the subtask' },
            { id: 'jira-subtask-scenario', label: 'Scenario:', type: 'select', options: ['create_subtask', 'delete_subtask'], value: 'create_subtask', scenarioLabels: { 'create_subtask': 'Create sub-task', 'delete_subtask': 'Delete sub task' } },
            { id: 'jira-subtask-use-live', label: 'Use live Jira (server configured)', type: 'checkbox', value: false },
            { id: 'jira-subtask-parent-key', label: 'Live Jira parent issue key (task):', type: 'text', value: '', placeholder: 'e.g. PROJ-123' }
        ],
        generateState: (config) => generateJiraSubtaskManagementState(config),
        processStep: (state, action) => processJiraSubtaskManagementStep(state, action)
    }
    // Generic config will be used for environments not in this list
};

// Load Jira mock data for sample use cases
async function loadJiraMockData() {
    try {
        const response = await fetch(`${API_BASE}/jira-mock-data`);
        if (response.ok) jiraMockData = await response.json();
    } catch (e) {
        console.warn('Jira mock data not loaded, using fallback:', e);
    }
    if (!jiraMockData || !jiraMockData.issues) {
        jiraMockData = {
            issues: [
                // Fallback sample issues across multiple projects; when API is available,
                // full jira_mock_data.json is loaded instead.
                { key: 'PROJ-101', summary: 'Login 500 with SSO', description: 'Server returns 500 when SSO is enabled.', status: 'In Progress', valid_transitions: [{ id: '31', name: 'Done' }] },
                { key: 'PROJ-102', summary: 'Dashboard export PII', description: 'CSV export includes PII columns; should be redacted.', status: 'To Do', valid_transitions: [{ id: '21', name: 'In Progress' }] },
                { key: 'PROJ-103', summary: 'API rate limit not applied', description: 'Internal service accounts bypass rate limiting.', status: 'In Progress', valid_transitions: [{ id: '31', name: 'Done' }] },
                { key: 'PROJ-104', summary: 'Support Excel export', description: 'Support Excel export in notifications.', status: 'To Do', valid_transitions: [{ id: '21', name: 'In Progress' }] },
                { key: 'PROJ-201', summary: 'Add multi-project dashboard', description: 'New dashboard aggregating multiple Jira projects.', status: 'In Progress', valid_transitions: [{ id: '31', name: 'Done' }] },
                { key: 'OPS-301', summary: 'Server maintenance task', description: 'Planned maintenance for Jira infrastructure.', status: 'To Do', valid_transitions: [{ id: '21', name: 'In Progress' }] }
            ],
            comment_threads: {
                'PROJ-101': [{ id: '1', author: 'Alice', body: 'Reproduced on staging.' }],
                'PROJ-102': [],
                'PROJ-103': [],
                'PROJ-104': [],
                'PROJ-201': [],
                'OPS-301': []
            }
        };
        console.warn(`Using fallback Jira mock data with ${jiraMockData.issues.length} issues. To use full mock data, ensure ${API_BASE}/jira-mock-data is reachable.`);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadJiraMockData();
    loadEnvironments();
    setupEventListeners();
    setupRangeInputs();
    setupVerifierControls();
});

// Jira verifier options for dropdown (value used in API: jira_workflow:workflow_id)
const JIRA_VERIFIER_OPTIONS = [
    { value: 'jira_workflow:issue_resolution', label: 'Jira Issue Resolution' },
    { value: 'jira_workflow:status_update', label: 'Jira Status Update' },
    { value: 'jira_workflow:comment_management', label: 'Jira Comment Management' },
    { value: 'jira_workflow:subtask_management', label: 'Jira Task Management' }
];
const JIRA_ENV_TO_WORKFLOW = { JiraIssueResolution: 'issue_resolution', JiraStatusUpdate: 'status_update', JiraCommentManagement: 'comment_management', JiraSubtaskManagement: 'subtask_management' };

// Jira verifiers from app (Verifiers.tsx): per-environment verifier name and expected tool order
const JIRA_VERIFIERS_BY_ENV = {
    'JiraIssueResolution': {
        name: 'Jira Issue Resolution',
        description: 'Validates tool sequence and argument validity for Jira issue resolution.',
        expected_order: ['get_issue_summary_and_description', 'get_transitions', 'transition_issue'],
        usedInScenarios: ['Issue Resolution Flow', 'Status Update Workflow']
    },
    'JiraStatusUpdate': {
        name: 'Jira Issue Resolution',
        description: 'Validates valid transitions and status updates (same validator as Issue Resolution).',
        expected_order: ['get_transitions', 'transition_issue'],
        usedInScenarios: ['Status Update Workflow']
    },
    'JiraCommentManagement': {
        name: 'Jira Comment Management',
        description: 'Validates tool sequence and content for Jira comment workflows.',
        expected_order: ['add_comment', 'get_comments'],
        usedInScenarios: ['Comment Thread Management']
    },
    'JiraSubtaskManagement': {
        name: 'Jira Subtask Management',
        description: 'Validates tool sequence for adding subtasks to Jira issues.',
        expected_order: ['get_issue_summary_and_description', 'create_subtask'],
        usedInScenarios: ['Subtask Management']
    }
};

// Recommended verifier by software system (aligned with catalog/training and app Verifiers.tsx)
function getVerifierRecommendationForSystem(system) {
    if (!system || system === 'all') {
        return { type: 'ensemble', weights: { clinical: 0.35, operational: 0.3, financial: 0.2, compliance: 0.15 } };
    }
    const s = system.toLowerCase();
    // Jira: use environment built-in verifier (workflow order); app verifiers in Verifiers.tsx
    if (s.includes('jira') || s.includes('atlassian')) {
        return { type: 'default' };
    }
    if (s.includes('epic') || s.includes('cerner') || s.includes('allscripts') || s.includes('meditech')) {
        return { type: 'ensemble', weights: { clinical: 0.45, operational: 0.25, financial: 0.15, compliance: 0.15 } };
    }
    if (s.includes('philips') || s.includes('ge ')) {
        return { type: 'ensemble', weights: { clinical: 0.3, operational: 0.45, financial: 0.15, compliance: 0.1 } };
    }
    if (s.includes('change ')) {
        return { type: 'ensemble', weights: { clinical: 0.15, operational: 0.2, financial: 0.45, compliance: 0.2 } };
    }
    if (s.includes('veeva') || s.includes('iqvia')) {
        return { type: 'ensemble', weights: { clinical: 0.4, operational: 0.2, financial: 0.2, compliance: 0.2 } };
    }
    if (s.includes('health catalyst') || s.includes('innovaccer')) {
        return { type: 'ensemble', weights: { clinical: 0.4, operational: 0.35, financial: 0.15, compliance: 0.1 } };
    }
    if (s.includes('teladoc') || s.includes('amwell')) {
        return { type: 'ensemble', weights: { clinical: 0.35, operational: 0.4, financial: 0.15, compliance: 0.1 } };
    }
    if (s.includes('intersystems') || s.includes('orion health')) {
        return { type: 'ensemble', weights: { clinical: 0.25, operational: 0.35, financial: 0.15, compliance: 0.25 } };
    }
    return { type: 'ensemble', weights: { clinical: 0.35, operational: 0.3, financial: 0.2, compliance: 0.15 } };
}

function updateSimulationVerifierForSystem() {
    const systemSelect = document.getElementById('system-select');
    const verifierTypeSelect = document.getElementById('verifier-type');
    const verifierWeightsInput = document.getElementById('verifier-weights');
    if (!systemSelect || !verifierTypeSelect) return;
    const rec = getVerifierRecommendationForSystem(systemSelect.value);
    verifierTypeSelect.value = rec.type;
    if (verifierWeightsInput && rec.weights) verifierWeightsInput.value = JSON.stringify(rec.weights, null, 2);
    const g = document.getElementById('verifier-weights-group');
    if (g) g.style.display = (verifierTypeSelect.value === 'ensemble') ? 'block' : 'none';
    updateJiraVerifierDisplay();
}

function updateJiraVerifierDisplay() {
    const envName = currentEnvironment;
    const verifierInfo = document.getElementById('jira-verifier-info');
    if (!verifierInfo) return;
    const v = JIRA_VERIFIERS_BY_ENV[envName];
    if (v) {
        verifierInfo.style.display = 'block';
        verifierInfo.innerHTML = '<strong>Active verifier (from app):</strong> ' + v.name + '<br>' +
            '<span class="verifier-desc">' + v.description + '</span><br>' +
            '<span class="verifier-order">Tool order: ' + v.expected_order.join(' → ') + '</span>';
    } else {
        verifierInfo.style.display = 'none';
    }
}

function setupVerifierControls() {
    const verifierTypeSelect = document.getElementById('verifier-type');
    const verifierWeightsGroup = document.getElementById('verifier-weights-group');
    
    if (verifierTypeSelect && verifierWeightsGroup) {
        verifierTypeSelect.addEventListener('change', (e) => {
            if (e.target.value === 'ensemble') {
                verifierWeightsGroup.style.display = 'block';
            } else {
                verifierWeightsGroup.style.display = 'none';
            }
        });
    }
}

function getFilteredEnvironmentsForSystem() {
    const systemSel = document.getElementById('system-select');
    const system = systemSel ? systemSel.value : 'all';
    if (system === 'all') return allEnvironments;
    return allEnvironments.filter(env => {
        const envSystems = (env.system || '').split(',').map(s => s.trim()).filter(Boolean);
        const matchesSystem = envSystems.includes(system);
        // When Jira is selected, only show RL Jira environments (category === 'jira')
        if (matchesSystem && (system.includes('Jira') || system.includes('jira'))) {
            return (env.category || '') === 'jira';
        }
        return matchesSystem;
    });
}

function populateEnvironmentSelect() {
    const envSelect = document.getElementById('environment-select');
    if (!envSelect) return;
    const filtered = getFilteredEnvironmentsForSystem();
    const currentVal = envSelect.value;
    envSelect.innerHTML = '<option value="">Select an environment...</option>' +
        filtered.map(env => {
            const displayName = formatEnvironmentName(env.name);
            const systemLabel = env.system ? ` (${env.system})` : '';
            return `<option value="${env.name}">${displayName}${systemLabel}</option>`;
        }).join('');
    if (currentVal && filtered.some(e => e.name === currentVal)) {
        envSelect.value = currentVal;
    } else if (filtered.length > 0 && !currentVal) {
        const urlParams = new URLSearchParams(window.location.search);
        const envParam = urlParams.get('env');
        if (envParam && filtered.some(e => e.name === envParam)) {
            envSelect.value = envParam;
            selectEnvironment(envParam);
        }
    }
}

async function loadEnvironments() {
    try {
        const response = await fetch(`${API_BASE}/environments`);
        if (!response.ok) throw new Error('Failed to load environments');
        
        const data = await response.json();
        allEnvironments = data.environments || [];
        
        const systems = new Set();
        allEnvironments.forEach(env => {
            (env.system || '').split(',').forEach(s => {
                const t = s.trim();
                if (t) systems.add(t);
            });
        });
        const systemList = Array.from(systems).sort((a, b) => a.localeCompare(b));
        
        const systemSelect = document.getElementById('system-select');
        if (systemSelect) {
            systemSelect.innerHTML = '<option value="all">All systems</option>' +
                systemList.map(s => `<option value="${s.replace(/"/g, '&quot;')}">${s}</option>`).join('');
            systemSelect.addEventListener('change', () => {
                populateEnvironmentSelect();
                updateSimulationVerifierForSystem();
            });
        }
        
        const select = document.getElementById('environment-select');
        populateEnvironmentSelect();
        updateSimulationVerifierForSystem();
        
        select.addEventListener('change', (e) => {
            if (e.target.value) {
                selectEnvironment(e.target.value);
            }
        });
        
        const urlParams = new URLSearchParams(window.location.search);
        const envParam = urlParams.get('env');
        if (envParam && allEnvironments.some(e => e.name === envParam)) {
            const filtered = getFilteredEnvironmentsForSystem();
            if (filtered.some(e => e.name === envParam)) {
                select.value = envParam;
                selectEnvironment(envParam);
            }
        }
    } catch (error) {
        console.error('Error loading environments:', error);
    }
}

function formatEnvironmentName(name) {
    // Add spaces before capital letters
    return name.replace(/([A-Z])/g, ' $1').trim();
}

function selectEnvironment(envName) {
    currentEnvironment = envName;
    const env = allEnvironments.find(e => e.name === envName);
    
    // Update title
    const displayName = formatEnvironmentName(envName);
    document.getElementById('console-title').textContent = `🩻 ${displayName} - Simulation Console`;
    
    // For Jira envs, show Jira verifier options and set default to matching workflow
    updateVerifierSelectForEnvironment(envName);

    // Limit system selector to relevant system(s) for this environment
    const systemSelect = document.getElementById('system-select');
    if (systemSelect && env && env.system) {
        const systems = (env.system || '').split(',').map(s => s.trim()).filter(Boolean);
        if (systems.length === 1) {
            systemSelect.innerHTML = `<option value="${systems[0].replace(/"/g, '&quot;')}">${systems[0]}</option>`;
            systemSelect.value = systems[0];
        } else if (systems.length > 1) {
            systemSelect.innerHTML = systems.map(s => `<option value="${s.replace(/"/g, '&quot;')}">${s}</option>`).join('');
            systemSelect.value = systems[0];
        }
    }

    // Load environment-specific configuration
    loadEnvironmentConfig(envName);
    // Show correct Jira verifier (from app) for Jira envs
    updateJiraVerifierDisplay();
}

function updateVerifierSelectForEnvironment(envName) {
    const verifierTypeSelect = document.getElementById('verifier-type');
    const verifierWeightsGroup = document.getElementById('verifier-weights-group');
    if (!verifierTypeSelect) return;
    const isJiraEnv = JIRA_VERIFIERS_BY_ENV[envName];
    if (isJiraEnv) {
        const defaultWorkflow = JIRA_ENV_TO_WORKFLOW[envName] || 'issue_resolution';
        const hasMatchingVerifier = JIRA_VERIFIER_OPTIONS.some(o => o.value === 'jira_workflow:' + defaultWorkflow);
        verifierTypeSelect.innerHTML = JIRA_VERIFIER_OPTIONS.map(o =>
            `<option value="${o.value}"${o.value === 'jira_workflow:' + defaultWorkflow ? ' selected' : ''}>${o.label}</option>`
        ).join('') + `<option value="default"${!hasMatchingVerifier ? ' selected' : ''}>Default (Environment Built-in)</option>`;
        if (verifierWeightsGroup) verifierWeightsGroup.style.display = 'none';
    } else {
        verifierTypeSelect.innerHTML = `
            <option value="ensemble" selected>Ensemble (Default - All Verifiers)</option>
            <option value="clinical">Clinical Verifier</option>
            <option value="operational">Operational Verifier</option>
            <option value="financial">Financial Verifier</option>
            <option value="compliance">Compliance Verifier</option>
            <option value="default">Default (Environment Built-in)</option>`;
        if (verifierWeightsGroup) verifierWeightsGroup.style.display = 'none';
    }
}

function loadEnvironmentConfig(envName) {
    const configDiv = document.getElementById('dynamic-config');
    const config = environmentConfigs[envName];
    
    if (!config) {
        // Generic configuration for environments without specific config
        const maxStepsTooltip = 'Maximum number of simulation steps before the episode ends (10–1000). Longer episodes allow for more complex scenarios and better evaluation of long-term strategies. Shorter episodes give quick feedback.';
        const randomSeedTooltip = 'Optional random seed for reproducible simulations. Enter a number to get the same random sequence each run (useful for comparing strategies). Leave empty for different random behavior each run.';
        configDiv.innerHTML = `
            <div class="form-group">
                <label>Max Steps: <span class="tooltip-icon" title="${maxStepsTooltip}">ℹ️</span></label>
                <input type="number" id="max-steps" value="100" min="10" max="1000" title="${maxStepsTooltip}" />
            </div>
            <div class="form-group">
                <label>Random Seed (optional): <span class="tooltip-icon" title="${randomSeedTooltip}">ℹ️</span></label>
                <input type="number" id="random-seed" value="" placeholder="Auto" title="${randomSeedTooltip}" />
            </div>
        `;
        return;
    }
    
    configDiv.innerHTML = config.configFields.map(field => {
        const tooltip = field.tooltip || getDefaultTooltip(field.id, field.label);
        if (field.type === 'range') {
            return `
                <div class="form-group">
                    <label>${field.label} <span class="tooltip-icon" title="${tooltip}">ℹ️</span></label>
                    <input type="range" id="${field.id}" min="${field.min}" max="${field.max}" value="${field.value}" title="${tooltip}" />
                    <span id="${field.id}-value">${field.value}${field.id.includes('availability') || field.id.includes('pct') || field.id.includes('probability') ? '%' : ''}</span>
                </div>
            `;
        } else if (field.type === 'select') {
            // Jira scenario: use scenarioLabels for display
            if ((field.id === 'jira-scenario-status' || field.id === 'jira-subtask-scenario') && field.scenarioLabels) {
                const options = field.options || [];
                const defaultVal = options.includes(field.value) ? field.value : (options[0] || '');
                return `
                    <div class="form-group">
                        <label>${field.label} <span class="tooltip-icon" title="${tooltip}">ℹ️</span></label>
                        <select id="${field.id}" title="${tooltip}">
                            ${options.map(opt => `<option value="${opt}" ${opt === defaultVal ? 'selected' : ''}>${field.scenarioLabels[opt] || opt}</option>`).join('')}
                        </select>
                    </div>
                `;
            }
            // Jira: use issues filtered by scenario for status_update; otherwise all issues
            let options = (field.id && field.id.includes('jira-issue-key') && jiraMockData && jiraMockData.issues)
                ? jiraMockData.issues.map(i => i.key)
                : (field.options || []);
            const defaultVal = options.includes(field.value) ? field.value : (options[0] || '');
            return `
                <div class="form-group">
                    <label>${field.label} <span class="tooltip-icon" title="${tooltip}">ℹ️</span></label>
                    <select id="${field.id}" title="${tooltip}">
                        ${options.map(opt => `<option value="${opt}" ${opt === defaultVal ? 'selected' : ''}>${opt}</option>`).join('')}
                    </select>
                </div>
            `;
        } else {
            const placeholder = field.placeholder || '';
            return `
                <div class="form-group">
                    <label>${field.label} <span class="tooltip-icon" title="${tooltip}">ℹ️</span></label>
                    <input type="${field.type}" id="${field.id}" value="${(field.value || '').replace(/"/g, '&quot;')}" min="${field.min || ''}" max="${field.max || ''}" placeholder="${placeholder.replace(/"/g, '&quot;')}" title="${tooltip}" />
                </div>
            `;
        }
    }).join('');
    
    // Setup range inputs
    setupRangeInputs();
}

function getDefaultTooltip(fieldId, label) {
    const tooltips = {
        'queue-size': 'Number of items (orders, tickets, or tasks) currently in the queue waiting to be processed. Larger queues represent busier operational settings and test the RL agent\'s ability to prioritize effectively.',
        'high-urgency-pct': 'Percentage of items in the queue that are high urgency or critical (0-100%). Higher values mean more urgent cases requiring immediate attention. This tests the agent\'s ability to handle time-sensitive situations.',
        'avg-order-value': 'Average monetary value of each order or item in dollars. Used to calculate financial impact and revenue metrics. Higher values make financial optimization more important in the reward function.',
        'ct-availability': 'Percentage availability of CT scanners (0-100%). Lower values indicate more constrained resources, testing the agent\'s ability to optimize resource allocation when capacity is limited.',
        'mri-availability': 'Percentage availability of MRI machines (0-100%). Affects capacity for MRI orders. Lower availability requires better scheduling and prioritization strategies.',
        'xray-availability': 'Percentage availability of X-Ray equipment (0-100%). Impacts throughput for X-Ray orders. The RL agent must balance different imaging modalities based on availability.',
        'patient-severity': 'Initial severity level of the patient condition (mild, moderate, severe, critical). Affects treatment complexity and outcomes. More severe cases require more intensive interventions and careful resource allocation.',
        'num-conditions': 'Number of concurrent medical conditions the patient has (1-5). More conditions increase complexity and require coordinated multi-step treatment plans. Tests the agent\'s ability to handle complex cases.',
        'initial-risk': 'Initial risk score for the patient (0-100). Higher scores indicate greater risk of complications or poor outcomes. The RL agent should prioritize higher-risk patients while managing overall workflow.',
        'sepsis-probability': 'Probability that the patient has or will develop sepsis (30-90%). Higher values require more urgent intervention. This tests early detection and rapid response capabilities critical in sepsis management.',
        'initial-sofa': 'Initial SOFA (Sequential Organ Failure Assessment) score (0-24). Higher scores indicate more severe organ dysfunction. The RL agent should prioritize interventions to reduce SOFA scores and improve patient outcomes.',
        'time-since-admission': 'Hours since patient admission (0-24). Affects urgency of interventions. Earlier interventions typically lead to better outcomes, so the agent should consider time-sensitive factors.',
        'max-steps': 'Maximum number of simulation steps before the episode ends (10-1000). Longer episodes allow for more complex scenarios and better evaluation of long-term strategies. Shorter episodes provide quick feedback.',
        'random-seed': 'Optional random seed for reproducible simulations. Enter a number to get the same random sequence each run, useful for comparing different strategies. Leave empty for random behavior each run.',
        'patient-count': 'Number of patients in the simulation (1-20). More patients increase complexity and resource demands, testing the agent\'s ability to manage multiple cases simultaneously.',
        'severity-level': 'Average severity level of patients (0-100). Higher values indicate more critical cases requiring immediate attention. This parameter helps simulate different hospital acuity levels.',
        'claims-count': 'Number of insurance claims to process (5-50). More claims increase workload and test the agent\'s ability to optimize claim processing workflows and reduce denials.',
        'avg-claim-value': 'Average dollar value of each claim ($500-$10,000). Used for revenue calculations. Higher values make financial optimization more critical in the reward function.',
        'population-size': 'Size of the population being managed (10-1000). Larger populations require more resources and test scalability. The agent must identify high-risk individuals efficiently.',
        'high-risk-pct': 'Percentage of the population that is high-risk (5-50%). Higher values require more intensive interventions and better risk stratification. Tests population health management capabilities.',
        'resource-availability': 'Overall resource availability percentage (0-100%). Lower values indicate more constrained operations, requiring better resource allocation strategies. Tests efficiency under resource constraints.',
        'icu-beds': 'Number of ICU beds available (5-50). Limited beds require optimal allocation based on patient acuity and expected outcomes.',
        'stepdown-beds': 'Number of step-down unit beds available (10-60). These beds provide intermediate care between ICU and general wards.',
        'patient-queue': 'Number of patients waiting for ICU admission (0-20). Higher queues test the agent\'s ability to prioritize and manage wait times.',
        'surgery-queue': 'Number of surgeries waiting to be scheduled (1-30). Tests OR scheduling optimization and resource allocation.',
        'urgent-pct': 'Percentage of surgeries that are urgent (0-100%). Higher values require faster scheduling and better prioritization.',
        'or-rooms': 'Number of operating rooms available (2-20). Limited rooms require optimal scheduling to maximize utilization.',
        'appointments': 'Number of appointments to schedule (5-50). Tests scheduling optimization and patient satisfaction.',
        'morning-slots': 'Number of morning appointment slots available (5-20). Tests time-based scheduling optimization.',
        'afternoon-slots': 'Number of afternoon appointment slots available (5-20). Tests preference matching and capacity management.',
        'jira-scenario-status': 'Select the status update scenario. Agent runs across all Jira issues in mock data. No live Jira required.',
        'jira-subtask-summary': 'The summary/title of the subtask you want to add under the parent Jira issue. Enter what the subtask should be about.',
        'jira-subtask-description': 'Optional description or additional context for the subtask. Leave empty if not needed.'
    };
    
    return tooltips[fieldId] || `Configure ${label.toLowerCase()}. Adjust this parameter to simulate different workflow scenarios and test the RL agent's decision-making capabilities.`;
}

function setupRangeInputs() {
    document.querySelectorAll('input[type="range"]').forEach(slider => {
        const display = document.getElementById(`${slider.id}-value`);
        if (display) {
            slider.addEventListener('input', (e) => {
                const suffix = slider.id.includes('availability') || slider.id.includes('pct') || slider.id.includes('probability') ? '%' : '';
                display.textContent = `${e.target.value}${suffix}`;
            });
        }
    });
}

function setupEventListeners() {
    document.getElementById('btn-initialize').addEventListener('click', initializeEnvironment);
    document.getElementById('btn-reset').addEventListener('click', resetSimulation);
    document.getElementById('btn-step').addEventListener('click', runStep);
    document.getElementById('btn-auto').addEventListener('click', startAutoRun);
    document.getElementById('btn-stop').addEventListener('click', stopAutoRun);
    const downloadBtn = document.getElementById('btn-download-jira-subtasks');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', downloadJiraSubtaskLog);
    }
    // Human evaluation (simulation run – local only; for training jobs use Training Monitor)
    const humanEvalYes = document.getElementById('human-eval-yes');
    const humanEvalNo = document.getElementById('human-eval-no');
    const humanEvalStatus = document.getElementById('human-eval-status');
    const humanEvalComment = document.getElementById('human-eval-comment');
    if (humanEvalYes) {
        humanEvalYes.addEventListener('click', () => recordHumanEval('yes'));
    }
    if (humanEvalNo) {
        humanEvalNo.addEventListener('click', () => recordHumanEval('no'));
    }

    function recordHumanEval(decision) {
        const comment = (humanEvalComment && humanEvalComment.value) ? humanEvalComment.value.trim() : '';
        const entry = { decision, comment, timestamp: new Date().toISOString(), stepCount, totalReward: (simulationState && simulationState.metrics && simulationState.metrics.totalReward != null) ? simulationState.metrics.totalReward : null };
        try {
            const key = 'rl_hub_sim_human_eval';
            const stored = JSON.parse(sessionStorage.getItem(key) || '[]');
            stored.push(entry);
            sessionStorage.setItem(key, JSON.stringify(stored));
        } catch (e) { /* ignore */ }
        if (humanEvalStatus) {
            humanEvalStatus.textContent = `Recorded: ${decision === 'yes' ? 'Yes' : 'No'}${comment ? ' — ' + comment.substring(0, 50) + (comment.length > 50 ? '…' : '') : ''}`;
        }
    }
}

async function initializeEnvironment() {
    if (!currentEnvironment) {
        alert('Please select an environment first');
        return;
    }
    
    const config = getConfiguration();
    
    try {
        // Build API URL with verifier config if provided
        let apiUrl = `${API_BASE}/kpis/${currentEnvironment}`;
        const params = new URLSearchParams();
        
        if (config.verifier_config) {
            params.append('verifier_type', config.verifier_config.type);
            params.append('verifier_config', JSON.stringify({
                type: config.verifier_config.type,
                verifiers: config.verifier_config.verifiers,
                metadata: config.verifier_config.metadata
            }));
        }
        
        if (params.toString()) {
            apiUrl += '?' + params.toString();
        }
        
        // Initialize via API
        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error('Failed to initialize environment');
        
        const envConfig = environmentConfigs[currentEnvironment];
        if (envConfig && envConfig.generateState) {
            simulationState = envConfig.generateState(config);
            if (currentEnvironment && currentEnvironment.startsWith('Jira')) {
                jiraIssueIndex++;
            }
        } else {
            simulationState = generateGenericState(config);
        }
        
        simulationState.config = config;
        simulationState.environment = currentEnvironment;
        simulationState.step = 0;
        stepCount = 0;
        metricsHistory = [];
        
        // Initialize metrics based on state
        if (simulationState.queue) {
            simulationState.metrics.queueLength = simulationState.queue.length;
            simulationState.metrics.urgentWaiting = simulationState.queue.filter(item => (item.urgency || item.acuity || 0) > 0.7).length;
        }
        if (simulationState.patientQueue) {
            simulationState.metrics.queueLength = simulationState.patientQueue.length;
        }
        if (simulationState.appointments) {
            simulationState.metrics.queueLength = simulationState.appointments.length;
        }
        
        updateDisplay();
        updateMetrics();
        
        document.getElementById('btn-step').disabled = false;
        document.getElementById('btn-auto').disabled = false;
        const humanEvalStatusEl = document.getElementById('human-eval-status');
        if (humanEvalStatusEl) humanEvalStatusEl.textContent = '';
        
    } catch (error) {
        alert(`Error initializing: ${error.message}`);
    }
}

function getConfiguration() {
    const config = {};
    const envConfig = environmentConfigs[currentEnvironment];
    
    if (envConfig && envConfig.configFields) {
        envConfig.configFields.forEach(field => {
            const element = document.getElementById(field.id);
            if (element) {
                if (field.type === 'number' || field.type === 'range') {
                    config[field.id] = parseFloat(element.value);
                } else if (field.type === 'checkbox') {
                    config[field.id] = element.checked;
                } else {
                    config[field.id] = element.value;
                }
            }
        });
    } else {
        // Generic config
        const maxSteps = document.getElementById('max-steps');
        const seed = document.getElementById('random-seed');
        if (maxSteps) config.maxSteps = parseInt(maxSteps.value);
        if (seed && seed.value) config.seed = parseInt(seed.value);
    }
    
    config.agentStrategy = document.getElementById('agent-strategy').value;
    const agentModelEl = document.getElementById('agent-model');
    if (agentModelEl) {
        config.agentModel = agentModelEl.value;
    }
    
    // Add verifier configuration
    const verifierType = document.getElementById('verifier-type');
    if (verifierType && verifierType.value !== 'default') {
        if (verifierType.value.startsWith('jira_workflow:')) {
            config.verifier_config = {
                type: 'jira_workflow',
                metadata: { workflow_id: verifierType.value.split(':')[1] }
            };
        } else {
            config.verifier_config = {
                type: verifierType.value
            };
            if (verifierType.value === 'ensemble') {
                const verifierWeights = document.getElementById('verifier-weights');
                if (verifierWeights && verifierWeights.value.trim()) {
                    try {
                        const weights = JSON.parse(verifierWeights.value);
                        config.verifier_config.verifiers = weights;
                    } catch (e) {
                        console.warn('Invalid verifier weights JSON, using defaults:', e);
                    }
                }
            }
        }
    }

    return config;
}

function generateImagingQueue(config) {
    const queue = [];
    const urgentCount = Math.floor((config['queue-size'] || 15) * (config['high-urgency-pct'] || 30) / 100);
    
    for (let i = 0; i < (config['queue-size'] || 15); i++) {
        const isUrgent = i < urgentCount;
        const urgency = isUrgent ? Math.random() * 0.3 + 0.7 : Math.random() * 0.5 + 0.2;
        
        queue.push({
            id: `ORD-${String(i + 1).padStart(4, '0')}`,
            type: ['ct', 'mri', 'xray', 'ultrasound', 'pet'][Math.floor(Math.random() * 5)],
            urgency: urgency,
            value: (config['avg-order-value'] || 500) * (0.8 + Math.random() * 0.4),
            waitTime: 0
        });
    }
    
    return { queue: queue.sort((a, b) => b.urgency - a.urgency), processed: [], metrics: initializeMetrics() };
}

function generatePatientState(config) {
    return {
        patient: {
            severity: config['patient-severity'] || 'moderate',
            riskScore: (config['initial-risk'] || 50) / 100,
            conditions: config['num-conditions'] || 2
        },
        pathwayStep: 0,
        treatmentHistory: [],
        queue: [],
        processed: [],
        metrics: initializeMetrics()
    };
}

function generateICUState(config) {
    return {
        icuBeds: config['icu-beds'] || 20,
        stepdownBeds: config['stepdown-beds'] || 30,
        patientQueue: Array(config['patient-queue'] || 5).fill(0).map((_, i) => ({
            id: `PAT-${i+1}`,
            acuity: Math.random() * 0.5 + 0.5,
            waitTime: 0
        })),
        processed: [],
        metrics: initializeMetrics()
    };
}

function generateSurgeryState(config) {
    const queueSize = config['surgery-queue'] || 10;
    const urgentCount = Math.floor(queueSize * (config['urgent-pct'] || 25) / 100);
    
    return {
        queue: Array(queueSize).fill(0).map((_, i) => ({
            id: `SURG-${i+1}`,
            urgency: i < urgentCount ? Math.random() * 0.3 + 0.7 : Math.random() * 0.4 + 0.2,
            duration: Math.random() * 3 + 1,
            waitTime: 0
        })),
        orRooms: config['or-rooms'] || 10,
        scheduled: [],
        metrics: initializeMetrics()
    };
}

function generateScheduleState(config) {
    return {
        appointments: Array(config['appointments'] || 20).fill(0).map((_, i) => ({
            id: `APT-${i+1}`,
            priority: Math.random(),
            preferredTime: Math.random() > 0.5 ? 'morning' : 'afternoon'
        })),
        morningSlots: config['morning-slots'] || 10,
        afternoonSlots: config['afternoon-slots'] || 10,
        scheduled: [],
        metrics: initializeMetrics()
    };
}

function generateSepsisState(config) {
    return {
        sepsisProbability: (config['sepsis-probability'] || 60) / 100,
        sofaScore: config['initial-sofa'] || 8,
        timeSinceAdmission: config['time-since-admission'] || 2,
        interventions: [],
        metrics: initializeMetrics()
    };
}

function generateGenericState(config) {
    // Create a generic state based on category
    const env = allEnvironments.find(e => e.name === currentEnvironment);
    const category = env?.category || 'other';
    
    let queue = [];
    const queueSize = config['queue-size'] || config['patient-count'] || config['claims-count'] || config['population-size'] || 10;
    
    // Generate generic queue items
    for (let i = 0; i < queueSize; i++) {
        queue.push({
            id: `ITEM-${String(i + 1).padStart(4, '0')}`,
            priority: Math.random(),
            urgency: Math.random(),
            value: (config['avg-order-value'] || config['avg-claim-value'] || 500) * (0.8 + Math.random() * 0.4),
            waitTime: 0
        });
    }
    
    return {
        step: 0,
        queue: queue.sort((a, b) => (b.priority || b.urgency || 0) - (a.priority || a.urgency || 0)),
        processed: [],
        actionHistory: [],
        metrics: initializeMetrics()
    };
}

// Jira Issue Resolution: get_issue_summary_and_description → get_transitions → transition_issue
// Agent runs across all issues (cycles through on each Initialize)
const JIRA_ISSUE_RESOLUTION_ORDER = ['get_issue_summary_and_description', 'get_transitions', 'transition_issue'];
function generateJiraIssueResolutionState(config) {
    const issues = (jiraMockData && jiraMockData.issues) || [];
    const idx = issues.length ? (jiraIssueIndex % issues.length) : 0;
    const issue = issues[idx] || { key: 'PROJ-101', summary: 'Sample issue', description: 'No description', status: 'To Do', valid_transitions: [{ id: '31', name: 'Done' }] };
    return {
        jiraIssue: true,
        issue_key: issue.key,
        issue: { summary: issue.summary, description: issue.description, status: issue.status, valid_transitions: issue.valid_transitions || [] },
        workflow_step: 0,
        tool_sequence: [],
        expected_order: JIRA_ISSUE_RESOLUTION_ORDER,
        metrics: initializeMetrics()
    };
}
function processJiraIssueResolutionStep(state, action) {
    if (!state.jiraIssue || state.workflow_step >= state.expected_order.length) return state;
    const tool = state.expected_order[state.workflow_step];
    state.tool_sequence = [...(state.tool_sequence || []), tool];
    state.workflow_step = state.workflow_step + 1;
    if (tool === 'transition_issue') state.issue = { ...state.issue, status: 'Done' };
    const m = state.metrics || initializeMetrics();
    m.steps = state.workflow_step;
    const rcfg = jiraMockData && jiraMockData.reward_config;
    const stepReward = (rcfg && rcfg.status_reward_weights && state.issue && state.issue.status)
        ? (rcfg.status_reward_weights[state.issue.status] ?? rcfg.per_step_base?.issue_resolution ?? 0.50)
        : (rcfg?.per_step_base?.issue_resolution ?? 0.50);
    m.totalReward = (m.totalReward || 0) + stepReward;
    m.processed = state.workflow_step;
    state.metrics = m;
    return state;
}

// Jira Status Update: get_transitions → transition_issue
// Agent runs across all issues (cycles through on each Initialize)
const JIRA_STATUS_UPDATE_ORDER = ['get_transitions', 'transition_issue'];
const JIRA_STATUS_SCENARIO_TARGET = { in_progress_to_blocked: 'Blocked', in_progress_to_done: 'Done' };
function generateJiraStatusUpdateState(config) {
    const scenario = config['jira-scenario-status'] || 'in_progress_to_blocked';
    const targetStatus = JIRA_STATUS_SCENARIO_TARGET[scenario] || 'Blocked';
    let issues = (jiraMockData && jiraMockData.issues) || [];
    if (scenario === 'in_progress_to_blocked') {
        issues = issues.filter(i => (i.valid_transitions || []).some(t => t.name === 'Blocked'));
        if (issues.length === 0) issues = (jiraMockData && jiraMockData.issues) || [];
    }
    const idx = issues.length ? (jiraIssueIndex % issues.length) : 0;
    const issue = issues[idx] || { key: 'PROJ-101', summary: 'Sample issue', status: 'In Progress', valid_transitions: [{ id: '41', name: 'Blocked' }, { id: '31', name: 'Done' }] };
    return {
        jiraIssue: true,
        issue_key: issue.key,
        issue: { summary: issue.summary, status: issue.status, valid_transitions: issue.valid_transitions || [] },
        scenario,
        target_status: targetStatus,
        workflow_step: 0,
        tool_sequence: [],
        expected_order: JIRA_STATUS_UPDATE_ORDER,
        metrics: initializeMetrics()
    };
}
function processJiraStatusUpdateStep(state, action) {
    if (!state.jiraIssue || state.workflow_step >= state.expected_order.length) return state;
    const tool = state.expected_order[state.workflow_step];
    state.tool_sequence = [...(state.tool_sequence || []), tool];
    state.workflow_step = state.workflow_step + 1;
    if (tool === 'transition_issue') {
        const targetStatus = state.target_status || 'Done';
        state.issue = { ...state.issue, status: targetStatus };
    }
    const m = state.metrics || initializeMetrics();
    m.steps = state.workflow_step;
    const rcfg = jiraMockData && jiraMockData.reward_config;
    const stepReward = (rcfg && rcfg.status_reward_weights && state.issue && state.issue.status)
        ? (rcfg.status_reward_weights[state.issue.status] ?? rcfg.per_step_base?.status_update ?? 0.50)
        : (rcfg?.per_step_base?.status_update ?? 0.50);
    m.totalReward = (m.totalReward || 0) + stepReward;
    m.processed = state.workflow_step;
    state.metrics = m;
    return state;
}

// Jira Comment Management: add_comment → get_comments
// Agent runs across all issues (cycles through on each Initialize)
const JIRA_COMMENT_ORDER = ['add_comment', 'get_comments'];
function generateJiraCommentManagementState(config) {
    const issues = (jiraMockData && jiraMockData.issues) || [];
    const threads = (jiraMockData && jiraMockData.comment_threads) || {};
    const idx = issues.length ? (jiraIssueIndex % issues.length) : 0;
    const issue = issues[idx] || { key: 'PROJ-102', summary: 'Sample issue', status: 'In Progress' };
    const comments = threads[key] || [];
    return {
        jiraComment: true,
        issue_key: issue.key,
        issue_summary: issue.summary,
        issue: { status: issue.status },
        comments: [...comments],
        workflow_step: 0,
        tool_sequence: [],
        expected_order: JIRA_COMMENT_ORDER,
        metrics: initializeMetrics()
    };
}
function processJiraCommentManagementStep(state, action) {
    if (!state.jiraComment || state.workflow_step >= state.expected_order.length) return state;
    const tool = state.expected_order[state.workflow_step];
    state.tool_sequence = [...(state.tool_sequence || []), tool];
    if (tool === 'add_comment') {
        state.comments = [...(state.comments || []), { id: 'new', author: 'Agent', body: 'Compliance note added via workflow.' }];
    }
    state.workflow_step = state.workflow_step + 1;
    const m = state.metrics || initializeMetrics();
    m.steps = state.workflow_step;
    const rcfg = jiraMockData && jiraMockData.reward_config;
    const stepReward = (rcfg && rcfg.status_reward_weights && state.issue && state.issue.status)
        ? (rcfg.status_reward_weights[state.issue.status] ?? rcfg.per_step_base?.comment_management ?? 0.50)
        : (rcfg?.per_step_base?.comment_management ?? 0.50);
    m.totalReward = (m.totalReward || 0) + stepReward;
    m.processed = state.workflow_step;
    state.metrics = m;
    return state;
}

// Jira Subtask Management: scenarios for create / delete sub-tasks
const JIRA_SUBTASK_ORDER_CREATE = ['get_issue_summary_and_description', 'create_subtask'];
const JIRA_SUBTASK_ORDER_DELETE = ['get_subtasks', 'delete_subtask'];
function generateJiraSubtaskManagementState(config) {
    const issues = (jiraMockData && jiraMockData.issues) || [];
    const subtasksMap = (jiraMockData && jiraMockData.subtasks) || {};
    const useLive = !!config['jira-subtask-use-live'];
    const liveParentKey = (config['jira-subtask-parent-key'] || '').trim();

    // When using live Jira, anchor the simulation view on the live parent key
    let idx = issues.length ? (jiraIssueIndex % issues.length) : 0;
    let issue;
    if (useLive && liveParentKey) {
        issue = { key: liveParentKey, summary: `Live parent: ${liveParentKey}`, status: 'Unknown' };
    } else {
        issue = issues[idx] || { key: 'PROJ-101', summary: 'Sample issue', status: 'In Progress' };
    }

    const parentKey = issue.key;
    const existingSubtasks = subtasksMap[parentKey] ? [...subtasksMap[parentKey]] : [];
    const scenario = config['jira-subtask-scenario'] || 'create_subtask';
    let subtasks = existingSubtasks;
    // For delete scenario, ensure at least one subtask exists to delete
    if (scenario === 'delete_subtask' && subtasks.length === 0) {
        subtasks = [{ key: `${parentKey}-1`, summary: 'Existing subtask', description: '', parent_key: parentKey, status: 'To Do' }];
    }
    const expectedOrder = scenario === 'delete_subtask' ? JIRA_SUBTASK_ORDER_DELETE : JIRA_SUBTASK_ORDER_CREATE;
    return {
        jiraSubtask: true,
        scenario,
        issue_index: idx,
        issue_key: parentKey,
        issue_summary: issue.summary,
        issue: { status: issue.status },
        subtasks,
        workflow_step: 0,
        tool_sequence: [],
        expected_order: expectedOrder,
        metrics: initializeMetrics()
    };
}
function processJiraSubtaskManagementStep(state, action) {
    if (!state.jiraSubtask || state.workflow_step >= state.expected_order.length) return state;
    const tool = state.expected_order[state.workflow_step];
    state.tool_sequence = [...(state.tool_sequence || []), tool];
    const scenario = state.scenario || 'create_subtask';
    if (scenario === 'create_subtask' && tool === 'create_subtask') {
        const cfg = state.config || {};
        const summary = (cfg['jira-subtask-summary'] || '').trim() || 'New subtask';
        const description = (cfg['jira-subtask-description'] || '').trim() || '';
        const newSubtask = { key: `${state.issue_key}-${(state.subtasks?.length || 0) + 1}`, summary, description, parent_key: state.issue_key, status: 'To Do' };
        state.subtasks = [...(state.subtasks || []), newSubtask];
        // Log for download: capture all subtasks created across simulation runs
        const entry = {
            environment: 'JiraSubtaskManagement',
            action: 'create_subtask',
            parent_issue_key: state.issue_key,
            subtask_key: newSubtask.key,
            summary,
            description,
            status: newSubtask.status,
            created_at: new Date().toISOString()
        };
        jiraSubtaskLog.push(entry);
        updateJiraSubtaskConsole(entry);

        // Optional: call live Jira instance when configured
        const useLive = !!cfg['jira-subtask-use-live'];
        const liveParentKey = (cfg['jira-subtask-parent-key'] || '').trim();
        if (useLive) {
            if (!liveParentKey) {
                const warnEntry = {
                    ...entry,
                    live_created: false,
                    error: 'Live Jira enabled, but Live Jira parent issue key is empty.'
                };
                updateJiraSubtaskConsole(warnEntry);
                jiraSubtaskLog[jiraSubtaskLog.length - 1] = warnEntry;
                // Do not attempt live call without an explicit parent key
                return state;
            }
            const parent_key = liveParentKey;
            const body = {
                parent_key,
                summary,
                description
            };
            try {
                fetch(`${API_BASE}/jira/subtasks`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                })
                    .then(async (resp) => {
                        let data = null;
                        try {
                            data = await resp.json();
                        } catch (_) {
                            // ignore JSON errors
                        }
                        if (resp.ok && data && data.key) {
                            const enriched = { ...entry, live_created: true, jira_key: data.key };
                            updateJiraSubtaskConsole(enriched);
                            jiraSubtaskLog[jiraSubtaskLog.length - 1] = enriched;
                        } else {
                            const errMsg = (data && data.detail) || `HTTP ${resp.status}`;
                            const enriched = { ...entry, live_created: false, error: errMsg };
                            updateJiraSubtaskConsole(enriched);
                            jiraSubtaskLog[jiraSubtaskLog.length - 1] = enriched;
                        }
                    })
                    .catch((err) => {
                        const enriched = { ...entry, live_created: false, error: String(err) };
                        updateJiraSubtaskConsole(enriched);
                        jiraSubtaskLog[jiraSubtaskLog.length - 1] = enriched;
                    });
            } catch (err) {
                const enriched = { ...entry, live_created: false, error: String(err) };
                updateJiraSubtaskConsole(enriched);
                jiraSubtaskLog[jiraSubtaskLog.length - 1] = enriched;
            }
        }
    } else if (scenario === 'delete_subtask') {
        const cfg = state.config || {};
        if (tool === 'get_subtasks') {
            // No-op for now: state.subtasks already contains current subtasks
        } else if (tool === 'delete_subtask' && (state.subtasks || []).length > 0) {
            const subtasks = [...(state.subtasks || [])];
            const deleted = subtasks.pop();
            state.subtasks = subtasks;
            const entry = {
                environment: 'JiraSubtaskManagement',
                action: 'delete_subtask',
                parent_issue_key: state.issue_key,
                subtask_key: deleted.key,
                summary: deleted.summary,
                description: deleted.description || '',
                status: deleted.status,
                created_at: new Date().toISOString()
            };
            jiraSubtaskLog.push(entry);
            updateJiraSubtaskConsole(entry);

            // Optional: call live Jira to delete real sub-tasks when configured.
            // The "Live Jira parent issue key" field should contain the parent task key;
            // all of its subtasks will be deleted (parent is kept).
            const useLive = !!cfg['jira-subtask-use-live'];
            const parentKey = (cfg['jira-subtask-parent-key'] || '').trim();
            if (useLive) {
                if (!parentKey) {
                    const warnEntry = {
                        ...entry,
                        live_deleted: false,
                        error: 'Live Jira enabled, but Live Jira parent issue key is empty.'
                    };
                    updateJiraSubtaskConsole(warnEntry);
                    jiraSubtaskLog[jiraSubtaskLog.length - 1] = warnEntry;
                } else {
                    try {
                        fetch(`${API_BASE}/jira/issues/${encodeURIComponent(parentKey)}/subtasks`, {
                            method: 'DELETE'
                        })
                            .then(async (resp) => {
                                let data = null;
                                try {
                                    data = await resp.json();
                                } catch (_) {
                                    // ignore JSON errors (204 No Content etc.)
                                }
                                if (resp.ok) {
                                    const enriched = { ...entry, live_deleted: true, parent_issue_key: parentKey };
                                    updateJiraSubtaskConsole(enriched);
                                    jiraSubtaskLog[jiraSubtaskLog.length - 1] = enriched;
                                } else {
                                    const errMsg = (data && data.detail) || `HTTP ${resp.status}`;
                                    const enriched = { ...entry, live_deleted: false, error: errMsg };
                                    updateJiraSubtaskConsole(enriched);
                                    jiraSubtaskLog[jiraSubtaskLog.length - 1] = enriched;
                                }
                            })
                            .catch((err) => {
                                const enriched = { ...entry, live_deleted: false, error: String(err) };
                                updateJiraSubtaskConsole(enriched);
                                jiraSubtaskLog[jiraSubtaskLog.length - 1] = enriched;
                            });
                    } catch (err) {
                        const enriched = { ...entry, live_deleted: false, error: String(err) };
                        updateJiraSubtaskConsole(enriched);
                        jiraSubtaskLog[jiraSubtaskLog.length - 1] = enriched;
                    }
                }
            }
        }
    }
    state.workflow_step = state.workflow_step + 1;
    const m = state.metrics || initializeMetrics();
    m.steps = state.workflow_step;
    const rcfg = jiraMockData && jiraMockData.reward_config;
    const stepReward = (rcfg && rcfg.per_step_base && rcfg.per_step_base.subtask_management) ?? 0.50;
    m.totalReward = (m.totalReward || 0) + stepReward;
    m.processed = state.workflow_step;
    state.metrics = m;

    // Auto-cycle to next Jira issue once current workflow sequence is finished (within a single Initialize)
    if (state.workflow_step >= state.expected_order.length) {
        const issues = (jiraMockData && jiraMockData.issues) || [];
        if (issues.length) {
            const currentIdx = typeof state.issue_index === 'number' ? state.issue_index : 0;
            const nextIdx = (currentIdx + 1) % issues.length;
            const nextIssue = issues[nextIdx] || issues[0];
            const parentKey = nextIssue.key;
            const subtasksMap = (jiraMockData && jiraMockData.subtasks) || {};
            let subtasks = subtasksMap[parentKey] ? [...subtasksMap[parentKey]] : [];
            if (scenario === 'delete_subtask' && subtasks.length === 0) {
                subtasks = [{ key: `${parentKey}-1`, summary: 'Existing subtask', description: '', parent_key: parentKey, status: 'To Do' }];
            }
            state.issue_index = nextIdx;
            state.issue_key = parentKey;
            state.issue_summary = nextIssue.summary;
            state.issue = { status: nextIssue.status };
            state.subtasks = subtasks;
            state.workflow_step = 0;
            state.tool_sequence = [];
        }
    }

    return state;
}

function initializeMetrics() {
    return {
        queueLength: 0,
        urgentWaiting: 0,
        utilization: 0,
        processed: 0,
        waitTime: 0,
        revenue: 0,
        totalReward: 0.0,
        steps: 0
    };
}

function runStep() {
    if (!simulationState) return;
    
    const envConfig = environmentConfigs[currentEnvironment];
    if (envConfig && envConfig.processStep) {
        const result = envConfig.processStep(simulationState, getNextAction());
        simulationState = result;
    } else {
        // Generic step processing for any environment
        simulationState = processGenericStep(simulationState);
    }
    
    stepCount++;
    simulationState.step = stepCount;
    
    // Update metrics after step
    updateMetricsAfterStep();
    
    updateDisplay();
    updateMetrics();
    
    // Check if done
    const isDone = checkIfDone();
    if (isDone) {
        stopAutoRun();
        showFinalResults();
    }
}

function updateMetricsAfterStep() {
    if (!simulationState) return;
    const m = simulationState.metrics || {};
    
    // Update queue length if queue exists
    if (simulationState.queue) {
        m.queueLength = simulationState.queue.length;
        m.urgentWaiting = simulationState.queue.filter(item => (item.urgency || item.acuity || item.priority || 0) > 0.7).length;
        simulationState.queue.forEach(item => {
            if (item.waitTime !== undefined) item.waitTime++;
        });
    }
    if (simulationState.patientQueue) {
        m.queueLength = simulationState.patientQueue.length;
        simulationState.patientQueue.forEach(item => {
            if (item.waitTime !== undefined) item.waitTime++;
        });
    }
    if (simulationState.appointments) {
        m.queueLength = simulationState.appointments.length;
    }
    
    // Update processed count
    const processed = simulationState.processed || simulationState.scheduled || [];
    m.processed = processed.length;
    
    // Update utilization (generic calculation)
    if (m.processed > 0) {
        m.utilization = Math.min(100, (m.processed / (m.processed + (m.queueLength || 0))) * 100);
    }
    
    simulationState.metrics = m;
}

function checkIfDone() {
    if (!simulationState) return false;
    
    // Jira workflows: done when all expected steps completed
    if (simulationState.jiraIssue || simulationState.jiraComment || simulationState.jiraSubtask) {
        const expected = simulationState.expected_order || [];
        if (expected.length && simulationState.workflow_step >= expected.length) return true;
    }
    // Queue-based completion
    if (simulationState.queue && simulationState.queue.length === 0 && simulationState.processed?.length > 0) return true;
    if (simulationState.patientQueue && simulationState.patientQueue.length === 0 && simulationState.processed?.length > 0) return true;
    if (simulationState.appointments && simulationState.appointments.length === 0 && simulationState.scheduled?.length > 0) return true;
    if (stepCount >= 100) return true; // Max steps reached
    
    return false;
}

function getNextAction() {
    if (!simulationState) return 0;
    
    // Simplified action selection - in production, use trained policy
    const strategy = simulationState.config?.agentStrategy || 'random';
    
    // Strategy-based action selection
    if (strategy === 'random') {
        return Math.floor(Math.random() * 5);
    } else if (strategy === 'urgency_first') {
        return 1; // Prioritize urgent
    } else if (strategy === 'value_first') {
        return 2; // Prioritize high value
    } else {
        return 3; // Balanced/RL optimized
    }
}

function processImagingStep(state, action) {
    if (state.queue && state.queue.length > 0) {
        const order = state.queue.shift();
        state.processed.push({ ...order, processedAt: stepCount, priority: determinePriority(order, state.config?.agentStrategy) });
        state.metrics.processed++;
        state.metrics.revenue = (state.metrics.revenue || 0) + (order.value || 0);
        state.metrics.queueLength = state.queue.length;
        state.metrics.urgentWaiting = state.queue.filter(o => (o.urgency || 0) > 0.7).length;
        state.metrics.totalReward = (state.metrics.totalReward || 0) + 0.1;
        state.queue.forEach(o => { if (o.waitTime !== undefined) o.waitTime++; });
    }
    return state;
}

function determinePriority(item, strategy) {
    if (!item) return 'routine';
    const urgency = item.urgency || item.acuity || item.priority || 0.5;
    if (urgency > 0.8) return 'stat';
    if (urgency > 0.6) return 'urgent';
    if (urgency > 0.4) return 'routine';
    return 'defer';
}

function processTreatmentStep(state, action) {
    state.pathwayStep++;
    state.treatmentHistory.push({ step: state.pathwayStep, action });
    state.patient.riskScore = Math.max(0, state.patient.riskScore - 0.05);
    state.metrics.processed = state.pathwayStep;
    state.metrics.totalReward += 0.1;
    return state;
}

function processSepsisStep(state, action) {
    state.interventions.push({ step: stepCount, action });
    state.sepsisProbability = Math.max(0, state.sepsisProbability - 0.1);
    state.sofaScore = Math.max(0, state.sofaScore - 1);
    state.metrics.processed = state.interventions.length;
    state.metrics.totalReward += 0.15;
    return state;
}

function processICUStep(state, action) {
    if (state.patientQueue && state.patientQueue.length > 0) {
        const patient = state.patientQueue.shift();
        state.processed.push({ ...patient, processedAt: stepCount });
        state.metrics.processed++;
        state.metrics.queueLength = state.patientQueue.length;
        state.metrics.totalReward += 0.12;
    }
    return state;
}

function processSurgeryStep(state, action) {
    if (state.queue && state.queue.length > 0) {
        const surgery = state.queue.shift();
        state.scheduled.push({ ...surgery, scheduledAt: stepCount });
        state.metrics.processed++;
        state.metrics.queueLength = state.queue.length;
        state.metrics.totalReward += 0.1;
    }
    return state;
}

function processScheduleStep(state, action) {
    if (state.appointments && state.appointments.length > 0) {
        const apt = state.appointments.shift();
        state.scheduled.push({ ...apt, scheduledAt: stepCount });
        state.metrics.processed++;
        state.metrics.queueLength = state.appointments.length;
        state.metrics.totalReward += 0.08;
    }
    return state;
}

function processGenericStep(state) {
    state.step = state.step || 0;
    state.step++;
    state.actionHistory = state.actionHistory || [];
    state.actionHistory.push({ step: state.step, action: getNextAction() });
    
    const m = state.metrics || initializeMetrics();
    m.steps = state.step;
    m.totalReward = (m.totalReward || 0) + (Math.random() * 0.1 - 0.05); // Small reward variation
    m.processed = state.actionHistory.length;
    
    state.metrics = m;
    return state;
}

function updateDisplay() {
    if (!simulationState) return;
    
    // Jira sample use cases: issue resolution or comment management
    if (simulationState.jiraIssue) {
        updateJiraIssueDisplay();
    } else if (simulationState.jiraComment) {
        updateJiraCommentDisplay();
    } else if (simulationState.jiraSubtask) {
        updateJiraSubtaskDisplay();
    } else if (simulationState.queue && Array.isArray(simulationState.queue)) {
        updateQueueBasedDisplay();
    } else if (simulationState.patientQueue && Array.isArray(simulationState.patientQueue)) {
        updateQueueBasedDisplay('patientQueue');
    } else if (simulationState.appointments && Array.isArray(simulationState.appointments)) {
        updateQueueBasedDisplay('appointments');
    } else {
        updateGenericDisplay();
    }
    
    // Update action display
    updateActionDisplayGeneric();
}

function updateJiraIssueDisplay() {
    const stateDiv = document.getElementById('state-display');
    const historyDiv = document.getElementById('action-history');
    const issue = simulationState.issue || {};
    const seq = simulationState.tool_sequence || [];
    const expected = simulationState.expected_order || [];
    stateDiv.innerHTML = `
        <div class="jira-issue-card" style="background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 8px; padding: 0.75rem; margin-bottom: 0.5rem;">
            <div style="font-weight: 600; color: #0369a1;">${simulationState.issue_key || 'PROJ-XXX'}</div>
            <div style="font-size: 0.9rem; margin-top: 0.25rem;">${issue.summary || '—'}</div>
            <div style="font-size: 0.8rem; color: #64748b; margin-top: 0.25rem;">Status: <strong>${issue.status || '—'}</strong></div>
            ${(issue.valid_transitions && issue.valid_transitions.length) ? `<div style="font-size: 0.75rem; margin-top: 0.25rem;">Transitions: ${issue.valid_transitions.map(t => t.name).join(', ')}</div>` : ''}
        </div>
        <div style="font-size: 0.85rem;"><strong>Workflow steps:</strong> ${expected.map((t, i) => seq.includes(t) ? `<span style="color: #16a34a;">✓ ${t}</span>` : `<span style="color: #94a3b8;">${t}</span>`).join(' → ')}</div>
    `;
    historyDiv.innerHTML = seq.length ? seq.map((t, i) => `<div class="order-item"><div class="order-id">Step ${i + 1}</div><div class="order-details">${t}</div></div>`).join('') : '<div class="empty-state">No steps yet. Click Step to run workflow.</div>';
}

function updateJiraCommentDisplay() {
    const stateDiv = document.getElementById('state-display');
    const historyDiv = document.getElementById('action-history');
    const comments = simulationState.comments || [];
    const seq = simulationState.tool_sequence || [];
    stateDiv.innerHTML = `
        <div class="jira-issue-card" style="background: #f0fdf4; border: 1px solid #22c55e; border-radius: 8px; padding: 0.75rem; margin-bottom: 0.5rem;">
            <div style="font-weight: 600; color: #15803d;">${simulationState.issue_key || 'PROJ-XXX'}</div>
            <div style="font-size: 0.9rem; margin-top: 0.25rem;">${simulationState.issue_summary || '—'}</div>
        </div>
        <div style="font-size: 0.85rem; margin-top: 0.5rem;"><strong>Comment thread (${comments.length}):</strong></div>
        ${comments.length ? comments.map(c => `<div style="font-size: 0.8rem; margin-top: 0.35rem; padding: 0.35rem; background: #f8fafc; border-radius: 4px;"><strong>${c.author}</strong>: ${(c.body || '').substring(0, 120)}${(c.body && c.body.length > 120) ? '…' : ''}</div>`).join('') : '<div class="empty-state">No comments yet.</div>'}
        <div style="font-size: 0.85rem; margin-top: 0.5rem;"><strong>Steps:</strong> ${seq.join(' → ') || '—'}</div>
    `;
    historyDiv.innerHTML = seq.length ? seq.map((t, i) => `<div class="order-item"><div class="order-id">Step ${i + 1}</div><div class="order-details">${t}</div></div>`).join('') : '<div class="empty-state">No steps yet. Click Step to add comment and get thread.</div>';
}

function updateJiraSubtaskDisplay() {
    const stateDiv = document.getElementById('state-display');
    const historyDiv = document.getElementById('action-history');
    const subtasks = simulationState.subtasks || [];
    const seq = simulationState.tool_sequence || [];
    const expected = simulationState.expected_order || [];
    stateDiv.innerHTML = `
        <div class="jira-issue-card" style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 0.75rem; margin-bottom: 0.5rem;">
            <div style="font-weight: 600; color: #b45309;">${simulationState.issue_key || 'PROJ-XXX'} (parent)</div>
            <div style="font-size: 0.9rem; margin-top: 0.25rem;">${simulationState.issue_summary || '—'}</div>
        </div>
        <div style="font-size: 0.85rem; margin-top: 0.5rem;"><strong>Subtasks (${subtasks.length}):</strong></div>
        ${subtasks.length ? subtasks.map(s => `<div style="font-size: 0.8rem; margin-top: 0.35rem; padding: 0.35rem; background: #fffbeb; border-radius: 4px;"><strong>${s.key || '—'}</strong>: ${(s.summary || '').substring(0, 80)}</div>`).join('') : '<div class="empty-state">No subtasks yet.</div>'}
        <div style="font-size: 0.85rem; margin-top: 0.5rem;"><strong>Steps:</strong> ${expected.map((t, i) => seq.includes(t) ? `<span style="color: #16a34a;">✓ ${t}</span>` : `<span style="color: #94a3b8;">${t}</span>`).join(' → ')}</div>
    `;
    historyDiv.innerHTML = seq.length ? seq.map((t, i) => `<div class="order-item"><div class="order-id">Step ${i + 1}</div><div class="order-details">${t}</div></div>`).join('') : '<div class="empty-state">No steps yet. Click Step to add subtask under parent issue.</div>';
}

function updateQueueBasedDisplay(queueKey = 'queue') {
    const queue = simulationState[queueKey] || [];
    const stateDiv = document.getElementById('state-display');
    
    if (queue.length > 0) {
        stateDiv.innerHTML = queue.map((item, idx) => {
            const urgency = item.urgency || item.acuity || item.priority || 0.5;
            const urgencyClass = urgency > 0.8 ? 'urgent' : urgency > 0.6 ? 'high' : urgency > 0.4 ? 'medium' : 'low';
            const badgeClass = `badge-${urgencyClass}`;
            const priorityText = urgency > 0.8 ? 'STAT' : urgency > 0.6 ? 'URGENT' : urgency > 0.4 ? 'ROUTINE' : 'LOW';
            
            return `
                <div class="order-item ${urgencyClass}">
                    <div class="order-info">
                        <div class="order-id">${item.id || `Item-${idx+1}`}</div>
                        <div class="order-details">
                            ${item.type ? `Type: ${item.type.toUpperCase()} | ` : ''}
                            ${item.value ? `Value: $${Math.round(item.value)} | ` : ''}
                            ${item.waitTime !== undefined ? `Wait: ${item.waitTime} min` : ''}
                            ${item.duration ? `Duration: ${item.duration.toFixed(1)}h` : ''}
                        </div>
                    </div>
                    <span class="order-badge ${badgeClass}">${priorityText}</span>
                </div>
            `;
        }).join('');
    } else {
        stateDiv.innerHTML = '<div class="empty-state">Queue is empty</div>';
    }
    
    const historyDiv = document.getElementById('action-history');
    const processed = simulationState.processed || simulationState.scheduled || [];
    if (processed.length > 0) {
        const recent = processed.slice(-5).reverse();
        historyDiv.innerHTML = recent.map(item => `
            <div class="order-item">
                <div class="order-info">
                    <div class="order-id">${item.id || 'Processed'}</div>
                    <div class="order-details">Processed at step ${item.processedAt || item.scheduledAt || 'N/A'}</div>
                </div>
                <span class="order-badge badge-low">PROCESSED</span>
            </div>
        `).join('');
    } else {
        historyDiv.innerHTML = '<div class="empty-state">No items processed yet</div>';
    }
}

function updateActionDisplayGeneric() {
    const actionDiv = document.getElementById('action-display');
    if (simulationState && stepCount > 0) {
        const strategy = simulationState.config?.agentStrategy || 'balanced';
        actionDiv.innerHTML = `
            <div class="action-priority">${strategy.toUpperCase()}</div>
            <div class="action-description">
                Step: ${stepCount}<br>
                Environment: ${formatEnvironmentName(currentEnvironment)}<br>
                Strategy: ${strategy}
            </div>
        `;
    } else {
        actionDiv.innerHTML = '<div class="empty-state">Waiting for initialization...</div>';
    }
}

function updateGenericDisplay() {
    const stateDiv = document.getElementById('state-display');
    stateDiv.innerHTML = `
        <div class="state-info">
            <div><strong>Step:</strong> ${simulationState.step || 0}</div>
            <div><strong>Environment:</strong> ${formatEnvironmentName(currentEnvironment)}</div>
            <div><strong>Status:</strong> Running</div>
        </div>
    `;
    
    const historyDiv = document.getElementById('action-history');
    if (simulationState.actionHistory && simulationState.actionHistory.length > 0) {
        const recent = simulationState.actionHistory.slice(-5).reverse();
        historyDiv.innerHTML = recent.map(item => `
            <div class="order-item">
                <div class="order-info">
                    <div class="order-id">Step ${item.step}</div>
                    <div class="order-details">Action: ${item.action}</div>
                </div>
            </div>
        `).join('');
    } else {
        historyDiv.innerHTML = '<div class="empty-state">No actions taken yet</div>';
    }
}

function updateMetrics() {
    if (!simulationState) return;
    
    const m = simulationState.metrics || {};
    
    document.getElementById('metric-steps').textContent = stepCount;
    document.getElementById('metric-reward').textContent = (m.totalReward || 0).toFixed(2);
    
    // Update dynamic metrics based on environment type
    updateDynamicMetrics(m);
}

function updateDynamicMetrics(m) {
    // Update metrics grid with environment-specific metrics
    const metricsGrid = document.getElementById('metrics-grid');
    
    // Clear existing metric cards (except steps and reward)
    const existingCards = metricsGrid.querySelectorAll('.metric-card');
    existingCards.forEach((card, idx) => {
        if (idx >= 2) card.remove(); // Keep first two (steps and reward)
    });
    
    // RL-focused metrics only: Step Count and Total Reward are in the grid; no extra cards for queue/revenue/utilization
}

function addMetricCard(label, value, trendId) {
    const metricsGrid = document.getElementById('metrics-grid');
    const card = document.createElement('div');
    card.className = 'metric-card';
    card.innerHTML = `
        <div class="metric-label">${label}</div>
        <div class="metric-value">${value}</div>
        <div class="metric-trend" id="${trendId}">-</div>
    `;
    metricsGrid.appendChild(card);
}

function startAutoRun() {
    const speed = document.getElementById('sim-speed').value;
    const delays = { slow: 1000, medium: 500, fast: 200 };
    
    document.getElementById('btn-auto').disabled = true;
    document.getElementById('btn-step').disabled = true;
    
    simulationInterval = setInterval(() => {
        runStep();
    }, delays[speed]);
}

function stopAutoRun() {
    if (simulationInterval) {
        clearInterval(simulationInterval);
        simulationInterval = null;
    }
    document.getElementById('btn-auto').disabled = false;
    document.getElementById('btn-step').disabled = false;
}

function resetSimulation() {
    stopAutoRun();
    simulationState = null;
    stepCount = 0;
    metricsHistory = [];

    document.getElementById('state-display').innerHTML = '<div class="empty-state">Click "Initialize Environment" to start</div>';
    document.getElementById('action-history').innerHTML = '<div class="empty-state">No actions taken yet</div>';
    document.getElementById('action-display').innerHTML = '<div class="empty-state">Waiting for initialization...</div>';

    updateMetrics();
    showFinalResults();
    const humanEvalStatusEl = document.getElementById('human-eval-status');
    if (humanEvalStatusEl) humanEvalStatusEl.textContent = '';
    // Do not clear jiraSubtaskLog here; it should track the full session across resets
}

function downloadJiraSubtaskLog() {
    if (!jiraSubtaskLog.length) {
        alert('No Jira subtasks have been created in this simulation session yet.');
        return;
    }
    const payload = {
        generated_at: new Date().toISOString(),
        environment: 'JiraSubtaskManagement',
        total_subtasks: jiraSubtaskLog.length,
        subtasks: jiraSubtaskLog
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const ts = new Date().toISOString().replace(/[:.]/g, '-');
    a.href = url;
    a.download = `jira_subtask_log_${ts}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function updateJiraSubtaskConsole(entry) {
    try {
        const el = document.getElementById('jira-subtask-console-output');
        if (!el) return;
        const line = `[${entry.created_at}] ${entry.action} | parent=${entry.parent_issue_key} | subtask=${entry.subtask_key} | ${entry.summary}`;
        const existing = el.textContent ? el.textContent.split('\n') : [];
        existing.push(line);
        // Keep last 50 lines for readability
        const trimmed = existing.slice(-50);
        el.textContent = trimmed.join('\n');
    } catch (e) {
        console.warn('Failed to update Jira subtask console output:', e);
    }
}

function showFinalResults() {
    const runSummaryEl = document.getElementById('results-run-summary');
    const laggingEl = document.getElementById('results-lagging');
    if (!runSummaryEl || !laggingEl) return;

    if (!simulationState) {
        runSummaryEl.textContent = '-';
        laggingEl.textContent = '-';
        return;
    }
    
    const m = simulationState.metrics || {};
    const isComplete = (simulationState.queue?.length === 0 || 
                        simulationState.patientQueue?.length === 0 ||
                        simulationState.appointments?.length === 0) && 
                       (simulationState.processed?.length > 0 || simulationState.scheduled?.length > 0);
    const totalReward = m.totalReward ?? 0;
    const avgRewardPerStep = stepCount > 0 ? (totalReward / stepCount).toFixed(3) : '—';
    
    runSummaryEl.innerHTML = `
        <strong>Steps completed:</strong> ${stepCount}<br>
        <strong>Total reward:</strong> ${totalReward.toFixed(2)}<br>
        <strong>Episode completed:</strong> ${isComplete ? 'Yes' : 'No'}
    `;
    laggingEl.innerHTML = `
        <strong>Average reward per step:</strong> ${avgRewardPerStep}<br>
        <strong>Steps to complete:</strong> ${isComplete ? stepCount : '—'}
        <div class="metric-reasoning" style="margin-top: 0.75rem; padding: 0.5rem; background: rgba(37,99,235,0.06); border-radius: 6px; font-size: 0.82rem; color: var(--text-secondary); line-height: 1.45;">
            Lagging indicators help compare strategies and assess convergence over multiple runs.
        </div>
    `;
}

