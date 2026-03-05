// AgentWork Simulator - Analytics Dashboard
const API_BASE = window.API_BASE || 'http://localhost:8000';

let currentFrom = null;
let currentTo = null;
let currentGroupBy = null;
let currentEnvFilter = '';

function getDateRange(period) {
    const now = new Date();
    let from = null;
    let to = new Date(now);
    to.setSeconds(59, 999);
    if (period === 'day') {
        from = new Date(now);
        from.setHours(0, 0, 0, 0);
    } else if (period === 'week') {
        from = new Date(now);
        const day = from.getDay();
        const diff = from.getDate() - day + (day === 0 ? -6 : 1);
        from.setDate(diff);
        from.setHours(0, 0, 0, 0);
    } else if (period === 'month') {
        from = new Date(now.getFullYear(), now.getMonth(), 1);
    }
    return {
        from: from ? from.toISOString().slice(0, 19) + 'Z' : null,
        to: to.toISOString().slice(0, 19) + 'Z',
    };
}

function getGroupBy(period) {
    if (period === 'day') return 'day';
    if (period === 'week') return 'week';
    if (period === 'month') return 'month';
    return null;
}

async function fetchSummary() {
    const params = new URLSearchParams();
    if (currentFrom) params.set('from_date', currentFrom);
    if (currentTo) params.set('to_date', currentTo);
    const res = await fetch(`${API_BASE}/api/dashboard/summary?${params}`);
    if (!res.ok) throw new Error('Failed to fetch summary');
    return res.json();
}

async function fetchActivities() {
    const params = new URLSearchParams();
    if (currentFrom) params.set('from_date', currentFrom);
    if (currentTo) params.set('to_date', currentTo);
    if (currentGroupBy) params.set('group_by', currentGroupBy);
    if (currentEnvFilter) params.set('environment_name', currentEnvFilter);
    const res = await fetch(`${API_BASE}/api/dashboard/activities?${params}`);
    if (!res.ok) throw new Error('Failed to fetch activities');
    return res.json();
}

async function fetchExecutionStory(jobId) {
    const res = await fetch(`${API_BASE}/api/dashboard/job/${jobId}/execution-story`);
    if (!res.ok) return null;
    return res.json();
}

function buildCatalogUrl(envName) {
    const base = new URL('/', window.location.origin);
    if (envName) base.searchParams.set('env', envName);
    return base.pathname + base.search;
}

function buildSimulationUrl(envName) {
    const base = new URL('/test-console', window.location.origin);
    if (envName) base.searchParams.set('env', envName);
    return base.pathname + base.search;
}

function buildTrainingUrl(envName) {
    const base = new URL('/', window.location.origin);
    if (envName) base.searchParams.set('env', envName);
    return base.pathname + base.search + '#training';
}

function renderSummary(data) {
    document.getElementById('summary-total').textContent = data.total_activities || 0;
    document.getElementById('summary-envs').textContent = (data.environments_used || []).length;
    const envSelect = document.getElementById('filter-env');
    const envs = data.environments_used || [];
    const current = envSelect.value;
    envSelect.innerHTML = '<option value="">All environments</option>' +
        envs.map(e => `<option value="${e}">${e}</option>`).join('');
    if (current && envs.includes(current)) envSelect.value = current;
}

var STEP_ICONS = { target: '🎯', sliders: '⚙️', play: '▶️', activity: '📊', plug: '🔌', shield: '✓', package: '📦', users: '👥', eye: '👁', arrow: '→' };

