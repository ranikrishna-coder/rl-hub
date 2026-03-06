// Generic Simulation Console for AgentWork Simulator

// API Base URL - auto-detected or set by config.js
const API_BASE = window.API_BASE || (() => {
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') return 'http://localhost:8000';
    return window.location.origin;
})();
let currentEnvironment = null;
let simulationState = null;
let simulationInterval = null;
let stepCount = 0;
let metricsHistory = [];
let allEnvironments = [];
let jiraMockData = null;
let jiraIssueIndex = 0;  // Cycles through all issues on each Initialize (agent runs across all)
let jiraSubtaskLog = []; // Collects all subtasks created in simulation for download
let currentRolloutSteps = []; // Accumulates step data during a simulation run
let rolloutEpisodeCounter = 0; // Auto-incrementing episode number per session
let _previousTotalReward = 0; // For computing per-step reward delta
let _simStartTime = 0; // performance.now() at simulation start, for timeline timestamps

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
    populateSimAlgorithms();
});

// ── Verifier Section State ───────────────────────────────────────────
let _verifierActiveSystem = null;
let _verifierActiveTypeFilter = 'all';
let _selectedVerifierId = null;

// ── Verifier Section: Show/hide and render (compact dropdown) ──────

function showVerifierSection(envName) {
    var section = document.getElementById('verifier-section');
    if (!section || !window.VERIFIER_DATA) return;
    var env = allEnvironments.find(function (e) { return e.name === envName; });
    var category = env ? (env.category || '') : '';
    var system = window.VERIFIER_DATA.getSystemForCategory(category);
    _verifierActiveSystem = system;
    _verifierActiveTypeFilter = 'all';
    _selectedVerifierId = null;
    section.style.display = '';
    populateSystemDropdown(system);
    populateVerifierDropdown(system, 'all');
    updateVerifierInfoRow();
    setupVerifierDropdownListeners();
    setupCreateVerifierButton();
}

function hideVerifierSection() {
    var section = document.getElementById('verifier-section');
    if (section) section.style.display = 'none';
}

// ── System Dropdown ─────────────────────────────────────────────────

function populateSystemDropdown(activeSystem) {
    var select = document.getElementById('verifier-system-select');
    if (!select) return;
    var groups = window.VERIFIER_DATA.getGroups();
    select.innerHTML = groups.map(function (g) {
        return '<option value="' + escAttr(g.system) + '"' +
            (g.system === activeSystem ? ' selected' : '') + '>' +
            esc(g.system) + ' (' + g.count + ')</option>';
    }).join('');
}

// ── Verifier Dropdown ───────────────────────────────────────────────

function populateVerifierDropdown(system, typeFilter) {
    var select = document.getElementById('verifier-dropdown');
    if (!select) return;
    var verifiers = window.VERIFIER_DATA.getBySystem(system);
    if (typeFilter && typeFilter !== 'all') {
        verifiers = verifiers.filter(function (v) { return v.type === typeFilter; });
    }
    select.innerHTML = '<option value="">-- Select verifier (' + verifiers.length + ') --</option>';
    verifiers.forEach(function (v) {
        var badge = v.type === 'human-eval' ? ' [HIL]' : '';
        var statusTag = v.status === 'disabled' ? ' (disabled)' : '';
        select.innerHTML += '<option value="' + escAttr(v.id) + '"' +
            (v.status === 'disabled' ? ' disabled' : '') +
            (v.id === _selectedVerifierId ? ' selected' : '') + '>' +
            esc(v.name) + badge + statusTag + '</option>';
    });
}

// ── Dropdown Listeners ──────────────────────────────────────────────

function setupVerifierDropdownListeners() {
    var systemSelect = document.getElementById('verifier-system-select');
    var verifierSelect = document.getElementById('verifier-dropdown');
    var typeFilter = document.getElementById('verifier-type-filter-dropdown');
    var clearBtn = document.getElementById('btn-clear-verifier');

    if (systemSelect) {
        systemSelect.onchange = function () {
            _verifierActiveSystem = systemSelect.value;
            _selectedVerifierId = null;
            populateVerifierDropdown(_verifierActiveSystem, typeFilter ? typeFilter.value : 'all');
            updateVerifierInfoRow();
        };
    }
    if (typeFilter) {
        typeFilter.onchange = function () {
            _verifierActiveTypeFilter = typeFilter.value;
            populateVerifierDropdown(_verifierActiveSystem, typeFilter.value);
        };
    }
    if (verifierSelect) {
        verifierSelect.onchange = function () {
            _selectedVerifierId = verifierSelect.value || null;
            updateVerifierInfoRow();
            showSubVerifierFilter();
            showHilNotice();
            showAdvancedDetails();
        };
    }
    if (clearBtn) {
        clearBtn.onclick = function () {
            _selectedVerifierId = null;
            if (verifierSelect) verifierSelect.value = '';
            updateVerifierInfoRow();
            showSubVerifierFilter();
            showHilNotice();
            showAdvancedDetails();
        };
    }
}

