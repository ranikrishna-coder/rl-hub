// Environment Catalog Application

// API Base URL - auto-detected or set by config.js
// This will use window.API_BASE which is set by the auto-detection script in index.html
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
        description: 'Jira Subtask Management: add subtasks to existing Jira tickets by fetching parent issue and creating subtask under it.',
        stateFeatures: 6,
        actionType: 'Discrete',
        actionSpace: 3,
        kpis: ['Parent Fetched', 'Subtask Created', 'Sequence Correct', 'Workflow Compliance'],
        useCase: 'Adding subtasks to Jira issues',
        whatItDoes: '<p>Validates the Subtask Management workflow: <strong>get_issue_summary_and_description</strong> → <strong>create_subtask</strong>. Fetches parent issue, then creates a subtask under it.</p>',
        howToUse: '<p>Use action 0 for the correct next step. Fetch parent first, then create_subtask.</p>'
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
        } else if (domain === 'enterprise') {
            btn.style.display = (btnDomain === 'enterprise' || btn.dataset.category === 'all') ? '' : 'none';
        } else if (domain === 'healthcare') {
            btn.style.display = (btnDomain === 'healthcare' || btn.dataset.category === 'all') ? '' : 'none';
        }
    });
    const activeBtn = container.querySelector('.filter-btn.active');
    const activeDomain = activeBtn ? (activeBtn.dataset.domain || 'all') : 'all';
    const activeHidden = activeBtn && activeBtn.style.display === 'none';
    if (activeHidden || (domain === 'enterprise' && activeDomain === 'healthcare') || (domain === 'healthcare' && activeDomain === 'enterprise')) {
        container.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        const allBtn = container.querySelector('.filter-btn[data-category="all"]');
        if (allBtn && allBtn.style.display !== 'none') allBtn.classList.add('active');
    }
}

function updateSystemFilterOptions() {
    const domain = getActiveDomain();
    const systemFilter = document.getElementById('system-filter');
    if (!systemFilter) return;
    let envsForSystems = allEnvironments;
    if (domain === 'enterprise') {
        envsForSystems = allEnvironments.filter(env => env.category === 'jira');
    } else if (domain === 'healthcare') {
        envsForSystems = allEnvironments.filter(env => env.category !== 'jira');
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
    } else if (domain === 'enterprise' && systemList.length === 1) {
        systemFilter.value = systemList[0];
    }
}

function filterEnvironments(searchTerm, category) {
    const system = getActiveSystem();
    const domain = getActiveDomain();
    filteredEnvironments = allEnvironments.filter(env => {
        const matchesSearch = !searchTerm || 
            env.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (env.description && env.description.toLowerCase().includes(searchTerm.toLowerCase()));
        
        const matchesCategory = category === 'all' || env.category === category;
        
        const envSystems = (env.system || '').split(',').map(s => s.trim()).filter(Boolean);
        const matchesSystem = system === 'all' || envSystems.includes(system);
        
        let matchesDomain = true;
        // When a specific system is selected, system filter takes precedence over domain
        if (system === 'all') {
            if (domain === 'enterprise') matchesDomain = env.category === 'jira';
            else if (domain === 'healthcare') matchesDomain = env.category !== 'jira';
        }
        
        return matchesSearch && matchesCategory && matchesSystem && matchesDomain;
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
        'JiraSubtaskManagement': 'Jira Subtask Management: get_issue_summary_and_description → create_subtask for adding subtasks to issues.'
    };
    
    return descriptions[envName] || (category === 'jira' ? `Jira workflow environment for ${envName.replace(/([A-Z])/g, ' $1').trim().toLowerCase()} optimization.` : `Reinforcement learning environment for ${category.replace('_', ' ')} optimization and decision support.`);
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
        'JiraSubtaskManagement': 'Adding subtasks to existing Jira issues.'
    };
    
    return useCases[envName] || (category === 'jira' ? `Jira workflow: ${envName.replace(/([A-Z])/g, ' $1').trim().toLowerCase()}.` : `General ${category.replace('_', ' ')} optimization and decision support applications.`);
}

