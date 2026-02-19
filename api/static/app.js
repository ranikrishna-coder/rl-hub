// Environment Catalog Application

const API_BASE = 'http://localhost:8000';
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
        description: 'Reconciles data across multiple healthcare systems to ensure data integrity and consistency.',
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
    }
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadEnvironments();
    setupEventListeners();
});

async function loadEnvironments() {
    try {
        const response = await fetch(`${API_BASE}/environments`);
        if (!response.ok) throw new Error('Failed to load environments');
        
        const data = await response.json();
        allEnvironments = data.environments || [];
        
        // Enhance with details
        allEnvironments = allEnvironments.map(env => ({
            ...env,
            ...(environmentDetails[env.name] || {
                category: env.category || 'other',
                description: 'RL environment for optimization',
                stateFeatures: 15,
                actionType: 'Discrete',
                actionSpace: 5,
                kpis: ['Clinical Outcomes', 'Operational Efficiency', 'Financial Metrics']
            })
        }));
        
        filteredEnvironments = allEnvironments;
        renderEnvironments();
        document.getElementById('loading').style.display = 'none';
    } catch (error) {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('error').style.display = 'block';
        document.getElementById('error').textContent = `Error: ${error.message}. Make sure the API server is running on port 8000.`;
    }
}

function setupEventListeners() {
    // Search
    document.getElementById('search-input').addEventListener('input', (e) => {
        filterEnvironments(e.target.value, getActiveCategory());
    });
    
    // Category filters
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
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
            description: env.description || 'RL environment',
            system: env.system || 'Multiple'
        });
    });
    
    helpBody.innerHTML = `
        <h1 style="margin-bottom: 2rem;">📚 Help & Documentation</h1>
        
        <div class="help-section" style="margin-bottom: 3rem;">
            <h2 style="color: var(--primary-color); margin-bottom: 1.5rem; border-bottom: 2px solid var(--border-color); padding-bottom: 0.5rem;">🏥 Healthcare Systems Integrated</h2>
            <p style="margin-bottom: 1.5rem; color: var(--text-secondary);">
                This platform integrates with the following major healthcare systems, providing digital twin simulations 
                and RL environments for optimization:
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
                                    <strong>System:</strong> ${workflow.system}
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
                    <li><strong>Browse Environments:</strong> Use the search and filter options to find RL environments relevant to your healthcare system.</li>
                    <li><strong>View Details:</strong> Click "View Details" on any environment card to learn about its capabilities and use cases.</li>
                    <li><strong>Test with Simulation:</strong> Click "🧪 Simulation" to open the interactive console and test the environment with your parameters.</li>
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

function filterEnvironments(searchTerm, category) {
    filteredEnvironments = allEnvironments.filter(env => {
        const matchesSearch = !searchTerm || 
            env.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (env.description && env.description.toLowerCase().includes(searchTerm.toLowerCase()));
        
        const matchesCategory = category === 'all' || env.category === category;
        
        return matchesSearch && matchesCategory;
    });
    
    renderEnvironments();
}

function renderEnvironments() {
    const grid = document.getElementById('environments-grid');
    
    if (filteredEnvironments.length === 0) {
        grid.innerHTML = '<div class="error">No environments found matching your criteria.</div>';
        return;
    }
    
    grid.innerHTML = filteredEnvironments.map(env => createEnvCard(env)).join('');
    
    // Add event listeners to buttons
    document.querySelectorAll('.btn-view-details').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const envName = e.target.dataset.env;
            showEnvironmentDetails(envName);
        });
    });
    
    document.querySelectorAll('.btn-test-env').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const envName = e.target.dataset.env;
            testEnvironment(envName);
        });
    });
}

function formatEnvironmentName(name) {
    // Add spaces before capital letters
    return name.replace(/([A-Z])/g, ' $1').trim();
}

function createEnvCard(env) {
    const categoryClass = `category-${env.category}`;
    const multiAgentBadge = env.multi_agent ? '<span style="background: #fecdd3; color: #991b1b; padding: 0.25rem 0.5rem; border-radius: 12px; font-size: 0.7rem; margin-left: 0.5rem;">Multi-Agent</span>' : '';
    const displayName = formatEnvironmentName(env.name);
    
    return `
        <div class="env-card">
            <div class="env-card-header">
                <div>
                    <div class="env-name">${displayName}${multiAgentBadge}</div>
                    <span class="env-category ${categoryClass}">${env.category || 'other'}</span>
                </div>
            </div>
            <div class="env-description">
                ${env.description || 'RL environment for optimization'}
            </div>
            <div class="env-details">
                <div class="detail-item">
                    <span class="detail-label">System:</span>
                    <span class="detail-value">${env.system || 'Multiple'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">State Features:</span>
                    <span class="detail-value">${env.stateFeatures || 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Action Type:</span>
                    <span class="detail-value">${env.actionType || 'Discrete'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Actions:</span>
                    <span class="detail-value">${env.actionSpace || 'N/A'}</span>
                </div>
            </div>
            <div class="env-actions">
                <button class="btn btn-primary btn-view-details" data-env="${env.name}">
                    View Details
                </button>
                <button class="btn btn-secondary" onclick="window.location.href='/test-console?env=${env.name}'">
                    🧪 Simulation
                </button>
            </div>
        </div>
    `;
}

function getDefaultWhatItDoes(category, envName) {
    const categoryDescriptions = {
        'clinical': `
            <p>This RL environment optimizes clinical decision-making processes in healthcare settings. 
            It uses reinforcement learning to learn optimal strategies for patient care, resource allocation, 
            and treatment sequencing. The agent learns from trial and error to maximize clinical outcomes 
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
            <p>This RL environment optimizes healthcare revenue cycle management processes, including 
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
        `
    };
    
    return categoryDescriptions[category] || `
        <p>This RL environment uses reinforcement learning to optimize healthcare processes and decision-making. 
        The agent learns optimal strategies through trial and error, maximizing desired outcomes while 
        balancing multiple objectives such as clinical quality, operational efficiency, and financial performance.</p>
    `;
}

function getDefaultHowToUse(category, envName) {
    return `
        <ol>
            <li><strong>Access the Simulation:</strong> Click the "🧪 Simulation" button to open the interactive simulation console.</li>
            <li><strong>Configure Parameters:</strong> Adjust the environment configuration parameters in the left panel to match your healthcare setting (e.g., queue sizes, resource availability, urgency levels).</li>
            <li><strong>Select Agent Strategy:</strong> Choose an RL agent strategy (Random, Urgency First, Value First, or Balanced) to see how different approaches perform.</li>
            <li><strong>Initialize Environment:</strong> Click "Initialize Environment" to start a new simulation episode with your configured parameters.</li>
            <li><strong>Run Simulation:</strong> Use "Step Forward" to advance one step at a time, or "Auto Run" to let the simulation run automatically at your selected speed.</li>
            <li><strong>Monitor Metrics:</strong> Watch real-time KPIs, metrics, and recommendations in the right panel to understand performance.</li>
            <li><strong>Analyze Results:</strong> Review the results summary at the bottom to assess clinical outcomes, operational efficiency, financial impact, and ROI.</li>
            <li><strong>Iterate and Optimize:</strong> Adjust parameters and strategies to find optimal configurations for your specific use case.</li>
        </ol>
        <p><strong>Training:</strong> For production use, click "Start Training" to train a custom RL agent on your historical data. The trained model can then be deployed to make real-time decisions.</p>
    `;
}

function showEnvironmentDetails(envName) {
    const env = allEnvironments.find(e => e.name === envName);
    if (!env) return;
    
    const details = environmentDetails[envName] || {};
    const kpis = details.kpis || ['Clinical Outcomes', 'Operational Efficiency', 'Financial Metrics'];
    
    // Get detailed information about what the environment does and how to use it
    const whatItDoes = details.whatItDoes || getDefaultWhatItDoes(env.category, envName);
    const howToUse = details.howToUse || getDefaultHowToUse(env.category, envName);
    
    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = `
        <div class="modal-header">
            <h2>${formatEnvironmentName(env.name)}</h2>
            <span class="env-category category-${env.category}">${env.category}</span>
        </div>
        
        <div class="modal-section">
            <h3>What This RL Environment Does</h3>
            <div class="info-box">
                ${whatItDoes}
            </div>
        </div>
        
        <div class="modal-section">
            <h3>How to Use This Environment</h3>
            <div class="info-box">
                ${howToUse}
            </div>
        </div>
        
        <div class="modal-section">
            <h3>Description</h3>
            <p>${details.description || env.description || 'RL environment for optimization'}</p>
        </div>
        
        <div class="modal-section">
            <h3>System Integration</h3>
            <p><strong>Healthcare Systems:</strong> ${env.system || details.system || 'Multiple'}</p>
        </div>
        
        <div class="modal-section">
            <h3>Technical Specifications</h3>
            <ul>
                <li><strong>State Features:</strong> ${details.stateFeatures || env.stateFeatures || 'N/A'}</li>
                <li><strong>Action Space:</strong> ${details.actionType || 'Discrete'} (${details.actionSpace || env.actionSpace || 'N/A'} actions)</li>
                <li><strong>Multi-Agent:</strong> ${env.multi_agent ? 'Yes' : 'No'}</li>
            </ul>
        </div>
        
        <div class="modal-section">
            <h3>Key Performance Indicators (KPIs)</h3>
            <div class="kpi-list">
                ${kpis.map(kpi => `<div class="kpi-item">${kpi}</div>`).join('')}
            </div>
        </div>
        
        <div class="modal-section">
            <h3>Use Cases</h3>
            <p>${details.useCase || 'General healthcare optimization and decision support'}</p>
        </div>
        
        <div class="env-actions" style="margin-top: 2rem; border-top: 2px solid var(--border-color); padding-top: 1.5rem;">
            <div style="margin-bottom: 1.5rem; padding: 1rem; background: #f0f9ff; border-left: 4px solid var(--primary-color); border-radius: 6px;">
                <button class="btn btn-primary" onclick="window.location.href='/test-console?env=${envName}'" title="Open the interactive simulation console to test and explore the environment with different parameters. This allows you to manually control the simulation, adjust settings, and see real-time results without training an agent.">
                    🧪 Open Simulation
                </button>
                <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.75rem; line-height: 1.6;">
                    <strong style="color: var(--primary-color);">🧪 Simulation (Interactive Testing):</strong> Manually configure parameters, run simulations step-by-step, and observe results in real-time. Perfect for understanding how the environment works, testing different scenarios, and exploring the impact of various configurations. <strong>No AI training involved</strong> - you control everything manually.
                </p>
            </div>
            <div style="padding: 1rem; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 6px;">
                <div style="display: flex; gap: 0.5rem; margin-bottom: 0.75rem;">
                    <button class="btn btn-secondary" onclick="openTrainingConfig('${envName}')" title="Start training an RL agent (using PPO algorithm) to learn optimal decision-making strategies. This process runs in the background and creates a trained model that can make automated decisions.">
                        🎓 Start Training
                    </button>
                    <button class="btn btn-outline" onclick="openTrainingMonitor()" title="Monitor active training jobs, view progress, and download completed models." style="background: white; border-color: #f59e0b; color: #92400e;">
                        📊 Monitor Training
                    </button>
                </div>
                <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.75rem; line-height: 1.6;">
                    <strong style="color: #92400e;">🎓 Training (AI Learning):</strong> Train an AI agent using PPO (Proximal Policy Optimization) to learn optimal strategies through trial and error. The agent explores thousands of scenarios, learns from rewards/penalties, and develops a policy for automated decision-making. Creates a <strong>production-ready model</strong> that can make real-time decisions without human intervention.
                </p>
            </div>
        </div>
    `;
    
    document.getElementById('env-modal').style.display = 'block';
}

async function testEnvironment(envName) {
    try {
        const response = await fetch(`${API_BASE}/kpis/${envName}`);
        if (!response.ok) throw new Error('Failed to test environment');
        
        const data = await response.json();
        
        alert(`Environment Test Results:\n\n` +
              `Clinical Outcomes: ${JSON.stringify(data.kpis.clinical_outcomes, null, 2)}\n\n` +
              `Operational Efficiency: ${JSON.stringify(data.kpis.operational_efficiency, null, 2)}\n\n` +
              `Financial Metrics: ${JSON.stringify(data.kpis.financial_metrics, null, 2)}`);
    } catch (error) {
        alert(`Error testing environment: ${error.message}\n\nMake sure the API server is running.`);
    }
}

function openTrainingConfig(envName) {
    const env = allEnvironments.find(e => e.name === envName);
    const exampleConfig = getExampleConfig(envName);
    
    const configModal = document.createElement('div');
    configModal.className = 'modal';
    configModal.id = 'training-config-modal';
    configModal.innerHTML = `
        <div class="modal-content" style="max-width: 800px;">
            <span class="close" onclick="closeTrainingConfig()">&times;</span>
            <h2 style="margin-bottom: 1.5rem;">🎓 Configure Training: ${formatEnvironmentName(envName)}</h2>
            
            <div class="config-tabs" style="display: flex; gap: 0.5rem; margin-bottom: 1.5rem; border-bottom: 2px solid var(--border-color);">
                <button class="config-tab active" onclick="switchConfigTab('manual')" id="tab-manual">📝 Manual Entry</button>
                <button class="config-tab" onclick="switchConfigTab('json')" id="tab-json">📄 JSON Upload</button>
                <button class="config-tab" onclick="switchConfigTab('api')" id="tab-api">🔌 API Example</button>
            </div>
            
            <!-- Manual Entry Tab -->
            <div id="config-manual" class="config-tab-content">
                <div class="form-group">
                    <label>Algorithm:</label>
                    <select id="training-algorithm" onchange="updateModelInfo()">
                        <option value="PPO" selected>PPO (Proximal Policy Optimization)</option>
                        <option value="DQN">DQN (Deep Q-Network)</option>
                        <option value="A2C">A2C (Advantage Actor-Critic)</option>
                        <option value="SAC">SAC (Soft Actor-Critic)</option>
                    </select>
                    <small id="model-info" style="display: block; margin-top: 0.5rem; color: var(--text-secondary); font-size: 0.85rem;">
                        <strong>Model Architecture:</strong> PPO uses a Multi-Layer Perceptron (MLP) policy network with separate actor and critic networks. 
                        Default: [64, 64] hidden layers with tanh activation.
                    </small>
                </div>
                <div class="form-group">
                    <label>Dataset URL (Optional):</label>
                    <input type="url" id="training-dataset-url" placeholder="https://example.com/dataset.csv" />
                    <small>Provide a URL to download training data (CSV, JSON, or other formats). If not provided, synthetic data will be generated.</small>
                </div>
                <div class="form-group">
                    <label>Number of Episodes:</label>
                    <input type="number" id="training-episodes" value="100" min="10" max="10000" />
                    <small>More episodes = better learning but longer training time</small>
                </div>
                <div class="form-group">
                    <label>Max Steps per Episode:</label>
                    <input type="number" id="training-max-steps" value="1000" min="100" max="10000" />
                    <small>Maximum steps before episode terminates</small>
                </div>
                <div class="form-group">
                    <label>Environment Configuration (JSON):</label>
                    <textarea id="training-config-json" rows="8" placeholder='{"queue_size": 15, "high_urgency_pct": 30, "avg_order_value": 500}'>${JSON.stringify(exampleConfig, null, 2)}</textarea>
                    <small>Optional: Environment-specific parameters. Leave empty for defaults.</small>
                </div>
                
                <div style="background: #f0f9ff; padding: 1rem; border-radius: 6px; border-left: 4px solid var(--primary-color); margin-top: 1.5rem;">
                    <h4 style="margin-bottom: 0.75rem; color: var(--primary-color);">📦 Model Storage & Usage</h4>
                    <ul style="font-size: 0.85rem; line-height: 1.8; color: var(--text-secondary); padding-left: 1.5rem;">
                        <li><strong>Model Location:</strong> Trained models are saved to <code>./models/{'{algorithm}'}/</code> directory</li>
                        <li><strong>Model Format:</strong> Models are saved as ZIP files containing the policy network weights and metadata</li>
                        <li><strong>Download:</strong> After training completes, download via API: <code>GET /models/{'{algorithm}'}/{'{model_filename}'}</code></li>
                        <li><strong>Usage:</strong> Load models using stable-baselines3: <code>model = PPO.load("path/to/model.zip")</code></li>
                        <li><strong>Deployment:</strong> Use <code>model.predict(observation)</code> for real-time decision-making</li>
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
                        config: exampleConfig
                    }, null, 2)}</textarea>
                    <small>Include <code>"dataset_url"</code> field to provide training data URL</small>
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
                    config: exampleConfig
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
                    config: exampleConfig
                })}'</code></pre>
                
                <h3>Python Example:</h3>
                <pre style="background: #f1f5f9; padding: 1rem; border-radius: 6px; overflow-x: auto;"><code>import requests