// ── Info Row (selected verifier summary) ────────────────────────────

function updateVerifierInfoRow() {
    var row = document.getElementById('verifier-info-row');
    var clearBtn = document.getElementById('btn-clear-verifier');
    if (!row) return;
    if (!_selectedVerifierId) {
        row.style.display = 'none';
        if (clearBtn) clearBtn.style.display = 'none';
        showSubVerifierFilter();
        showHilNotice();
        showAdvancedDetails();
        return;
    }
    var v = window.VERIFIER_DATA.getById(_selectedVerifierId);
    if (!v) { row.style.display = 'none'; return; }
    var typeCls = 'vtype-' + v.type;
    row.style.display = '';
    row.innerHTML = '<span class="verifier-type-badge ' + typeCls + '">' + esc(v.type) + '</span> ' +
        '<span style="font-size:0.82rem;color:var(--text-secondary);">' + esc(v.system) + ' &middot; v' + v.version + ' &middot; ' + esc(v.status) + '</span>' +
        '<span style="font-size:0.78rem;color:var(--text-secondary);margin-left:auto;">' + v.usedInScenarios.length + ' scenario' + (v.usedInScenarios.length !== 1 ? 's' : '') + '</span>';
    if (clearBtn) clearBtn.style.display = '';
}

// ── Sub-Verifier Filter ─────────────────────────────────────────────

function showSubVerifierFilter() {
    var container = document.getElementById('verifier-sub-filter');
    if (!container) return;
    if (!_selectedVerifierId) { container.style.display = 'none'; return; }
    var v = window.VERIFIER_DATA.getById(_selectedVerifierId);
    if (!v || !v.subVerifiers || v.subVerifiers.length === 0) {
        container.style.display = 'none'; return;
    }
    container.style.display = '';
    container.innerHTML = '<label style="font-size:0.78rem;font-weight:600;margin-bottom:0.25rem;display:block;">Sub-verifiers</label>' +
        v.subVerifiers.map(function (sv) {
            return '<label class="sub-verifier-chip' + (sv.enabled ? ' active' : '') + '" title="' + escAttr(sv.description) + '">' +
                '<input type="checkbox"' + (sv.enabled ? ' checked' : '') + ' data-svid="' + escAttr(sv.id) + '"> ' +
                esc(sv.name) + '</label>';
        }).join('');
    container.querySelectorAll('input[type="checkbox"]').forEach(function (cb) {
        cb.addEventListener('change', function () {
            var svid = cb.getAttribute('data-svid');
            var sv = v.subVerifiers.find(function (s) { return s.id === svid; });
            if (sv) sv.enabled = cb.checked;
            cb.parentElement.classList.toggle('active', cb.checked);
        });
    });
}

// ── HIL Notice ──────────────────────────────────────────────────────

function showHilNotice() {
    var notice = document.getElementById('hil-verifier-notice');
    if (!notice) return;
    if (!_selectedVerifierId) { notice.style.display = 'none'; return; }
    var v = window.VERIFIER_DATA.getById(_selectedVerifierId);
    notice.style.display = (v && v.type === 'human-eval') ? 'flex' : 'none';
}

// ── Advanced Details (expandable) ───────────────────────────────────

function showAdvancedDetails() {
    var details = document.getElementById('verifier-advanced-details');
    var content = document.getElementById('verifier-expanded-content');
    if (!details || !content) return;
    if (!_selectedVerifierId) { details.style.display = 'none'; return; }
    var v = window.VERIFIER_DATA.getById(_selectedVerifierId);
    if (!v) { details.style.display = 'none'; return; }
    details.style.display = '';
    content.innerHTML = renderVerifierExpanded(v);
    content.querySelectorAll('[data-vaction]').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            handleVerifierAction(btn.getAttribute('data-vaction'), v.id);
        });
    });
    // Wire up HIL condition row add/remove events
    _initSimHilConditionEvents(content);
}

// ── Expanded Verifier View (reused in Advanced Details) ─────────────

