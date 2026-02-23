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
    }
    // Generic config will be used for environments not in this list
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadEnvironments();
    setupEventListeners();
    setupRangeInputs();
    setupVerifierControls();
});

// Recommended verifier by software system (aligned with catalog/training)
function getVerifierRecommendationForSystem(system) {
    if (!system || system === 'all') {
        return { type: 'ensemble', weights: { clinical: 0.35, operational: 0.3, financial: 0.2, compliance: 0.15 } };
    }
    const s = system.toLowerCase();
    if (s.includes('epic') || s.includes('cerner') || s.includes('allscripts') || s.includes('meditech')) {
        return { type: 'ensemble', weights: { clinical: 0.45, operational: 0.25, financial: 0.15, compliance: 0.15 } };
    }
    if (s.includes('philips') || s.includes('ge healthcare')) {
        return { type: 'ensemble', weights: { clinical: 0.3, operational: 0.45, financial: 0.15, compliance: 0.1 } };
    }
    if (s.includes('change healthcare')) {
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
    if (verifierWeightsInput) verifierWeightsInput.value = JSON.stringify(rec.weights, null, 2);
    if (verifierTypeSelect.value === 'ensemble') {
        const g = document.getElementById('verifier-weights-group');
        if (g) g.style.display = 'block';
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
        return envSystems.includes(system);
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
    
    // Load environment-specific configuration
    loadEnvironmentConfig(envName);
}

function loadEnvironmentConfig(envName) {
    const configDiv = document.getElementById('dynamic-config');
    const config = environmentConfigs[envName];
    
    if (!config) {
        // Generic configuration for environments without specific config
        configDiv.innerHTML = `
            <div class="form-group">
                <label>Max Steps:</label>
                <input type="number" id="max-steps" value="100" min="10" max="1000" />
            </div>
            <div class="form-group">
                <label>Random Seed (optional):</label>
                <input type="number" id="random-seed" value="" placeholder="Auto" />
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
            return `
                <div class="form-group">
                    <label>${field.label} <span class="tooltip-icon" title="${tooltip}">ℹ️</span></label>
                    <select id="${field.id}" title="${tooltip}">
                        ${field.options.map(opt => `<option value="${opt}" ${opt === field.value ? 'selected' : ''}>${opt.charAt(0).toUpperCase() + opt.slice(1)}</option>`).join('')}
                    </select>
                </div>
            `;
        } else {
            return `
                <div class="form-group">
                    <label>${field.label} <span class="tooltip-icon" title="${tooltip}">ℹ️</span></label>
                    <input type="${field.type}" id="${field.id}" value="${field.value}" min="${field.min || ''}" max="${field.max || ''}" title="${tooltip}" />
                </div>
            `;
        }
    }).join('');
    
    // Setup range inputs
    setupRangeInputs();
}

function getDefaultTooltip(fieldId, label) {
    const tooltips = {
        'queue-size': 'Number of items (orders, patients, appointments) currently in the queue waiting to be processed. Larger queues represent busier healthcare settings and test the RL agent\'s ability to prioritize effectively.',
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
        'afternoon-slots': 'Number of afternoon appointment slots available (5-20). Tests preference matching and capacity management.'
    };
    
    return tooltips[fieldId] || `Configure ${label.toLowerCase()}. Adjust this parameter to simulate different healthcare scenarios and test the RL agent's decision-making capabilities.`;
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
            if (config.verifier_config.verifiers) {
                params.append('verifier_config', JSON.stringify({
                    verifiers: config.verifier_config.verifiers
                }));
            }
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
        showRecommendations();
        
        document.getElementById('btn-step').disabled = false;
        document.getElementById('btn-auto').disabled = false;
        
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
                config[field.id] = field.type === 'number' || field.type === 'range' ? 
                    parseFloat(element.value) : element.value;
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
    
    // Add verifier configuration
    const verifierType = document.getElementById('verifier-type');
    if (verifierType && verifierType.value !== 'default') {
        config.verifier_config = {
            type: verifierType.value
        };
        
        // Add weights if ensemble and weights are provided
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
    showRecommendations();
    
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
    
    // Check various completion conditions
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
    
    // Check if environment has queue-based display
    if (simulationState.queue && Array.isArray(simulationState.queue)) {
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
    
    // Update KPI display
    updateKPIDisplay();
}

function updateDynamicMetrics(m) {
    // Update metrics grid with environment-specific metrics
    const metricsGrid = document.getElementById('metrics-grid');
    
    // Clear existing metric cards (except steps and reward)
    const existingCards = metricsGrid.querySelectorAll('.metric-card');
    existingCards.forEach((card, idx) => {
        if (idx >= 2) card.remove(); // Keep first two (steps and reward)
    });
    
    // Add environment-specific metrics
    if (m.queueLength !== undefined) {
        addMetricCard('Queue Length', m.queueLength, 'trend-queue');
    }
    if (m.urgentWaiting !== undefined) {
        addMetricCard('Urgent Waiting', m.urgentWaiting, 'trend-urgent');
    }
    if (m.utilization !== undefined) {
        addMetricCard('Utilization', `${m.utilization.toFixed(0)}%`, 'trend-utilization');
    }
    if (m.processed !== undefined) {
        addMetricCard('Processed', m.processed, 'trend-processed');
    }
    if (m.waitTime !== undefined) {
        addMetricCard('Wait Time', `${m.waitTime} min`, 'trend-wait');
    }
    if (m.revenue !== undefined) {
        addMetricCard('Revenue', `$${Math.round(m.revenue)}`, 'trend-revenue');
    }
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

async function updateKPIDisplay() {
    try {
        const response = await fetch(`${API_BASE}/kpis/${currentEnvironment}`);
        if (response.ok) {
            const data = await response.json();
            const kpis = data.kpis || {};
            
            const kpiDiv = document.getElementById('kpi-display');
            kpiDiv.innerHTML = `
                <div class="kpi-item"><strong>Clinical:</strong> ${JSON.stringify(kpis.clinical_outcomes || {})}</div>
                <div class="kpi-item"><strong>Efficiency:</strong> ${JSON.stringify(kpis.operational_efficiency || {})}</div>
                <div class="kpi-item"><strong>Financial:</strong> ${JSON.stringify(kpis.financial_metrics || {})}</div>
            `;
        }
    } catch (error) {
        console.error('Error fetching KPIs:', error);
    }
}

function showRecommendations() {
    if (!simulationState) return;
    
    const recommendations = [];
    const m = simulationState.metrics || {};
    
    if (m.urgentWaiting > 3) {
        recommendations.push('⚠️ High number of urgent items waiting. Consider prioritizing immediately.');
    }
    
    if (m.utilization < 50) {
        recommendations.push('💡 Resource utilization is low. You can process more items.');
    }
    
    if (m.waitTime > 30) {
        recommendations.push('⏱️ Average wait time is high. Consider increasing capacity.');
    }
    
    const recDiv = document.getElementById('recommendations-list');
    if (recommendations.length === 0) {
        recDiv.innerHTML = '<div class="empty-state">System operating optimally</div>';
    } else {
        recDiv.innerHTML = recommendations.map(rec => 
            `<div class="recommendation-item">${rec}</div>`
        ).join('');
    }
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
    showRecommendations();
    showFinalResults();
}

function showFinalResults() {
    if (!simulationState) {
        ['results-clinical', 'results-efficiency', 'results-financial', 'results-roi'].forEach(id => {
            document.getElementById(id).textContent = '-';
        });
        return;
    }
    
    const m = simulationState.metrics || {};
    const env = allEnvironments.find(e => e.name === currentEnvironment);
    const isComplete = (simulationState.queue?.length === 0 || 
                        simulationState.patientQueue?.length === 0 ||
                        simulationState.appointments?.length === 0) && 
                       (simulationState.processed?.length > 0 || simulationState.scheduled?.length > 0);
    
    // Clinical Outcomes
    const clinicalHtml = `
        <strong>Steps Completed:</strong> ${stepCount}<br>
        <strong>Status:</strong> ${isComplete ? 'Complete' : 'In Progress'}<br>
        ${m.urgentWaiting !== undefined ? `<strong>Urgent Waiting:</strong> ${m.urgentWaiting}` : ''}
    `;
    document.getElementById('results-clinical').innerHTML = clinicalHtml;
    
    // Operational Efficiency
    const efficiencyHtml = `
        <strong>Total Steps:</strong> ${stepCount}<br>
        <strong>Items Processed:</strong> ${m.processed || 0}<br>
        ${m.utilization !== undefined ? `<strong>Utilization:</strong> ${m.utilization.toFixed(1)}%` : ''}
    `;
    document.getElementById('results-efficiency').innerHTML = efficiencyHtml;
    
    // Financial Impact
    const financialHtml = `
        <strong>Total Reward:</strong> ${(m.totalReward || 0).toFixed(2)}<br>
        ${m.revenue !== undefined ? `<strong>Revenue:</strong> $${Math.round(m.revenue)}` : ''}
        ${m.revenue && stepCount > 0 ? `<strong>Revenue/Hour:</strong> $${Math.round(m.revenue / (stepCount / 60)) || 0}` : ''}
    `;
    document.getElementById('results-financial').innerHTML = financialHtml;
    
    // ROI Assessment
    const strategy = simulationState.config?.agentStrategy || 'N/A';
    const efficiencyLevel = m.utilization > 70 ? 'High' : m.utilization > 50 ? 'Medium' : 'Low';
    const roiHtml = `
        <strong>Strategy:</strong> ${strategy}<br>
        <strong>Efficiency:</strong> ${efficiencyLevel}<br>
        <strong>Assessment:</strong> ${stepCount > 0 ? (isComplete ? '✅ Simulation completed successfully' : '🔄 Simulation in progress') : '⏸️ Not started'}
    `;
    document.getElementById('results-roi').innerHTML = roiHtml;
}