function buildTrajectoryFromActivity(a) {
    var env = a.environment_name || '—';
    var meta = a.metadata || {};
    var eventType = a.event_type || '';
    var cfg = meta.config_summary || meta;
    if (eventType === 'simulation_initialized') {
        return { steps: [
            { step: 1, name: 'Environment selection', icon: 'target', input: { environment_name: env }, output: { loaded: true } },
            { step: 2, name: 'Input parameters', icon: 'sliders', input: cfg, output: { agent_strategy: meta.agent_strategy, agent_model: meta.agent_model } },
            { step: 3, name: 'Simulation step', icon: 'play', input: { step_count: meta.step_count }, output: { initialized: true, ready: 'Run steps in console' } },
            { step: 4, name: 'System integrated', icon: 'plug', input: {}, output: { system: meta.system_integrated || (env.indexOf('Jira') >= 0 ? 'Jira' : 'N/A') } },
            { step: 5, name: 'Verifier', icon: 'shield', input: {}, output: { verifier_type: meta.verifier_type } },
            { step: 6, name: 'Output', icon: 'package', input: {}, output: { status: 'Simulation runs in browser' } },
        ]};
    }
    if (eventType === 'environment_viewed') {
        return { steps: [
            { step: 1, name: 'Environment selection', icon: 'eye', input: { environment_name: env, category: meta.category, system: meta.system }, output: { viewed: true } },
            { step: 2, name: 'Next steps', icon: 'arrow', input: {}, output: { action: 'Open Simulation or Start Training from Catalog' } },
        ]};
    }
    return null;
}

function formatDataValue(v) {
    if (v === null || v === undefined) return '—';
    if (typeof v === 'boolean') return v ? 'yes' : 'no';
    if (typeof v === 'object') return JSON.stringify(v).length > 80 ? JSON.stringify(v).slice(0, 77) + '...' : JSON.stringify(v);
    return String(v);
}

function flattenDataForDisplay(obj, prefix, depth) {
    prefix = prefix || '';
    depth = depth || 0;
    if (!obj || typeof obj !== 'object' || depth > 2) return [];
    var rows = [];
    for (var k in obj) { if (!obj.hasOwnProperty(k)) continue;
        var v = obj[k];
        if (v !== null && v !== undefined && typeof v === 'object' && !Array.isArray(v) && depth < 2) {
            rows = rows.concat(flattenDataForDisplay(v, prefix + k + '.', depth + 1));
        } else {
            rows.push({ key: prefix + k, value: formatDataValue(v) });
        }
    }
    return rows;
}