function renderVerifierExpanded(v) {
    var html = '<div class="verifier-expanded">';
    html += '<div class="verifier-detail-section"><p style="font-size:0.85rem;color:var(--text-secondary);">' + esc(v.description) + '</p></div>';
    html += '<div class="verifier-detail-section"><h4>Metadata</h4>' +
        '<div class="verifier-meta-grid">' +
            '<div class="verifier-meta-item"><span class="label">Type: </span><span class="value">' + esc(v.type) + '</span></div>' +
            '<div class="verifier-meta-item"><span class="label">Environment: </span><span class="value">' + esc(v.environment) + '</span></div>' +
            '<div class="verifier-meta-item"><span class="label">On Failure: </span><span class="value">' + esc(v.metadata.onFailure) + '</span></div>' +
            '<div class="verifier-meta-item"><span class="label">Timeout: </span><span class="value">' + esc(v.metadata.timeout) + '</span></div>' +
            '<div class="verifier-meta-item"><span class="label">Version: </span><span class="value">v' + v.version + '</span></div>' +
            '<div class="verifier-meta-item"><span class="label">System: </span><span class="value">' + esc(v.system) + '</span></div>' +
        '</div></div>';
    var isHil = v.type === 'human-eval' || v.type === 'human_evaluation' ||
        (v.logic && v.logic.type === 'human_evaluation');

    if (isHil) {
        // Editable Evaluation Conditions & Weights for HIL verifiers
        var criteria = (v.logic && v.logic.criteria) || [];
        var equalWeight = criteria.length ? (Math.round((1 / criteria.length) * 100) / 100) : 0;
        html += '<div class="verifier-detail-section"><h4>Evaluation Conditions &amp; Weights</h4>';
        html += '<div style="display:flex;justify-content:space-between;padding:0 0 0.35rem;border-bottom:1px solid var(--border-color,#e8e4ef);margin-bottom:0.4rem;">' +
            '<span style="font-size:0.72rem;text-transform:uppercase;font-weight:600;color:var(--text-secondary);">Condition</span>' +
            '<span style="font-size:0.72rem;text-transform:uppercase;font-weight:600;color:var(--text-secondary);">Weight</span>' +
        '</div>';
        html += '<div id="sim-hil-condition-rows">';
        if (criteria.length) {
            criteria.forEach(function (c) {
                html += _buildSimHilCondRow(c, String(equalWeight));
            });
        } else {
            html += _buildSimHilCondRow('Correct resolution', '0.4');
            html += _buildSimHilCondRow('Proper status transitions', '0.3');
            html += _buildSimHilCondRow('', '0.0');
        }
        html += '</div>';
        html += '<button type="button" class="add-condition-btn" id="btn-sim-hil-add-cond" style="margin-top:0.5rem;">' +
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
            ' Add condition</button>';
        html += '</div>';
    } else {
        html += '<div class="verifier-detail-section"><h4>Verifier Logic</h4>' +
            '<div class="verifier-code-block">' + esc(JSON.stringify(v.logic, null, 2)) + '</div></div>';
        html += '<div class="verifier-detail-section"><h4>Example Input</h4>' +
            '<div class="verifier-code-block">' + esc(JSON.stringify(v.exampleInput, null, 2)) + '</div></div>';
        html += '<div class="verifier-detail-section"><h4>Example Output</h4>' +
            '<div class="verifier-code-block">' + esc(JSON.stringify(v.exampleOutput, null, 2)) + '</div></div>';
    }
    html += '<div class="verifier-detail-section"><h4>Used by Scenarios</h4>' +
        '<ul class="verifier-scenario-list">' +
        v.usedInScenarios.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') +
        '</ul></div>';
    html += '<div class="verifier-detail-section"><h4>Failure Policy</h4>' +
        '<div class="verifier-code-block">' + esc(JSON.stringify(v.failurePolicy, null, 2)) + '</div></div>';
    html += '<div class="verifier-actions">' +
        '<button class="btn btn-secondary btn-small" data-vaction="edit">Edit (New Version)</button>' +
        '<button class="btn btn-secondary btn-small" data-vaction="duplicate">Duplicate</button>' +
        '<button class="btn btn-secondary btn-small" data-vaction="toggle-status">' + (v.status === 'active' ? 'Disable' : 'Enable') + '</button>' +
        '</div>';
    html += '</div>';
    return html;
}

// ── HIL Condition Row Helpers (Simulation Expanded View) ──────────