// Save/favorite management functions
function resetAllSaveCounts() {
    // Reset all save counts to 0 to remove fake random numbers (only run once)
    const savedData = JSON.parse(localStorage.getItem('rl_hub_saves') || '{}');
    const resetFlag = localStorage.getItem('rl_hub_counts_reset');
    
    // Only reset if we haven't done it before
    if (!resetFlag) {
        Object.keys(savedData).forEach(envName => {
            // Reset count to 0 but keep saved state
            if (savedData[envName].count > 4) {
                savedData[envName].count = 0;
            }
        });
        localStorage.setItem('rl_hub_saves', JSON.stringify(savedData));
        localStorage.setItem('rl_hub_counts_reset', 'true');
    }
}

function initializeSaveData(envName) {
    const savedData = JSON.parse(localStorage.getItem('rl_hub_saves') || '{}');
    
    if (!savedData[envName]) {
        // Initialize with 0 count for authentic, legitimate appearance
        savedData[envName] = { 
            saved: false, 
            count: 0 
        };
        localStorage.setItem('rl_hub_saves', JSON.stringify(savedData));
    }
    return savedData;
}

function getSavedCount(envName) {
    const savedData = initializeSaveData(envName);
    return savedData[envName].count;
}

function isSaved(envName) {
    const savedData = JSON.parse(localStorage.getItem('rl_hub_saves') || '{}');
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
    
    localStorage.setItem('rl_hub_saves', JSON.stringify(savedData));
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

function createEnvCard(env) {
    const categoryClass = `category-${env.category}`;
    const multiAgentBadge = env.multi_agent ? '<span style="background: #fecdd3; color: #991b1b; padding: 0.25rem 0.5rem; border-radius: 12px; font-size: 0.7rem; margin-left: 0.5rem;">Multi-Agent</span>' : '';
    const displayName = formatEnvironmentName(env.name);
    const saved = isSaved(env.name);
    const saveCount = getSavedCount(env.name);
    
    return `
        <div class="env-card">
            <div class="env-card-header">
                <div>
                    <div class="env-name">${displayName}${multiAgentBadge}</div>
                    <span class="env-category ${categoryClass}">${env.category || 'other'}</span>
                </div>
                <button class="save-btn ${saved ? 'saved' : ''}" data-save-env="${env.name}" onclick="toggleSave('${env.name}')" title="${saved ? 'Unsave this environment' : 'Save this environment'}">
                    ${saved ? '❤️' : '🤍'} <span class="save-count">${saveCount}</span>
                </button>
            </div>
            <div class="env-description">
                ${env.description || getEnvironmentDescription(env.name, env.category || 'other') || 'Reinforcement learning environment for workflow optimization.'}
            </div>
            <div class="env-details">
                <div class="detail-item">
                    <span class="detail-label">Software system:</span>
                    <span class="detail-value">${env.system || 'Multiple'}</span>
                </div>
            </div>
            <div class="env-actions">
                <button class="btn btn-primary btn-view-details" data-env="${env.name}">
                    View Details
                </button>
                <button class="btn btn-secondary" onclick="window.location.href='simulation-console.html?env=${env.name}'">
                    🧪 Simulation
                </button>
            </div>
        </div>
    `;
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
            <li><strong>Access the Simulation:</strong> Click the "🧪 Simulation" button to open the interactive simulation console.</li>
            <li><strong>Configure Parameters:</strong> Adjust the environment configuration parameters in the left panel to match your workflow setting (e.g., queue sizes, resource availability, urgency levels).</li>
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

function closeEnvDetailPage() {
    const page = document.getElementById('env-detail-page');
    const catalog = document.getElementById('catalog-container');
    if (page) page.style.display = 'none';
    if (catalog) catalog.style.display = 'block';
}

function showEnvironmentDetails(envName) {
    const env = allEnvironments.find(e => e.name === envName);
    if (!env) return;
    
    const details = environmentDetails[envName] || {};
    const kpis = details.kpis || ['Clinical Outcomes', 'Operational Efficiency', 'Financial Metrics'];
    
    // Get detailed information about what the environment does and how to use it
    const whatItDoes = details.whatItDoes || getDefaultWhatItDoes(env.category, envName);
    const howToUse = details.howToUse || getDefaultHowToUse(env.category, envName);
    
    const description = details.description || env.description || getEnvironmentDescription(env.name, env.category || 'other');
    const shortDesc = description.length > 200 ? description.slice(0, 197) + '...' : description;
    const useCase = details.useCase || getUseCaseDescription(env.name, env.category || 'other');

    const detailBody = document.getElementById('env-detail-body');
    detailBody.innerHTML = `
        <div class="detail-hero">
            <div class="detail-hero-left">
                <h1 class="detail-page-title">${formatEnvironmentName(env.name)}</h1>
                <span class="env-category category-${env.category}">${env.category}</span>
            </div>
            <div class="detail-action-bar">
                <button class="btn btn-primary" onclick="window.location.href='simulation-console.html?env=${envName}'" title="Open simulation console">🧪 Open Simulation</button>
                <button class="btn btn-secondary" onclick="openTrainingConfig('${envName}')" title="Start PPO training">🎓 Start Training</button>
                <button class="btn btn-outline" onclick="openTrainingMonitor()" title="View training jobs" style="background: var(--card-bg); border-color: var(--border-color); color: var(--text-primary);">📊 Monitor Training</button>
            </div>
        </div>

        <div class="detail-grid">
            <div class="detail-card">
                <h3>Overview</h3>
                <p>${shortDesc}</p>
                <p style="margin-top: 0.75rem; font-size: 0.85rem;"><strong>System:</strong> ${env.system || details.system || 'Multiple'}</p>
                <p style="margin-top: 0.25rem; font-size: 0.85rem;"><strong>Use case:</strong> ${useCase}</p>
            </div>
            <div class="detail-card">
                <h3>Specifications</h3>
                <div class="spec-grid">
                    <div class="spec-item"><label>State features</label><span>${details.stateFeatures || env.stateFeatures || 'N/A'}</span></div>
                    <div class="spec-item"><label>Action type</label><span>${details.actionType || env.actionType || 'Discrete'}</span></div>
                    <div class="spec-item"><label>Actions</label><span>${details.actionSpace || env.actionSpace || 'N/A'}</span></div>
                    <div class="spec-item"><label>Multi-agent</label><span>${env.multi_agent ? 'Yes' : 'No'}</span></div>
                </div>
            </div>
            <div class="detail-card">
                <h3>KPIs</h3>
                <div class="kpi-list">${kpis.map(kpi => `<span class="kpi-item">${kpi}</span>`).join('')}</div>
            </div>
            <div class="detail-card">
                <h3>Action choices</h3>
                ${env.actions && env.actions.length > 0 ? `
                    <div class="action-chips">${env.actions.map((action, i) => {
                        const display = action.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                        return `<span class="action-chip" title="${getActionDescription(env.name, action) || ''}">${i + 1}. ${display}</span>`;
                    }).join('')}</div>
                ` : `<p>${env.actionType || 'Discrete'} · ${env.actionSpace || 'N/A'} actions</p>`}
            </div>
        </div>

        <div class="detail-section" style="margin-top: 1.5rem;">
            <h3>What it does</h3>
            <div class="info-box">${whatItDoes}</div>
        </div>
        <div class="detail-section">
            <h3>How to use</h3>
            <div class="info-box">${howToUse}</div>
        </div>
    `;
    
    document.getElementById('catalog-container').style.display = 'none';
    document.getElementById('env-detail-page').style.display = 'block';
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

const JIRA_ENV_VERIFIERS = [
    { value: 'jira_workflow:issue_resolution', label: 'Jira Issue Resolution' },
    { value: 'jira_workflow:status_update', label: 'Jira Status Update' },
    { value: 'jira_workflow:comment_management', label: 'Jira Comment Management' },
    { value: 'jira_workflow:subtask_management', label: 'Jira Task Management' }
];
const JIRA_ENVS = ['JiraIssueResolution', 'JiraStatusUpdate', 'JiraCommentManagement', 'JiraSubtaskManagement'];
const JIRA_ENV_TO_WORKFLOW = { JiraIssueResolution: 'issue_resolution', JiraStatusUpdate: 'status_update', JiraCommentManagement: 'comment_management', JiraSubtaskManagement: 'subtask_management' };

function openTrainingConfig(envName) {
    const env = allEnvironments.find(e => e.name === envName);
    const exampleConfig = getExampleConfig(envName);
    const systemStr = (env && env.system) ? env.system : 'Multiple';
    const envSystemsList = systemStr.split(',').map(s => s.trim()).filter(Boolean);
    const hasMultiple = envSystemsList.length > 1;
    const isJiraEnv = JIRA_ENVS.includes(envName);
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
                            <option value="PPO" selected>PPO (Proximal Policy Optimization)</option>
                            <option value="DQN">DQN (Deep Q-Network)</option>
                            <option value="A2C">A2C (Advantage Actor-Critic)</option>
                            <option value="SAC">SAC (Soft Actor-Critic)</option>
                            <option value="SLM">SLM (Small Language Model – Jira)</option>
                        </select>
                        <small id="model-info">PPO uses an MLP policy network with separate actor and critic. Default: [64, 64] hidden layers.</small>
                    </div>
                </section>
                
                <section class="training-section">
                    <span class="training-section-title">Reward verifier</span>
                    <div class="form-group">
                        <label>Verifier <span class="tooltip-icon" title="Select the reward verifier. For Jira envs choose Issue Resolution, Status Update, or Comment Management. Ensemble combines clinical, operational, financial, and compliance verifiers.">ℹ️</span></label>
                        <select id="training-verifier-type" onchange="updateVerifierWeightsVisibility()">
                            ${verifierOptionsHtml}
                        </select>
                        <small>Choose a software system above to get a suggested verifier and weights.</small>
                        <div id="training-verifier-hint" class="verifier-hint"></div>
                    </div>
                    <div class="form-group" id="training-verifier-weights-group" style="display: none;">
                        <label>Verifier weights (JSON) <span class="tooltip-icon" title="Optional. Updated when you change the software system.">ℹ️</span></label>
                        <textarea id="training-verifier-weights" rows="4" placeholder='{"clinical": 0.4, "operational": 0.3, "financial": 0.2, "compliance": 0.1}'></textarea>
                        <small>Optional. Suggested weights are set from the selected software system.</small>
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
                            <input type="number" id="training-episodes" value="100" min="10" max="10000" />
                            <small>More episodes = longer training.</small>
                        </div>
                        <div class="form-group">
                            <label>Max steps per episode</label>
                            <input type="number" id="training-max-steps" value="1000" min="100" max="10000" />
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
    updateTrainingVerifierForSystem();
    updateModelInfo();
    updateVerifierWeightsVisibility();
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
        
        // Get verifier configuration
        const verifierType = document.getElementById('training-verifier-type');
        if (verifierType && verifierType.value !== 'default') {
            if (verifierType.value.startsWith('jira_workflow:')) {
                verifierConfig = {
                    type: 'jira_workflow',
                    metadata: { workflow_id: verifierType.value.split(':')[1] }
                };
            } else {
                verifierConfig = {
                    type: verifierType.value
                };
            }
            // Add weights if ensemble and weights are provided
            if (verifierType.value === 'ensemble') {
                const verifierWeights = document.getElementById('training-verifier-weights');
                if (verifierWeights && verifierWeights.value.trim()) {
                    try {
                        const weights = JSON.parse(verifierWeights.value);
                        verifierConfig.verifiers = weights;
                    } catch (e) {
                        console.warn('Invalid verifier weights JSON, using defaults:', e);
                    }
                }
            }
        }

        const configJson = document.getElementById('training-config-json').value.trim();
        if (configJson) {
            try {
                config = JSON.parse(configJson);
            } catch (e) {
                alert(`❌ Invalid JSON in configuration: ${e.message}`);
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
            alert('Please provide a JSON configuration');
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
        const requestBody = {
            environment_name: envName,
            algorithm: algorithm,
            num_episodes: numEpisodes,
            max_steps: maxSteps,
            dataset_url: datasetUrl,
            config: config
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
    
    const resultsSection = jobData.results ? (() => {
        const meanR = jobData.results.mean_reward;
        const maxR = jobData.results.max_reward;
        const minR = jobData.results.min_reward;
        const eps = jobData.results.total_episodes || jobData.num_episodes || 0;
        const completed = jobData.results.episodes_completed ?? eps;
        
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
                        ${jobData.results.mean_reward?.toFixed(2) ?? 'N/A'}
                    </span>
                </div>
                <div>
                    <strong>Max Reward:</strong><br/>
                    <span style="color: var(--secondary-color); font-size: 1.1rem; font-weight: 600;">
                        ${jobData.results.max_reward?.toFixed(2) ?? 'N/A'}
                    </span>
                </div>
                <div>
                    <strong>Min Reward:</strong><br/>
                    <span style="color: var(--text-secondary); font-size: 1.1rem; font-weight: 600;">
                        ${jobData.results.min_reward?.toFixed(2) ?? 'N/A'}
                    </span>
                </div>
                <div>
                    <strong>Episodes:</strong><br/>
                    <span style="color: var(--text-primary); font-size: 1.1rem; font-weight: 600;">
                        ${completed} / ${jobData.results.total_episodes || jobData.num_episodes || 'N/A'}
                    </span>
                </div>
            </div>
            <div style="margin-top: 0.75rem; padding: 0.6rem 0.75rem; background: rgba(37,99,235,0.08); border-radius: 6px; font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5;">
                <strong style="color: var(--text-primary);">Why these values:</strong> ${summaryText}
            </div>
        </div>
    `;
    })() : '';
    
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

    const subtaskSection = (jobData.status === 'completed'
        && jobData.environment_name === 'JiraSubtaskManagement'
        && jobData.subtask_log_url) ? `
        <div style="background: #eff6ff; padding: 1rem; border-radius: 6px; margin-top: 1rem; border-left: 4px solid #2563eb;">
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
    const humanEvalSection = `
        <div id="job-card-human-eval" style="background: #fef3c7; padding: 1rem; border-radius: 6px; margin-top: 1rem; border-left: 4px solid #d97706;">
            <h4 style="margin-bottom: 0.75rem; color: #92400e;">👤 Human Evaluation</h4>
            <p style="font-size: 0.9rem; margin-bottom: 0.75rem; color: var(--text-secondary);">
                Record your approval or rejection for this run (for RLHF / model selection).
            </p>
            ${lastEval ? `
            <div style="margin-bottom: 0.75rem; padding: 0.5rem; background: white; border-radius: 4px; font-size: 0.85rem;">
                <strong>Last evaluation:</strong> ${lastEval.decision === 'yes' ? '✅ Yes' : '❌ No'}
                ${lastEval.comments ? ` — ${(lastEval.comments || '').replace(/</g, '&lt;').substring(0, 80)}${(lastEval.comments || '').length > 80 ? '…' : ''}` : ''}
                <br/><span style="color: var(--text-secondary);">${lastEval.timestamp ? new Date(lastEval.timestamp).toLocaleString() : ''}</span>
                ${(jobData.human_evaluations && jobData.human_evaluations.length > 1) ? `<br/><span style="font-size: 0.8rem;">Total evaluations: ${jobData.human_evaluations.length}</span>` : ''}
            </div>
            ` : ''}
            <a href="${API_BASE}/static/human-eval.html?job_id=${jobData.job_id}" target="_blank" rel="noopener" class="btn btn-outline" style="display: inline-block; text-decoration: none;">
                ${lastEval ? '✏️ Open Human Evaluation' : '👤 Open Human Evaluation'}
            </a>
        </div>
    `;

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
window.updateVerifierWeightsVisibility = updateVerifierWeightsVisibility;
window.openTrainingMonitor = openTrainingMonitor;
window.loadTrainingJob = loadTrainingJob;
window.refreshJobStatus = refreshJobStatus;
window.copyModelInfo = copyModelInfo;
window.toggleSave = toggleSave;