function renderDataBlock(rows, type) {
    if (!rows || !rows.length) return '';
    var esc = function(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;'); };
    var html = rows.map(function(r) {
        return '<div class="traj-kv"><span class="traj-k">' + esc(r.key) + '</span><span class="traj-v" title="' + esc(r.value) + '">' + esc(r.value) + '</span></div>';
    }).join('');
    return '<div class="traj-block traj-' + type + '"><div class="traj-block-label">' + (type === 'input' ? 'Input' : 'Output') + '</div><div class="traj-block-body">' + html + '</div></div>';
}

function renderExecutionStory(container, story) {
    if (!story || !story.steps) {
        container.innerHTML = '<p>No execution trajectory available.</p>';
        return;
    }
    var steps = story.steps;
    var nodesHtml = '';
    for (var i = 0; i < steps.length; i++) {
        var s = steps[i];
        var inp = s.input !== undefined ? s.input : (s.data || {});
        var out = s.output !== undefined ? s.output : {};
        var inpRows = flattenDataForDisplay(inp);
        var outRows = flattenDataForDisplay(out);
        if (!outRows.length && s.description) outRows = [{ key: 'result', value: s.description }];
        if (!outRows.length) outRows = [{ key: 'status', value: '—' }];
        var blocks = renderDataBlock(inpRows, 'input') + renderDataBlock(outRows, 'output');
        nodesHtml += '<div class="traj-node">' +
            '<div class="traj-node-header">' +
                '<span class="traj-num">' + s.step + '</span>' +
                '<span class="traj-name">' + s.name + '</span>' +
            '</div>' +
            '<div class="traj-node-body">' + blocks + '</div>' +
        '</div>';
        if (i < steps.length - 1) nodesHtml += '<div class="traj-connector"></div>';
    }
    container.innerHTML = '<div class="trajectory-graph-v2">' + nodesHtml + '</div>';
}

function renderActivityItem(a, options = {}) {
    const env = a.environment_name || '—';
    const ts = a.timestamp ? new Date(a.timestamp).toLocaleString() : '—';
    const eventType = (a.event_type || '').replace(/_/g, ' ');
    const jobId = a.job_id || '';
    const hasJobStory = a.event_type === 'training_started' || a.event_type === 'training_completed';
    const hasInlineTrajectory = a.event_type === 'simulation_initialized' || a.event_type === 'environment_viewed';
    const hasTrajectory = hasJobStory || hasInlineTrajectory;
    const reuseEnv = a.environment_name || null;
    return `
        <div class="activity-item" data-activity-id="${a.id}" data-job-id="${jobId}" data-env="${reuseEnv || ''}" data-has-job-story="${hasJobStory}" data-has-inline-trajectory="${hasInlineTrajectory}">
            <div class="head">
                <span class="env">${env}</span>
                <span class="ts">${ts}</span>
                <span class="event-type">${eventType}</span>
            </div>
            <div class="trajectory-bar">
                <button type="button" class="btn-view-trajectory" data-activity-id="${a.id}">
                    <span class="trajectory-icon">▼</span> View execution trajectory
                </button>
            </div>
            <div class="execution-story" id="story-${a.id}"></div>
            <div class="reuse-bar">
                <a href="${buildCatalogUrl(reuseEnv)}"><button type="button">Open in Catalog</button></a>
                <a href="${buildSimulationUrl(reuseEnv)}"><button type="button">🧪 Simulation</button></a>
                <a href="${buildTrainingUrl(reuseEnv)}"><button type="button">🎓 Training</button></a>
            </div>
        </div>
    `;
}

function renderActivities(data) {
    const listEl = document.getElementById('activity-list');
    const emptyEl = document.getElementById('empty-state');
    const activities = data.activities || [];
    const grouped = data.grouped || null;

    if (activities.length === 0) {
        listEl.innerHTML = '';
        emptyEl.style.display = 'block';
        return;
    }
    emptyEl.style.display = 'none';

    if (grouped && Object.keys(grouped).length > 0) {
        const keys = Object.keys(grouped).sort().reverse();
        listEl.innerHTML = keys.map(key => {
            const items = grouped[key];
            return `
                <div class="group-label">${key}</div>
                ${items.map(a => renderActivityItem(a)).join('')}
            `;
        }).join('');
    } else {
        listEl.innerHTML = activities.map(a => renderActivityItem(a)).join('');
    }

    listEl.querySelectorAll('.activity-item .btn-view-trajectory').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const item = btn.closest('.activity-item');
            const activityId = item.dataset.activityId;
            const jobId = item.dataset.jobId;
            const hasJobStory = item.dataset.hasJobStory === 'true';
            const hasInlineTrajectory = item.dataset.hasInlineTrajectory === 'true';
            const storyEl = document.getElementById('story-' + activityId);
            if (!storyEl) return;

            const icon = btn.querySelector('.trajectory-icon');
            if (storyEl.classList.contains('visible')) {
                storyEl.classList.remove('visible');
                if (icon) icon.textContent = '▼';
                return;
            }

            let story = null;
            if (hasJobStory && jobId) {
                story = await fetchExecutionStory(jobId);
            } else if (hasInlineTrajectory) {
                const act = activities.find(x => x.id === activityId) || (grouped ? Object.values(grouped).flat().find(x => x.id === activityId) : null);
                story = act ? buildTrajectoryFromActivity(act) : null;
            }
            renderExecutionStory(storyEl, story);
            storyEl.classList.add('visible');
            if (icon) icon.textContent = '▲';
        });
    });
}

async function load() {
    try {
        const summary = await fetchSummary();
        renderSummary(summary);
        const activitiesData = await fetchActivities();
        renderActivities(activitiesData);
    } catch (err) {
        console.error(err);
        document.getElementById('activity-list').innerHTML = '';
        document.getElementById('empty-state').style.display = 'block';
        document.getElementById('empty-state').textContent = 'Could not load dashboard. Is the API running at ' + API_BASE + '?';
    }
}

function applyFilters() {
    const period = document.getElementById('filter-period').value;
    currentEnvFilter = document.getElementById('filter-env').value || '';
    if (period === 'all') {
        currentFrom = null;
        currentTo = null;
        currentGroupBy = null;
    } else {
        const range = getDateRange(period);
        currentFrom = range.from;
        currentTo = range.to;
        currentGroupBy = getGroupBy(period);
    }
    load();
}

document.getElementById('filter-period').addEventListener('change', applyFilters);
document.getElementById('filter-env').addEventListener('change', applyFilters);
document.getElementById('btn-refresh').addEventListener('click', () => load());

applyFilters();