function _buildSimHilCondRow(cond, weight) {
    return '<div class="condition-row" style="display:flex;gap:0.5rem;align-items:center;margin-bottom:0.4rem;">' +
        '<input type="text" class="sim-hil-cond-name" placeholder="Condition" value="' + esc(cond || '') + '" ' +
            'style="flex:1;padding:0.45rem 0.6rem;border:1px solid var(--border-color,#e8e4ef);border-radius:6px;font-size:0.85rem;">' +
        '<input type="number" class="sim-hil-cond-weight" placeholder="0.0" step="0.1" min="0" max="1" value="' + esc(weight || '') + '" ' +
            'style="width:70px;padding:0.45rem 0.6rem;border:1px solid var(--border-color,#e8e4ef);border-radius:6px;font-size:0.85rem;text-align:center;">' +
        '<button type="button" class="sim-hil-cond-remove" title="Remove" ' +
            'style="background:none;border:none;cursor:pointer;color:var(--text-secondary);font-size:1.1rem;padding:0 0.3rem;">&times;</button>' +
    '</div>';
}

function _initSimHilConditionEvents(container) {
    // Add condition button
    var addBtn = container.querySelector('#btn-sim-hil-add-cond');
    if (addBtn) {
        addBtn.addEventListener('click', function () {
            var rows = container.querySelector('#sim-hil-condition-rows');
            if (rows) {
                rows.insertAdjacentHTML('beforeend', _buildSimHilCondRow('', '0.0'));
                _updateSimHilRemoveButtons(rows);
            }
        });
    }
    // Remove buttons (delegated)
    var rowsContainer = container.querySelector('#sim-hil-condition-rows');
    if (rowsContainer) {
        rowsContainer.addEventListener('click', function (e) {
            var btn = e.target.closest('.sim-hil-cond-remove');
            if (btn) {
                var rows = rowsContainer.querySelectorAll('.condition-row');
                if (rows.length > 1) {
                    btn.closest('.condition-row').remove();
                    _updateSimHilRemoveButtons(rowsContainer);
                }
            }
        });
        _updateSimHilRemoveButtons(rowsContainer);
    }
}

function _updateSimHilRemoveButtons(container) {
    var rows = container.querySelectorAll('.condition-row');
    rows.forEach(function (r) {
        var btn = r.querySelector('.sim-hil-cond-remove');
        if (btn) {
            btn.style.visibility = rows.length <= 1 ? 'hidden' : 'visible';
        }
    });
}

// ── Lifecycle Actions ──────────────────────────────────────────────

function handleVerifierAction(action, vid) {
    var v = window.VERIFIER_DATA.getById(vid);
    if (!v) return;

    if (action === 'edit') {
        v.version = (v.version || 1) + 1;
        if (window.showToast) window.showToast('Verifier "' + v.name + '" updated to v' + v.version, 'success');
        updateVerifierInfoRow();
        showAdvancedDetails();
    } else if (action === 'duplicate') {
        var newV = JSON.parse(JSON.stringify(v));
        newV.id = window.VERIFIER_DATA.generateId();
        newV.name = v.name + ' (Copy)';
        newV.version = 1;
        window.VERIFIER_DATA.add(newV);
        if (window.showToast) window.showToast('Duplicated "' + v.name + '" as "' + newV.name + '"', 'success');
        populateSystemDropdown(_verifierActiveSystem);
        populateVerifierDropdown(_verifierActiveSystem, _verifierActiveTypeFilter);
    } else if (action === 'toggle-status') {
        v.status = v.status === 'active' ? 'disabled' : 'active';
        if (window.showToast) window.showToast('Verifier "' + v.name + '" ' + v.status, v.status === 'active' ? 'success' : 'warning');
        if (_selectedVerifierId === vid && v.status === 'disabled') {
            _selectedVerifierId = null;
            var sel = document.getElementById('verifier-dropdown');
            if (sel) sel.value = '';
        }
        populateVerifierDropdown(_verifierActiveSystem, _verifierActiveTypeFilter);
        updateVerifierInfoRow();
        showAdvancedDetails();
    } else if (action === 'view-scenarios') {
        var scenarioSelect = document.querySelector('#dynamic-config select[id*="scenario"]');
        if (scenarioSelect) {
            scenarioSelect.scrollIntoView({ behavior: 'smooth', block: 'center' });
            scenarioSelect.style.outline = '2px solid var(--primary-color)';
            setTimeout(function () { scenarioSelect.style.outline = ''; }, 2000);
        }
        if (window.showToast) window.showToast('Scenarios linked: ' + v.usedInScenarios.join(', '), 'info');
    }
}

// ── Create New Verifier Modal ──────────────────────────────────────

function setupCreateVerifierButton() {
    var btn = document.getElementById('btn-create-verifier');
    if (!btn) return;
    btn.removeEventListener('click', _openCreateVerifierModal);
    btn.addEventListener('click', _openCreateVerifierModal);
}