from stable_baselines3 import PPO

# Start training
response = requests.post(
    "${API_BASE}/train/${envName}",
    json={
        "environment_name": "${envName}",
        "algorithm": "PPO",
        "num_episodes": 100,
        "max_steps": 1000,
        "dataset_url": "https://example.com/training_data.csv",
        "config": ${JSON.stringify(exampleConfig)}
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
        }
    };
    return examples[envName] || { queue_size: 10, resource_availability: 70 };
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

function updateModelInfo() {
    const algorithm = document.getElementById('training-algorithm').value;
    const modelInfo = document.getElementById('model-info');
    const modelDescriptions = {
        'PPO': '<strong>Model Architecture:</strong> PPO uses a Multi-Layer Perceptron (MLP) policy network with separate actor and critic networks. Default: [64, 64] hidden layers with tanh activation.',
        'DQN': '<strong>Model Architecture:</strong> DQN uses a deep Q-network with MLP architecture. Default: [64, 64] hidden layers with ReLU activation.',
        'A2C': '<strong>Model Architecture:</strong> A2C uses an MLP policy network with shared feature extractor. Default: [64, 64] hidden layers.',
        'SAC': '<strong>Model Architecture:</strong> SAC uses twin Q-networks and a policy network. Default: [256, 256] hidden layers for better performance.'
    };
    if (modelInfo) {
        modelInfo.innerHTML = modelDescriptions[algorithm] || modelDescriptions['PPO'];
    }
}