function _openCreateVerifierModal() {
    var existing = document.querySelector('.verifier-modal-overlay');
    if (existing) existing.remove();

    var overlay = document.createElement('div');
    overlay.className = 'verifier-modal-overlay';
    overlay.innerHTML =
        '<div class="verifier-modal">' +
            '<h3><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:-0.15em"><path d="M12 5v14M5 12h14"/></svg> Create New Verifier</h3>' +
            '<div class="form-group"><label>Name</label><input type="text" id="new-v-name" placeholder="e.g. My Custom Verifier"></div>' +
            '<div class="form-group"><label>Type</label><select id="new-v-type"><option value="rule-based">Rule-based</option><option value="trajectory-based">Trajectory-based</option><option value="llm-judge">LLM Judge</option><option value="human-eval">Human Eval (HIL)</option></select></div>' +
            '<div class="form-group"><label>System</label><input type="text" id="new-v-system" value="' + escAttr(_verifierActiveSystem || '') + '" readonly></div>' +
            /* Standard fields for rule-based, trajectory, llm-judge */
            '<div id="new-v-standard-panel">' +
                '<div class="form-group"><label>Description</label><textarea id="new-v-desc" rows="2" placeholder="What does this verifier check?"></textarea></div>' +
                '<div class="form-group"><label>Logic (JSON)</label><textarea id="new-v-logic" rows="4" placeholder=\'{"checks": {}, "scoring": {}}\'></textarea></div>' +
                '<div class="form-group"><label>Failure Policy</label>' +
                    '<div style="display:flex;gap:0.5rem;align-items:center;margin-bottom:0.3rem;">' +
                        '<label style="font-weight:400;font-size:0.8rem;"><input type="checkbox" id="new-v-hardfail"> Hard fail</label>' +
                        '<label style="font-weight:400;font-size:0.8rem;"><input type="checkbox" id="new-v-logfail" checked> Log failure</label>' +
                    '</div>' +
                    '<div class="form-group" style="margin-bottom:0;"><label style="font-size:0.78rem;">Penalty</label><input type="number" id="new-v-penalty" value="-0.5" step="0.1"></div>' +
                '</div>' +
            '</div>' +
            /* Condition/weight panel for human-eval */
            '<div id="new-v-hil-panel" style="display:none">' +
                '<div class="form-group">' +
                    '<label>Evaluation Conditions &amp; Weights</label>' +
                    '<div style="display:flex;justify-content:space-between;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.03em;color:#5a5568;padding:0.3rem 0;border-bottom:1px solid #e8e4ef;margin-bottom:0.5rem;">' +
                        '<span>Condition</span><span>Weight</span>' +
                    '</div>' +
                    '<div id="new-v-condition-rows"></div>' +
                    '<button type="button" id="new-v-add-condition" style="background:none;border:none;color:#9333ea;font-size:0.82rem;cursor:pointer;padding:0.4rem 0;font-weight:500;">+ Add condition</button>' +
                '</div>' +
            '</div>' +
            '<div class="verifier-modal-actions">' +
                '<button class="btn btn-secondary" id="new-v-cancel">Cancel</button>' +
                '<button class="btn btn-primary" id="new-v-save">Create Verifier</button>' +
            '</div>' +
        '</div>';

    document.body.appendChild(overlay);
    overlay.addEventListener('click', function (e) { if (e.target === overlay) overlay.remove(); });
    document.getElementById('new-v-cancel').addEventListener('click', function () { overlay.remove(); });

    // Type toggle: show standard fields or condition/weight panel
    var typeSelect = document.getElementById('new-v-type');
    var stdPanel = document.getElementById('new-v-standard-panel');
    var hilPanel = document.getElementById('new-v-hil-panel');
    typeSelect.addEventListener('change', function () {
        var isHil = typeSelect.value === 'human-eval';
        stdPanel.style.display = isHil ? 'none' : '';
        hilPanel.style.display = isHil ? '' : 'none';
        // Pre-populate default conditions if empty
        if (isHil && !document.querySelector('#new-v-condition-rows .new-v-cond-row')) {
            _addModalConditionRow('Correct resolution', '0.4');
            _addModalConditionRow('Proper status transitions', '0.3');
            _addModalConditionRow('Communication quality', '0.3');
        }
    });

    // Condition row management
    document.getElementById('new-v-add-condition').addEventListener('click', function () {
        _addModalConditionRow('', '0.0');
    });
    document.getElementById('new-v-condition-rows').addEventListener('click', function (e) {
        var btn = e.target.closest('.new-v-cond-remove');
        if (btn) {
            btn.closest('.new-v-cond-row').remove();
            _updateModalConditionRemoveButtons();
        }
    });

    document.getElementById('new-v-save').addEventListener('click', function () {
        var name = document.getElementById('new-v-name').value.trim();
        if (!name) { if (window.showToast) window.showToast('Verifier name is required', 'warning'); return; }
        var type = document.getElementById('new-v-type').value;
        var system = document.getElementById('new-v-system').value;
        var category = '';
        window.VERIFIER_DATA.systems.forEach(function (s) { if (s.system === system) category = s.category; });
        var onFailure = type === 'human-eval' ? 'block_training' : 'log_and_continue';
        var timeout = type === 'human-eval' ? 'manual' : '30s';

        var desc = '';
        var logic = {};
        var hardFail = false;
        var logFail = true;
        var penalty = -0.5;

        if (type === 'human-eval') {
            // Collect conditions
            var conditions = [];
            document.querySelectorAll('#new-v-condition-rows .new-v-cond-row').forEach(function (row) {
                var cond = row.querySelector('.new-v-cond-name').value.trim();
                var wt = parseFloat(row.querySelector('.new-v-cond-weight').value) || 0;
                if (cond) conditions.push({ condition: cond, weight: wt });
            });
            logic = { type: 'human_evaluation', criteria: conditions.map(function (c) { return c.condition; }), conditions: conditions, scoring: 'manual', output_range: [0, 1] };
            hardFail = true;
            penalty = 0;
        } else {
            desc = document.getElementById('new-v-desc').value.trim();
            var logicRaw = document.getElementById('new-v-logic').value.trim();
            if (logicRaw) { try { logic = JSON.parse(logicRaw); } catch (e) { if (window.showToast) window.showToast('Invalid JSON in Logic field', 'error'); return; } }
            penalty = parseFloat(document.getElementById('new-v-penalty').value) || -0.5;
            hardFail = document.getElementById('new-v-hardfail').checked;
            logFail = document.getElementById('new-v-logfail').checked;
        }

        var newV = {
            id: window.VERIFIER_DATA.generateId(),
            name: name,
            type: type,
            system: system,
            environment: category,
            version: 1,
            status: 'active',
            usedInScenarios: [],
            description: desc,
            metadata: { type: type, environment: category, onFailure: onFailure, timeout: timeout },
            logic: logic,
            exampleInput: {},
            exampleOutput: {},
            failurePolicy: { hard_fail: hardFail, penalty: penalty, log_failure: logFail },
            subVerifiers: []
        };
        window.VERIFIER_DATA.add(newV);
        _selectedVerifierId = newV.id;
        overlay.remove();
        if (window.showToast) window.showToast('Created verifier "' + name + '"', 'success');
        populateSystemDropdown(_verifierActiveSystem);
        populateVerifierDropdown(_verifierActiveSystem, _verifierActiveTypeFilter);
        updateVerifierInfoRow();
        showSubVerifierFilter();
        showHilNotice();
        showAdvancedDetails();
    });
}

function _addModalConditionRow(cond, weight) {
    var container = document.getElementById('new-v-condition-rows');
    var html = '<div class="new-v-cond-row" style="display:flex;gap:0.5rem;align-items:center;margin-bottom:0.5rem;">' +
        '<input type="text" class="new-v-cond-name" placeholder="Condition" value="' + escAttr(cond || '') + '" style="flex:1;padding:0.5rem;border:1px solid #e8e4ef;border-radius:6px;font-size:0.85rem;">' +
        '<input type="number" class="new-v-cond-weight" value="' + escAttr(weight || '0.0') + '" step="0.1" min="0" max="1" style="width:70px;padding:0.5rem;border:1px solid #e8e4ef;border-radius:6px;font-size:0.85rem;text-align:center;">' +
        '<button type="button" class="new-v-cond-remove" style="background:none;border:none;cursor:pointer;color:#999;font-size:1.1rem;padding:0 0.3rem;" title="Remove">&times;</button>' +
        '</div>';
    container.insertAdjacentHTML('beforeend', html);
    _updateModalConditionRemoveButtons();
}

function _updateModalConditionRemoveButtons() {
    var rows = document.querySelectorAll('#new-v-condition-rows .new-v-cond-row');
    rows.forEach(function (r) {
        r.querySelector('.new-v-cond-remove').style.visibility = rows.length <= 1 ? 'hidden' : 'visible';
    });
}