async function submitTrainingConfig(envName) {
    const activeTab = document.querySelector('.config-tab.active').id.replace('tab-', '');
    let config = null;
    let algorithm = 'PPO';
    let numEpisodes = 100;
    let maxSteps = 1000;
    let datasetUrl = null;
    
    if (activeTab === 'manual') {
        algorithm = document.getElementById('training-algorithm').value;
        numEpisodes = parseInt(document.getElementById('training-episodes').value);
        maxSteps = parseInt(document.getElementById('training-max-steps').value);
        datasetUrl = document.getElementById('training-dataset-url').value.trim() || null;
        const configJson = document.getElementById('training-config-json').value.trim();
        if (configJson) {
            try {
                config = JSON.parse(configJson);
            } catch (e) {
                alert(`❌ Invalid JSON in configuration: ${e.message}`);
                return;
            }
        }
    } else if (activeTab === 'json') {
        const jsonPaste = document.getElementById('config-json-paste').value.trim();
        if (!jsonPaste) {
            alert('Please provide a JSON configuration');
            return;
        }
        const parsed = validateJSON(jsonPaste);
        if (!parsed) return;
        
        algorithm = parsed.algorithm || 'PPO';
        numEpisodes = parsed.num_episodes || 100;
        maxSteps = parsed.max_steps || 1000;
        datasetUrl = parsed.dataset_url || null;
        config = parsed.config || parsed;
    }
    
    closeTrainingConfig();
    await startTraining(envName, algorithm, numEpisodes, maxSteps, config, datasetUrl);
}