// ── HTML escape helpers ────────────────────────────────────────────

function esc(s) { return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function escAttr(s) { return String(s || '').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }

// ── Legacy stubs (keep for backward compat) ────────────────────────

function updateSimulationVerifierForSystem() {
    // Now handled by showVerifierSection
}

function setupVerifierControls() {
    // Now handled by setupVerifierTypeFilters + setupCreateVerifierButton
}

function getSelectedVerifierConfig() {
    if (!_selectedVerifierId || !window.VERIFIER_DATA) return { type: 'ensemble' };
    var v = window.VERIFIER_DATA.getById(_selectedVerifierId);
    if (!v) return { type: 'ensemble' };
    return {
        type: v.type,
        id: v.id,
        name: v.name,
        system: v.system,
        failurePolicy: v.failurePolicy,
        logic: v.logic
    };
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
    
    // Show verifier section with system-appropriate verifiers
    showVerifierSection(envName);

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

    // Populate scenario, agent, algorithm from training config data
    populateSimScenarios(env);
    populateSimAgents(env);
    populateSimAlgorithms();
}

/* ── Scenario / Agent / Algorithm population (from TRAINING_CONFIG) ── */

function populateSimScenarios(env) {
    var sel = document.getElementById('sim-scenario');
    if (!sel) return;
    var cat = env ? env.category : '';
    var CFG = window.TRAINING_CONFIG || {};
    sel.innerHTML = '<option value="">— Select scenario —</option>';
    (CFG.scenarios || []).forEach(function (s) {
        if (!cat || s.category === cat) {
            var o = document.createElement('option');
            o.value = s.id;
            o.textContent = s.name + ' (' + s.task_count + ' tasks)';
            sel.appendChild(o);
        }
    });
}

function populateSimAgents(env) {
    var sel = document.getElementById('sim-agent');
    if (!sel) return;
    var cat = env ? env.category : '';
    var CFG = window.TRAINING_CONFIG || {};
    sel.innerHTML = '<option value="">— Select agent —</option>';
    (CFG.agents || []).forEach(function (a) {
        if (cat && a.compatible_categories && a.compatible_categories.indexOf(cat) === -1) return;
        var o = document.createElement('option');
        o.value = a.id;
        o.textContent = a.name + ' (' + a.base_model + ')';
        sel.appendChild(o);
    });
}

function populateSimAlgorithms() {
    var container = document.getElementById('sim-algo-group');
    if (!container) return;
    var CFG = window.TRAINING_CONFIG || {};
    container.innerHTML = '';
    (CFG.algorithms || []).forEach(function (a, i) {
        var id = 'sim-algo-' + a.id;
        var html = '<label class="sim-algo-option" style="display:flex;align-items:flex-start;gap:0.5rem;padding:0.4rem 0;cursor:pointer;">' +
            '<input type="radio" name="sim-algorithm" value="' + a.id + '"' + (i === 0 ? ' checked' : '') + ' id="' + id + '" style="margin-top:0.25rem;">' +
            '<div><strong style="font-size:0.85rem;">' + a.name + '</strong>' +
            (a.recommended ? ' <span style="color:var(--primary-color);font-size:0.75rem;">(Recommended)</span>' : '') +
            '<div style="font-size:0.78rem;color:var(--text-secondary);">' + a.description + '</div></div>' +
            '</label>';
        container.insertAdjacentHTML('beforeend', html);
    });
}

// updateVerifierSelectForEnvironment removed — replaced by showVerifierSection()

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
            const key = 'agentwork_simulator_sim_human_eval';
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
        showToast('Please select an environment first', 'warning');
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

        // Rollout tracking
        currentRolloutSteps = [];
        rolloutEpisodeCounter++;
        _previousTotalReward = 0;
        _simStartTime = performance.now();
        simulationState._initialStateSnapshot = JSON.parse(JSON.stringify(simulationState.metrics || {}));
        
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
        showToast('Error initializing: ' + error.message, 'error');
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
    
    // Add verifier configuration from the compact dropdown
    const selectedVerifier = getSelectedVerifierConfig();
    if (selectedVerifier && selectedVerifier.type !== 'ensemble') {
        config.verifier_config = selectedVerifier;
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

    // Record step data for rollout with rich timeline events
    var _currentReward = (simulationState.metrics || {}).totalReward || 0;
    var _stepReward = _currentReward - _previousTotalReward;
    _previousTotalReward = _currentReward;
    var _elapsed = performance.now() - (_simStartTime || performance.now());
    var _stepEvents = [];
    if (stepCount === 1) {
        _stepEvents.push({ timestamp_ms: 0, event_type: 'SYSTEM', content: 'User request received: "' + (currentEnvironment || 'simulation') + '"' });
    }
    var _actionDesc = simulationState.lastAction || ('action_' + stepCount);
    _stepEvents.push({
        timestamp_ms: Math.round(_elapsed),
        event_type: 'TOOL_CALL',
        tool_name: typeof _actionDesc === 'object' ? (_actionDesc.name || JSON.stringify(_actionDesc)) : String(_actionDesc),
        tool_args: typeof _actionDesc === 'object' ? _actionDesc : null
    });
    _stepEvents.push({
        timestamp_ms: Math.round(_elapsed + 5),
        event_type: 'TOOL_RESULT',
        content: 'reward: ' + _stepReward.toFixed(4),
        reward: _stepReward,
        state_snapshot: { step: stepCount, queueLength: (simulationState.metrics || {}).queueLength || 0 }
    });
    currentRolloutSteps.push({
        step: stepCount,
        action: simulationState.lastAction || null,
        reward: _stepReward,
        state_summary: { step: stepCount, queueLength: (simulationState.metrics || {}).queueLength || 0 },
        reward_breakdown: null,
        timeline_events: _stepEvents
    });

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
    document.getElementById('btn-stop').disabled = false;
    
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
    document.getElementById('btn-stop').disabled = true;
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
        showToast('No Jira subtasks have been created in this simulation session yet.', 'info');
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
        <div class="metric-reasoning" style="margin-top: 0.75rem; padding: 0.5rem; font-size: 0.82rem; line-height: 1.45;">
            Lagging indicators help compare strategies and assess convergence over multiple runs.
        </div>
    `;

    // Store rollout to backend
    if (currentEnvironment && currentRolloutSteps.length > 0) {
        var rolloutData = {
            environment_name: currentEnvironment,
            episode_number: rolloutEpisodeCounter,
            steps: currentRolloutSteps,
            initial_state: simulationState._initialStateSnapshot || null,
            final_outcome: {
                total_reward: totalReward,
                steps_completed: stepCount,
                episode_completed: isComplete
            },
            total_reward: totalReward,
            total_steps: stepCount,
            status: isComplete ? 'completed' : 'incomplete',
            source: 'simulation'
        };
        fetch(API_BASE + '/api/rollouts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(rolloutData)
        }).then(function () {
            if (window.showToast) window.showToast('Rollout saved (Episode ' + rolloutEpisodeCounter + ')', 'info');
            // Show rollout comparison if there's a previous rollout to compare against
            _showSimRolloutComparison(currentEnvironment);
        }).catch(function () {});
    }

    // HIL flow: if human-eval verifier is selected, prompt to open evaluation console
    if (_selectedVerifierId && window.VERIFIER_DATA) {
        var _hilV = window.VERIFIER_DATA.getById(_selectedVerifierId);
        if (_hilV && _hilV.type === 'human-eval') {
            setTimeout(function () {
                if (window.showToast) window.showToast('Human evaluation required for this verifier.', 'warning', 5000);
                if (confirm('Simulation complete. This verifier requires human evaluation.\n\nOpen the Human Evaluation Console now?')) {
                    window.open('/human-eval', '_blank');
                }
            }, 600);
        }
    }
}

function _showSimRolloutComparison(envName) {
    if (!envName || !window.renderRolloutComparison) return;
    fetch(API_BASE + '/api/rollouts/' + encodeURIComponent(envName) + '?limit=2')
    .then(function(r) { return r.ok ? r.json() : null; })
    .then(function(data) {
        if (!data || !data.rollouts || data.rollouts.length < 2) return;
        var compContainer = document.getElementById('sim-rollout-comparison');
        if (!compContainer) return;
        var latestId = data.rollouts[0].id;
        var previousId = data.rollouts[1].id;
        return Promise.all([
            fetch(API_BASE + '/api/rollouts/' + encodeURIComponent(envName) + '/' + previousId).then(function(r) { return r.json(); }),
            fetch(API_BASE + '/api/rollouts/' + encodeURIComponent(envName) + '/' + latestId).then(function(r) { return r.json(); })
        ]).then(function(pair) {
            compContainer.style.display = '';
            window.renderRolloutComparison(compContainer, pair[0], pair[1], {
                scenarioName: window.formatEnvironmentName ? window.formatEnvironmentName(envName) : envName,
                envName: envName,
                trainedLabel: 'Current Run (Episode ' + rolloutEpisodeCounter + ')'
            });
        });
    }).catch(function() {});
}