async function startTraining(envName, algorithm = 'PPO', numEpisodes = 100, maxSteps = 1000, config = null, datasetUrl = null) {
    try {
        const response = await fetch(`${API_BASE}/train/${envName}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                environment_name: envName,
                algorithm: algorithm,
                num_episodes: numEpisodes,
                max_steps: maxSteps,
                dataset_url: datasetUrl,
                config: config
            })
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
        const modelInfo = `
📦 Model Information:
• Model will be saved to: ./models/${algorithm.toLowerCase()}/${envName}_{job_id}.zip
• Download after training: ${API_BASE}/models/${algorithm.toLowerCase()}/{model_filename}
• Load in Python: from stable_baselines3 import ${algorithm}; model = ${algorithm}.load("path/to/model.zip")
• Use for predictions: action, _ = model.predict(observation)
        `.trim();
        
        const monitorMessage = `Would you like to open the Training Monitor to track this job's progress?`;
        const openMonitor = confirm(`✅ Training started successfully!\n\n` +
              `Job ID: ${data.job_id}\n` +
              `Status: ${data.status}\n` +
              `Environment: ${formatEnvironmentName(envName)}\n` +
              `Algorithm: ${algorithm}\n` +
              `Episodes: ${numEpisodes}\n` +
              `Max Steps: ${maxSteps}\n` +
              (datasetUrl ? `Dataset: ${datasetUrl}\n` : ``) +
              `\n${modelInfo}\n\n` +
              `Monitor progress at: ${API_BASE}/training/${data.job_id}\n\n` +
              `Once training completes, check the job status to get the model download URL.\n\n` +
              monitorMessage);
        
        if (openMonitor) {
            openTrainingMonitor(data.job_id);
        }
    } catch (error) {
        console.error('Training error:', error);
        alert(`❌ Error starting training: ${error.message}\n\n` +
              `Make sure the API server is running and the training endpoint is available.\n\n` +
              `If the error persists, check the browser console for more details.`);
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
        alert('Please enter a Job ID');
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
        alert(`❌ Error loading job: ${error.message}\n\nMake sure the Job ID is correct and the API server is running.`);
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
        'pending': '#f59e0b'
    };
    
    const statusIcons = {
        'running': '🔄',
        'completed': '✅',
        'failed': '❌',
        'pending': '⏳'
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
    
    const resultsSection = jobData.results ? `
        <div style="background: #f0f9ff; padding: 1rem; border-radius: 6px; margin-top: 1rem;">
            <h4 style="margin-bottom: 0.75rem; color: var(--primary-color);">📈 Training Results</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; font-size: 0.9rem;">
                <div>
                    <strong>Mean Reward:</strong><br/>
                    <span style="color: var(--primary-color); font-size: 1.1rem; font-weight: 600;">
                        ${jobData.results.mean_reward?.toFixed(2) || 'N/A'}
                    </span>
                </div>
                <div>
                    <strong>Max Reward:</strong><br/>
                    <span style="color: var(--secondary-color); font-size: 1.1rem; font-weight: 600;">
                        ${jobData.results.max_reward?.toFixed(2) || 'N/A'}
                    </span>
                </div>
                <div>
                    <strong>Min Reward:</strong><br/>
                    <span style="color: var(--text-secondary); font-size: 1.1rem; font-weight: 600;">
                        ${jobData.results.min_reward?.toFixed(2) || 'N/A'}
                    </span>
                </div>
                <div>
                    <strong>Episodes:</strong><br/>
                    <span style="color: var(--text-primary); font-size: 1.1rem; font-weight: 600;">
                        ${jobData.results.total_episodes || jobData.num_episodes || 'N/A'}
                    </span>
                </div>
            </div>
        </div>
    ` : '';
    
    const modelSection = (jobData.status === 'completed' && jobData.model_url) ? `
        <div style="background: #dcfce7; padding: 1rem; border-radius: 6px; margin-top: 1rem; border-left: 4px solid var(--secondary-color);">
            <h4 style="margin-bottom: 0.75rem; color: #166534;">📦 Trained Model Available</h4>
            <p style="font-size: 0.9rem; margin-bottom: 0.75rem; color: var(--text-secondary);">
                Your model has been trained and is ready for download.
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
    
    const errorSection = (jobData.status === 'failed' && jobData.error) ? `
        <div style="background: #fee2e2; padding: 1rem; border-radius: 6px; margin-top: 1rem; border-left: 4px solid var(--danger-color);">
            <h4 style="margin-bottom: 0.75rem; color: var(--danger-color);">❌ Training Error</h4>
            <pre style="background: white; padding: 0.75rem; border-radius: 4px; font-size: 0.85rem; overflow-x: auto; color: var(--text-primary);">${jobData.error}</pre>
        </div>
    ` : '';
    
    jobsList.innerHTML = `
        <div class="training-job-card" style="background: white; border: 2px solid ${statusColor}; border-radius: 8px; padding: 1.5rem; margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                <div>
                    <h3 style="margin-bottom: 0.5rem; color: var(--text-primary);">
                        ${statusIcon} ${formatEnvironmentName(jobData.environment_name || 'Unknown')}
                    </h3>
                    <div style="display: flex; gap: 1rem; flex-wrap: wrap; font-size: 0.85rem; color: var(--text-secondary);">
                        <span><strong>Job ID:</strong> <code style="background: #f1f5f9; padding: 0.25rem 0.5rem; border-radius: 4px;">${jobData.job_id}</code></span>
                        <span><strong>Algorithm:</strong> ${jobData.algorithm || 'N/A'}</span>
                        <span><strong>Status:</strong> <span style="color: ${statusColor}; font-weight: 600;">${jobData.status.toUpperCase()}</span></span>
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
            
            ${resultsSection}
            ${modelSection}
            ${errorSection}
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
        alert(`Error refreshing job: ${error.message}`);
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
        alert('✅ Model information copied to clipboard!');
    }).catch(() => {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = modelInfo;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        alert('✅ Model information copied to clipboard!');
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
window.openTrainingMonitor = openTrainingMonitor;
window.loadTrainingJob = loadTrainingJob;
window.refreshJobStatus = refreshJobStatus;
window.copyModelInfo = copyModelInfo;

