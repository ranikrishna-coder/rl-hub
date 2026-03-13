/**
 * Training Console — vanilla JS
 * Handles list view, new-run form, and run-details view.
 * Environments loaded from GET /environments API (113 across 22 systems).
 * Scenarios/verifiers filter based on selected environment's category.
 */
(function () {
    'use strict';

    var CFG = window.TRAINING_CONFIG || {};
    var VERIFIER_STORE = window.VERIFIER_DATA || {};
    var VERIFIERS = VERIFIER_STORE.all || [];

    // Environments loaded from API — populated by loadEnvironments()
    var ALL_ENVIRONMENTS = [];
    var CATEGORY_MAP = {}; // { category: [env, ...] }
    var SYSTEM_MAP = {}; // { system: [env, ...] }

    // Custom scenarios loaded from API — populated by loadScenarios()
    var CUSTOM_SCENARIOS = [];

    // Deferred environment preselection (set via ?preselect_env= param, applied on "New Training" click)
    var _preselectedEnv = null;
    // Persistent filter for training list — when opened embedded for a specific env, only show matching runs
    var _envFilterCategory = null;

    function _applyEnvPreselection(envId, readOnly) {
        if (!envId) return;
        var env = findEnv(envId);
        // Show all environments (no system filter) so the target env is visible
        var systemSel = document.getElementById('tr-env-system');
        if (systemSel) {
            systemSel.value = '';
            populateEnvironments();
        }
        var envSel = document.getElementById('tr-env');
        if (envSel) envSel.value = envId;
        onEnvironmentChange();

        // When navigated from environments page (?env=), lock the selection
        if (readOnly) {
            if (envSel) envSel.disabled = true;
            if (systemSel) systemSel.disabled = true;
        }
    }

    function _applyAgentPreselection(agentId) {
        if (!agentId) return;
        // Switch to new training view and pre-select the agent
        var agentSel = document.getElementById('tr-agent');
        if (agentSel) {
            // Ensure agent is in the dropdown (populate all first)
            agentSel.innerHTML = '<option value="">— Select agent —</option>';
            (CFG.agents || []).forEach(function (a) {
                if (!a.trainable) return;
                var o = document.createElement('option');
                o.value = a.id;
                o.textContent = a.name + ' (' + a.base_model + ')';
                agentSel.appendChild(o);
            });
            agentSel.value = agentId;
            // Make agent dropdown read-only when pre-populated from agent console
            setTimeout(function () {
                var sel = document.getElementById('tr-agent');
                if (sel) sel.disabled = true;
            }, 100);
        }
    }

    // ─── Fetch live training jobs from backend ─────────────────
    // Set of hardcoded mock IDs that should not be overwritten by API
    var MOCK_RUN_IDS = { 'run_grpo_001': true, 'run_grpo_ck_001': true };

    function fetchLiveJobs() {
        var apiBase = window.API_BASE || '';
        return fetch(apiBase + '/api/training/jobs')
            .then(function (res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function (data) {
                var liveJobs = data.jobs || [];
                // Build map of existing run IDs → index
                var existingMap = {};
                (CFG.trainingRuns || []).forEach(function (r, idx) { existingMap[r.id] = idx; });

                liveJobs.forEach(function (j) {
                    if (MOCK_RUN_IDS[j.job_id]) return; // don't overwrite hardcoded mock runs
                    var res = j.results || {};
                    if (existingMap[j.job_id] != null) {
                        // Update existing in-memory run with fresh backend data
                        var existing = CFG.trainingRuns[existingMap[j.job_id]];
                        existing.status = j.status || existing.status;
                        existing.progress = j.progress != null ? j.progress : existing.progress;
                        existing.model_saved = j.model_saved || existing.model_saved;
                        existing.model_url = j.model_url || existing.model_url;
                        existing.model_metadata = j.model_metadata || existing.model_metadata;
                        existing.hil_required = j.hil_required || existing.hil_required;
                        if (j.error) existing.error = j.error;
                        if (j.results) {
                            existing.results = j.results;
                            existing.avgReward = res.mean_reward;
                            existing.episodes = res.episodes_completed || res.total_episodes || existing.episodes;
                        }
                        if (j.baseline_results) {
                            existing.baseline_results = j.baseline_results;
                            existing.baselineReward = j.baseline_results.mean_reward;
                        }
                        if (j.started_at && existing.started === '\u2014') {
                            existing.started = fmtISODate(j.started_at);
                        }
                    } else {
                        // New backend job — append
                        var fallbackName = (j.algorithm || '') + ' \u2014 ' + humanizeName(j.environment_name || '');
                        // Resolve category: prefer API value, fallback to matching env from registry
                        var jobCategory = j.category || '';
                        if (!jobCategory && j.environment_name) {
                            var envObj = findEnv(j.environment_name);
                            if (envObj) jobCategory = envObj.category || '';
                        }
                        CFG.trainingRuns.push({
                            id: j.job_id,
                            job_id: j.job_id,
                            name: j.run_name || fallbackName,
                            description: (j.algorithm || '') + ' training on ' + humanizeName(j.environment_name || ''),
                            status: j.status || 'unknown',
                            environment: j.environment_name || '',
                            environmentDisplay: humanizeName(j.environment_name || ''),
                            category: jobCategory,
                            model: j.model || '\u2014',
                            algorithm: j.algorithm || '\u2014',
                            progress: j.progress || 0,
                            episodes: res.total_episodes || null,
                            successRate: null,
                            avgReward: res.mean_reward || null,
                            started: j.started_at ? fmtISODate(j.started_at) : '\u2014',
                            hil_required: j.hil_required || false,
                            model_saved: j.model_saved || false,
                            model_url: j.model_url || null,
                            model_metadata: j.model_metadata || null,
                            results: j.results,
                            baseline_results: j.baseline_results,
                            error: j.error || null
                        });
                    }
                });
            })
            .catch(function (err) {
                console.warn('Failed to fetch live training jobs:', err);
            });
    }

    // ─── Fetch agents & algorithms from backend (future API) ───
    // Falls back to hardcoded TRAINING_CONFIG data if API not available
    function fetchAgentsAndAlgorithms() {
        var apiBase = window.API_BASE || '';
        return fetch(apiBase + '/api/training/config')
            .then(function (res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function (data) {
                if (data.agents && data.agents.length) {
                    CFG.agents = data.agents;
                }
                if (data.algorithms && data.algorithms.length) {
                    CFG.algorithms = data.algorithms;
                }
            })
            .catch(function () {
                // API not available yet — use hardcoded sample data from TRAINING_CONFIG
            });
    }

    // ─── View navigation ────────────────────────────────────────
    function showView(name) {
        document.querySelectorAll('.training-view').forEach(function (v) {
            v.classList.remove('active');
        });
        var el = document.getElementById('training-' + name + '-view');
        if (el) el.classList.add('active');
    }

    // ─── Load environments from API ─────────────────────────────
    function loadEnvironments() {
        var apiBase = window.API_BASE || '';
        return fetch(apiBase + '/api/environments')
            .then(function (res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function (data) {
                ALL_ENVIRONMENTS = (data.environments || []).map(function (e) {
                    return {
                        id: e.name,
                        name: humanizeName(e.name),
                        category: e.category || '',
                        system: e.system || '',
                        workflow: e.workflow || '',
                        actions: e.actions || [],
                        actionSpace: e.actionSpace || 'N/A',
                        stateFeatures: e.stateFeatures || 'N/A',
                        actionType: e.actionType || 'Discrete',
                        multi_agent: e.multi_agent || false
                    };
                });
                CATEGORY_MAP = {};
                SYSTEM_MAP = {};
                ALL_ENVIRONMENTS.forEach(function (e) {
                    if (!CATEGORY_MAP[e.category]) CATEGORY_MAP[e.category] = [];
                    CATEGORY_MAP[e.category].push(e);
                    // Build system map: each env may belong to multiple systems
                    (e.system || '').split(',').forEach(function (s) {
                        var trimmed = s.trim();
                        if (trimmed) {
                            if (!SYSTEM_MAP[trimmed]) SYSTEM_MAP[trimmed] = [];
                            SYSTEM_MAP[trimmed].push(e);
                        }
                    });
                });
                // Ensure ClinKriya Clinic is always in the list (not in standard registry)
                if (!ALL_ENVIRONMENTS.some(function (e) { return e.id === 'ClinKriya Clinic'; })) {
                    var ckEnv = {
                        id: 'ClinKriya Clinic',
                        name: 'ClinKriya Clinic',
                        category: 'clinical',
                        system: 'FHIR / EHR',
                        workflow: 'Clinical',
                        actions: [],
                        actionSpace: 'N/A',
                        stateFeatures: 'N/A',
                        actionType: 'Discrete',
                        multi_agent: false
                    };
                    ALL_ENVIRONMENTS.push(ckEnv);
                    if (!CATEGORY_MAP['clinical']) CATEGORY_MAP['clinical'] = [];
                    CATEGORY_MAP['clinical'].push(ckEnv);
                    var ckSys = 'FHIR / EHR';
                    if (!SYSTEM_MAP[ckSys]) SYSTEM_MAP[ckSys] = [];
                    SYSTEM_MAP[ckSys].push(ckEnv);
                }
                CFG.environments = ALL_ENVIRONMENTS;
            })
            .catch(function (err) {
                console.warn('Failed to load environments:', err);
                ALL_ENVIRONMENTS = [];
                CATEGORY_MAP = {};
            });
    }

    // ─── Load custom scenarios from API ─────────────────────────
    function loadScenarios() {
        var apiBase = window.API_BASE || '';
        return fetch(apiBase + '/api/scenarios')
            .then(function (res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function (data) {
                CUSTOM_SCENARIOS = (data.scenarios || []).map(function (s) {
                    var tasks = s.tasks || [];
                    return {
                        id: s.id || '',
                        name: s.name || s.id || '',
                        category: s.category || '',
                        product: s.product || '',
                        environment: s.environment || s.product || '',
                        task_count: tasks.length || s.task_count || 0,
                        description: s.description || (s.system_prompt || '').substring(0, 120),
                        source: 'custom',
                        _full: s   // keep original full JSON
                    };
                });
            })
            .catch(function (err) {
                console.warn('Failed to load custom scenarios:', err);
                CUSTOM_SCENARIOS = [];
            });
    }

    // ─── Load verifiers from API (persisted in SQLite) ─────────
    function loadVerifiers() {
        var apiBase = window.API_BASE || '';
        return fetch(apiBase + '/api/verifiers')
            .then(function (res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function (data) {
                var apiVerifiers = data.verifiers || [];
                if (!apiVerifiers.length) return;
                // Build a set of existing IDs to avoid duplicates
                var existingIds = {};
                VERIFIERS.forEach(function (v) { if (v.id) existingIds[v.id] = true; });
                apiVerifiers.forEach(function (v) {
                    if (v.id && !existingIds[v.id]) {
                        VERIFIERS.push(v);
                        existingIds[v.id] = true;
                    }
                });
            })
            .catch(function (err) {
                console.warn('Failed to load verifiers from API:', err);
            });
    }

    function getAllScenarios() {
        // Merge built-in scenarios (from training-config-data.js) with custom ones from API
        // Deduplicate by name to avoid showing cloned DB copies alongside hardcoded originals
        var builtIn = (CFG.scenarios || []).map(function (s) {
            s.source = s.source || 'built-in';
            return s;
        });
        var seenNames = {};
        builtIn.forEach(function (s) { if (s.name) seenNames[s.name] = true; });
        var uniqueCustom = CUSTOM_SCENARIOS.filter(function (s) {
            if (s.name && seenNames[s.name]) return false;
            seenNames[s.name] = true;
            return true;
        });
        return builtIn.concat(uniqueCustom);
    }

    function humanizeName(name) {
        if (!name) return '';
        return name.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2');
    }

    function formatCategory(cat) {
        if (!cat) return '';
        return cat.split('_').map(function (w) {
            return w.charAt(0).toUpperCase() + w.slice(1);
        }).join(' ');
    }

    // ─── Training List ──────────────────────────────────────────
    function renderTrainingList() {
        var runs = CFG.trainingRuns || [];

        // When opened as embedded popup for a specific environment, filter runs
        // to only show runs matching that environment's category
        if (_envFilterCategory) {
            runs = runs.filter(function (r) {
                return r.category === _envFilterCategory;
            });
        }

        var body = document.getElementById('training-runs-body');
        var countEl = document.getElementById('run-count');
        var headerNewBtn = document.getElementById('btn-new-run');
        if (countEl) countEl.textContent = runs.length + ' run' + (runs.length !== 1 ? 's' : '');

        if (!runs.length) {
            // Hide the header "New Training" button when empty state has its own
            if (headerNewBtn) headerNewBtn.style.display = 'none';
            if (countEl) countEl.textContent = '0 runs';
            body.innerHTML =
                '<div class="training-empty-state">' +
                '<div class="training-empty-icon">' +
                '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">' +
                '<path d="M22 10v6M2 10l10-5 10 5-10 5z"/>' +
                '<path d="M6 12v5c6 3 10 3 16 0v-5"/>' +
                '</svg>' +
                '</div>' +
                '<h3 class="training-empty-title">No training runs yet</h3>' +
                '<p class="training-empty-text">Run a training to see results here. Configure your environment, select an algorithm, and start your first training run.</p>' +
                '<button type="button" class="btn btn-primary training-empty-btn" id="btn-empty-new-run">' +
                '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
                ' New Training' +
                '</button>' +
                '</div>';
            // Wire up the empty state button
            var emptyBtn = document.getElementById('btn-empty-new-run');
            if (emptyBtn) {
                emptyBtn.addEventListener('click', function () {
                    showView('new');
                    if (_preselectedEnv) {
                        _applyEnvPreselection(_preselectedEnv);
                        _preselectedEnv = null;
                    }
                });
            }
            return;
        }

        // Show the header "New Training" button when there are runs
        if (headerNewBtn) headerNewBtn.style.display = '';

        var html = '<table class="training-table"><thead><tr>';
        html += '<th>Name</th><th>Environment</th><th>Algorithm</th><th>Status</th><th>Progress</th><th>Episodes</th><th>Avg Reward</th><th>Started</th>';
        html += '</tr></thead><tbody>';

        runs.forEach(function (r) {
            var pct = r.progress || 0;
            var envDisplay = r.environmentDisplay || humanizeName(r.environment) || r.environment;
            var statusClass = r.status || 'pending';
            var statusLabel = capFirst(r.status);
            var reward = (r.avgReward != null) ? r.avgReward.toFixed(2) : '—';
            var episodes = (r.episodes != null) ? r.episodes : '—';

            html += '<tr class="training-row" data-run-id="' + esc(r.id) + '">';
            html += '<td class="tr-name">' + esc(r.name) + '</td>';
            html += '<td>' + esc(envDisplay) + '</td>';
            html += '<td>' + esc(r.algorithm) + '</td>';
            html += '<td><span class="status-badge ' + statusClass + '">' + statusLabel + '</span></td>';
            html += '<td><div class="progress-bar-wrap"><div class="progress-bar"><div class="progress-bar-fill ' + statusClass + '" style="width:' + pct + '%"></div></div><span class="progress-pct">' + pct + '%</span></div></td>';
            html += '<td>' + episodes + '</td>';
            html += '<td>' + reward + '</td>';
            html += '<td>' + esc(r.started || '—') + '</td>';
            html += '</tr>';
        });

        html += '</tbody></table>';
        body.innerHTML = html;

        body.querySelectorAll('.training-row[data-run-id]').forEach(function (row) {
            row.addEventListener('click', function () {
                showRunDetails(row.getAttribute('data-run-id'));
            });
        });
    }

    // ─── New Training Run Form ──────────────────────────────────

    function populateSystems() {
        var sel = document.getElementById('tr-env-system');
        if (!sel) return;
        var systems = Object.keys(SYSTEM_MAP).sort();
        sel.innerHTML = '<option value="">— All tools —</option>';
        systems.forEach(function (sys) {
            var o = document.createElement('option');
            o.value = sys;
            o.textContent = sys + ' (' + SYSTEM_MAP[sys].length + ')';
            sel.appendChild(o);
        });
        var hint = document.getElementById('env-system-hint');
        if (hint) hint.textContent = systems.length + ' tool' + (systems.length !== 1 ? 's' : '');
    }

    // Keep for backward compat (hidden category select)
    function populateCategories() {
        var sel = document.getElementById('tr-env-category');
        if (!sel) return;
        var cats = Object.keys(CATEGORY_MAP).sort();
        cats.forEach(function (cat) {
            var o = document.createElement('option');
            o.value = cat;
            o.textContent = formatCategory(cat) + ' (' + CATEGORY_MAP[cat].length + ')';
            sel.appendChild(o);
        });
    }

    function populateEnvironments() {
        var sel = document.getElementById('tr-env');
        var systemFilter = document.getElementById('tr-env-system') ? document.getElementById('tr-env-system').value : '';
        sel.innerHTML = '<option value="">— Select environment —</option>';

        var envs = systemFilter ? (SYSTEM_MAP[systemFilter] || []) : ALL_ENVIRONMENTS;
        envs.sort(function (a, b) { return a.name.localeCompare(b.name); });

        envs.forEach(function (e) {
            var o = document.createElement('option');
            o.value = e.id;
            o.textContent = e.name;
            sel.appendChild(o);
        });

        var hint = document.getElementById('env-count-hint');
        if (hint) {
            hint.textContent = envs.length + ' environment' + (envs.length !== 1 ? 's' : '') +
                (systemFilter ? ' in ' + systemFilter : ' across ' + Object.keys(SYSTEM_MAP).length + ' software');
        }
    }

    function populateAlgorithms() {
        var container = document.getElementById('algo-group');
        (CFG.algorithms || []).forEach(function (a, i) {
            var id = 'algo-' + a.id;
            var html = '<label class="algo-option">' +
                '<input type="radio" name="tr-algorithm" value="' + a.id + '"' + (i === 0 ? ' checked' : '') + ' id="' + id + '">' +
                '<div><span class="algo-label">' + esc(a.name) + '</span>' +
                (a.recommended ? '<span class="algo-rec">(Recommended)</span>' : '') +
                '<div class="algo-desc">' + esc(a.description) + '</div></div>' +
                '</label>';
            container.insertAdjacentHTML('beforeend', html);
        });
    }

    function _renderVerifierOptions(matches) {
        var field = document.getElementById('verifier-field');
        var container = document.getElementById('verifier-options');
        var countHint = document.getElementById('verifier-count-hint');
        var selectAll = document.getElementById('verifier-select-all');
        if (!field || !container) return;

        container.innerHTML = '';
        if (matches.length > 0) {
            field.style.display = '';
            matches.forEach(function (v) {
                var lbl = document.createElement('label');
                var cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.value = v.id;
                cb.dataset.verifierType = v.type || '';
                cb.addEventListener('change', onVerifierCheckboxChange);
                lbl.appendChild(cb);
                lbl.appendChild(document.createTextNode(' ' + v.name + ' (' + v.type + ')'));
                container.appendChild(lbl);
            });
            if (countHint) countHint.textContent = '(' + matches.length + ')';
            if (selectAll) {
                selectAll.checked = false;
                selectAll.onchange = function () {
                    var cbs = container.querySelectorAll('input[type="checkbox"]');
                    cbs.forEach(function (cb) { cb.checked = selectAll.checked; });
                    onVerifierCheckboxChange();
                };
            }
        } else {
            field.style.display = 'none';
            if (countHint) countHint.textContent = '';
        }
        // Reset HIL panel
        var hilPanel = document.getElementById('existing-hil-panel');
        if (hilPanel) hilPanel.style.display = 'none';
    }

    function populateVerifiers() {
        var env = findEnv(document.getElementById('tr-env') ? document.getElementById('tr-env').value : '');
        if (!env) {
            // No environment selected — hide verifiers
            var field = document.getElementById('verifier-field');
            var container = document.getElementById('verifier-options');
            var countHint = document.getElementById('verifier-count-hint');
            if (container) container.innerHTML = '';
            if (field) field.style.display = 'none';
            if (countHint) countHint.textContent = '';
            return;
        }
        var cat = env ? env.category : '';
        var envId = env ? env.id : '';

        // Start with built-in verifiers from verifier-data.js — match detail page logic exactly
        var isCustomEnv = env && env.source === 'custom';
        var builtInMatches = VERIFIERS.filter(function (v) {
            if (v.envName) return v.envName === envId;
            if (isCustomEnv) return false;
            return v.environment === cat;
        });

        // Also fetch custom verifiers from backend API and merge
        var apiBase = window.API_BASE || '';
        fetch(apiBase + '/api/verifiers')
            .then(function (res) { return res.ok ? res.json() : { verifiers: [] }; })
            .then(function (data) {
                var customVerifiers = (data.verifiers || []).filter(function (v) {
                    var vEnvName = v.envName || v.env_name || '';
                    if (vEnvName) return vEnvName === envId;
                    if (isCustomEnv) return false;
                    return v.environment === cat;
                });
                // Merge: avoid duplicates by id
                var seenIds = {};
                var allMatches = [];
                builtInMatches.forEach(function (v) { seenIds[v.id] = true; allMatches.push(v); });
                customVerifiers.forEach(function (v) {
                    if (!seenIds[v.id]) { seenIds[v.id] = true; allMatches.push(v); }
                });
                _renderVerifierOptions(allMatches);
            })
            .catch(function () {
                // Fallback to built-in only
                _renderVerifierOptions(builtInMatches);
            });
    }

    function onVerifierCheckboxChange() {
        var container = document.getElementById('verifier-options');
        var hilPanel = document.getElementById('existing-hil-panel');
        if (!container || !hilPanel) return;
        var checked = container.querySelectorAll('input[type="checkbox"]:checked');
        var hasHil = false;
        checked.forEach(function (cb) {
            var t = cb.dataset.verifierType || '';
            if (t === 'human-eval' || t === 'human_evaluation') hasHil = true;
        });
        if (hasHil) {
            hilPanel.style.display = '';
            // Populate default conditions if empty
            var rows = document.getElementById('existing-condition-rows');
            if (rows && rows.children.length === 0) {
                addExistingConditionRow('Correct resolution', '0.4');
                addExistingConditionRow('Proper status transitions', '0.3');
                addExistingConditionRow('Communication quality', '0.3');
            }
        } else {
            hilPanel.style.display = 'none';
        }
    }

    function populateActions() {
        var field = document.getElementById('action-field');
        var container = document.getElementById('action-options');
        var countHint = document.getElementById('action-count-hint');
        var selectAll = document.getElementById('action-select-all');
        if (!field || !container) return;

        // Actions only appear after a scenario is selected
        var scenarioVal = document.getElementById('tr-scenario') ? document.getElementById('tr-scenario').value : '';
        var actions = [];

        if (scenarioVal) {
            // Find the selected scenario and use its expected_workflow as actions
            var allScenarios = getAllScenarios();
            var scenario = allScenarios.filter(function (s) { return s.id === scenarioVal; })[0];
            if (scenario && scenario.expected_workflow && scenario.expected_workflow.length > 0) {
                actions = scenario.expected_workflow;
            } else {
                // Fallback: use the environment's actions if scenario has no expected_workflow
                var env = findEnv(document.getElementById('tr-env').value);
                actions = (env && env.actions) ? env.actions : [];
            }
        }

        container.innerHTML = '';
        if (actions.length > 0) {
            field.style.display = '';
            actions.forEach(function (a) {
                var lbl = document.createElement('label');
                var cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.value = a;
                cb.checked = false;
                lbl.appendChild(cb);
                lbl.appendChild(document.createTextNode(' ' + a));
                container.appendChild(lbl);
            });
            if (countHint) countHint.textContent = '(' + actions.length + ')';
            if (selectAll) {
                selectAll.checked = false;
                selectAll.onchange = function () {
                    var cbs = container.querySelectorAll('input[type="checkbox"]');
                    cbs.forEach(function (cb) { cb.checked = selectAll.checked; });
                };
            }
        } else {
            field.style.display = 'none';
            if (countHint) countHint.textContent = '';
        }
    }

    // Populate scenario dropdown based on selected environment / system
    function filterScenarios() {
        var scenarioField = document.getElementById('scenario-field');
        var scenarioSel = document.getElementById('tr-scenario');
        var countHint = document.getElementById('scenario-count-hint');
        if (!scenarioField || !scenarioSel) return;

        var envVal = document.getElementById('tr-env') ? document.getElementById('tr-env').value : '';
        var env = findEnv(envVal);
        if (!env) {
            // No environment selected — hide scenarios
            scenarioSel.innerHTML = '<option value="">— Select scenario —</option>';
            scenarioField.style.display = 'none';
            if (countHint) countHint.textContent = '';
            return;
        }
        var cat = env ? env.category : '';
        var envId = env ? env.id : '';
        var envName = env ? env.name : '';
        var system = env ? env.system : '';

        // Merge built-in + custom scenarios, filter to match detail page logic exactly
        var allScenarios = getAllScenarios();
        var isCustomEnv = env && env.source === 'custom';
        var matches = allScenarios.filter(function (s) {
            // If scenario has an environment field, it must match the raw env name exactly
            if (s.environment) return s.environment === envId;
            // Custom/cloned envs: skip category-level built-ins
            if (isCustomEnv) return false;
            // Otherwise, match by category or product against raw env name
            return s.category === cat || s.product === envId;
        });

        // Rebuild dropdown
        scenarioSel.innerHTML = '<option value="">— Select scenario —</option>';
        if (matches.length > 0) {
            scenarioField.style.display = '';
            matches.forEach(function (s) {
                var o = document.createElement('option');
                o.value = s.id;
                o.textContent = s.name + (s.task_count ? ' (' + s.task_count + ' tasks)' : '');
                scenarioSel.appendChild(o);
            });
            if (countHint) countHint.textContent = '(' + matches.length + ')';
        } else {
            scenarioField.style.display = 'none';
            if (countHint) countHint.textContent = '';
        }
    }

    function updateEnvPreview() {
        var envId = document.getElementById('tr-env').value;
        var env = findEnv(envId);

        // Update Software inline hint below environment dropdown
        var toolsField = document.getElementById('tools-display-field');
        var toolsValue = document.getElementById('tools-display-value');
        if (toolsField && toolsValue) {
            if (env && env.system) {
                toolsValue.textContent = env.system;
                toolsField.style.display = 'block';
            } else {
                toolsField.style.display = 'none';
            }
        }
    }

    function filterAgents() {
        var env = findEnv(document.getElementById('tr-env').value);
        var cat = env ? env.category : '';
        var sel = document.getElementById('tr-agent');
        sel.innerHTML = '<option value="">— Select agent —</option>';
        (CFG.agents || []).forEach(function (a) {
            if (!a.trainable) return;
            if (cat && a.compatible_categories && a.compatible_categories.indexOf(cat) === -1) return;
            var o = document.createElement('option');
            o.value = a.id;
            o.textContent = a.name + ' (' + a.base_model + ')';
            sel.appendChild(o);
        });
    }

    function onSystemChange() {
        populateEnvironments();
        document.getElementById('tr-env').value = '';
        onEnvironmentChange();
    }

    // Keep for backward compat
    function onCategoryChange() {
        populateEnvironments();
        document.getElementById('tr-env').value = '';
        onEnvironmentChange();
    }

    function onEnvironmentChange() {
        updateEnvPreview();
        filterScenarios();
        // Hide actions until a scenario is selected
        var actionField = document.getElementById('action-field');
        if (actionField) actionField.style.display = 'none';
        populateVerifiers();
        filterAgents();
        updateVerifierSystem();
    }

    function onScenarioChange() {
        populateActions();
    }

    function initVerifierToggle() {
        // Removed — create new verifier is no longer available here
    }

    function initVerifierType() {
        // Removed — create new verifier panel no longer exists
    }

    function updateVerifierSystem() {
        var envSel = document.getElementById('tr-env');
        var systemInput = document.getElementById('tr-verifier-system');
        if (!systemInput) return;
        var env = findEnv(envSel ? envSel.value : '');
        var system = '';
        if (env && env.system) {
            system = env.system;
        } else if (env && env.category) {
            system = formatCategory(env.category);
        }
        systemInput.value = system || '';
    }

    function addConditionRow(cond, weight) {
        var container = document.getElementById('condition-rows');
        var rowCount = container.querySelectorAll('.condition-row').length;
        var html = '<div class="condition-row">' +
            '<input type="text" class="cond-name" placeholder="Condition" value="' + esc(cond || '') + '">' +
            '<input type="number" class="cond-weight" placeholder="0.0" step="0.1" min="0" max="1" value="' + esc(weight || '') + '">' +
            '<button type="button" class="remove-btn" title="Remove"' + (rowCount === 0 ? ' disabled' : '') + '>' +
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
            '</button></div>';
        container.insertAdjacentHTML('beforeend', html);
        updateRemoveButtons();
    }

    function updateRemoveButtons() {
        var rows = document.querySelectorAll('#condition-rows .condition-row');
        rows.forEach(function (r) {
            r.querySelector('.remove-btn').disabled = rows.length <= 1;
        });
    }

    function initConditionRows() {
        var addBtn = document.getElementById('btn-add-condition');
        var rowsEl = document.getElementById('condition-rows');
        if (addBtn) {
            addBtn.addEventListener('click', function () {
                addConditionRow('', '');
            });
        }
        if (rowsEl) {
            rowsEl.addEventListener('click', function (e) {
                var btn = e.target.closest('.remove-btn');
                if (btn && !btn.disabled) {
                    btn.closest('.condition-row').remove();
                    updateRemoveButtons();
                }
            });
        }
    }

    function initExistingVerifierChange() {
        // Verifier is now multi-select checkboxes — HIL panel handled by onVerifierCheckboxChange()
        // This function retained for backward compat but is now a no-op
    }

    function addExistingConditionRow(cond, weight) {
        var container = document.getElementById('existing-condition-rows');
        var rowCount = container.querySelectorAll('.condition-row').length;
        var html = '<div class="condition-row">' +
            '<input type="text" class="cond-name" placeholder="Condition" value="' + esc(cond || '') + '">' +
            '<input type="number" class="cond-weight" placeholder="0.0" step="0.1" min="0" max="1" value="' + esc(weight || '') + '">' +
            '<button type="button" class="remove-btn" title="Remove"' + (rowCount === 0 ? ' disabled' : '') + '>' +
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
            '</button></div>';
        container.insertAdjacentHTML('beforeend', html);
        updateExistingRemoveButtons();
    }

    function updateExistingRemoveButtons() {
        var rows = document.querySelectorAll('#existing-condition-rows .condition-row');
        rows.forEach(function (r) {
            r.querySelector('.remove-btn').disabled = rows.length <= 1;
        });
    }

    function initExistingConditionRows() {
        document.getElementById('btn-add-existing-condition').addEventListener('click', function () {
            addExistingConditionRow('', '');
        });
        document.getElementById('existing-condition-rows').addEventListener('click', function (e) {
            var btn = e.target.closest('.remove-btn');
            if (btn && !btn.disabled) {
                btn.closest('.condition-row').remove();
                updateExistingRemoveButtons();
            }
        });
    }

    function initLoraToggle() {
        var btn = document.getElementById('lora-toggle');
        var panel = document.getElementById('lora-params');
        btn.addEventListener('click', function () {
            btn.classList.toggle('open');
            panel.classList.toggle('open');
        });
    }

    // ─── Prefill Sample Data ────────────────────────────────────
    function prefillSampleData() {
        // Select Jira system
        var systemSel = document.getElementById('tr-env-system');
        if (systemSel) {
            // Find the Jira option
            for (var i = 0; i < systemSel.options.length; i++) {
                if (systemSel.options[i].value.toLowerCase().indexOf('jira') !== -1) {
                    systemSel.value = systemSel.options[i].value;
                    break;
                }
            }
            onSystemChange();
        }

        setTimeout(function () {
            document.getElementById('tr-env').value = 'JiraIssueResolution';
            onEnvironmentChange();

            var nameField = document.getElementById('tr-name');
            if (!nameField.value.trim()) {
                nameField.value = 'train_jira_grpo_sample_' + new Date().toISOString().slice(0, 10).replace(/-/g, '_');
            }
            var descField = document.getElementById('tr-desc');
            if (!descField.value.trim()) {
                descField.value = 'Sample GRPO training run on Jira Issue Resolution environment';
            }

            var agentSel = document.getElementById('tr-agent');
            if (agentSel.options.length > 1) agentSel.selectedIndex = 1;

            var grpoRadio = document.querySelector('input[name="tr-algorithm"][value="GRPO"]');
            if (grpoRadio) grpoRadio.checked = true;

            document.getElementById('tr-episodes').value = '10';
            document.getElementById('tr-steps').value = '50';

            showToast('Sample data loaded. Click Start Training to begin.', 'success');
        }, 100);
    }

    // ─── Submit ─────────────────────────────────────────────────
    function submitNewTraining() {
        var name = document.getElementById('tr-name').value.trim();
        var envId = document.getElementById('tr-env').value;
        if (!name) { showToast('Please enter a run name.', 'error'); return; }
        if (!envId) { showToast('Please select an environment.', 'error'); return; }

        var env = findEnv(envId);

        var body = {
            run_name: name,
            description: document.getElementById('tr-desc').value.trim(),
            scenario: envId,
            environment: envId,
            category: env ? env.category : '',
            agent: document.getElementById('tr-agent').value,
            model: getAgentModel(document.getElementById('tr-agent').value),
            algorithm: getSelectedAlgorithm(),
            num_episodes: parseInt(document.getElementById('tr-episodes').value) || 320,
            max_steps: parseInt(document.getElementById('tr-steps').value) || 50,
            lora: {
                r: parseInt(document.getElementById('lora-r').value) || 32,
                lora_alpha: parseInt(document.getElementById('lora-alpha').value) || 16,
                lora_dropout: parseFloat(document.getElementById('lora-dropout').value) || 0.05,
                bias: document.getElementById('lora-bias').value,
                task_type: document.getElementById('lora-task-type').value,
                target_modules: document.getElementById('lora-target').value
            }
        };

        // ── Advanced optional configuration ──
        var _advVal = function (id) { var el = document.getElementById(id); return el ? el.value.trim() : ''; };
        var _advInt = function (id) { var v = _advVal(id); return v ? parseInt(v) : null; };

        var advMaxSteps = _advInt('adv-max-steps');
        var advBatchSize = _advInt('adv-batch-size');
        var advRollouts = _advInt('adv-rollouts');
        var advSamplingTokens = _advInt('adv-sampling-max-tokens');
        var advEnvId = _advVal('adv-env-id');
        var advEnvArgsRaw = _advVal('adv-env-args');
        var advWandbProject = _advVal('adv-wandb-project');
        var advWandbName = _advVal('adv-wandb-name');

        if (advMaxSteps) body.adv_max_steps = advMaxSteps;
        if (advBatchSize) body.batch_size = advBatchSize;
        if (advRollouts) body.rollouts_per_example = advRollouts;

        if (advSamplingTokens) {
            body.sampling = { max_tokens: advSamplingTokens };
        }

        if (advEnvId || advEnvArgsRaw) {
            body.env_override = {};
            if (advEnvId) body.env_override.id = advEnvId;
            if (advEnvArgsRaw) {
                try { body.env_override.args = JSON.parse(advEnvArgsRaw); } catch (e) {
                    showToast('Invalid JSON in env args', 'error');
                    return;
                }
            }
        }

        if (advWandbProject || advWandbName) {
            body.wandb = {};
            if (advWandbProject) body.wandb.project = advWandbProject;
            if (advWandbName) body.wandb.name = advWandbName;
        }

        // Scenario (optional — from the scenario dropdown)
        var scenarioVal = document.getElementById('tr-scenario') ? document.getElementById('tr-scenario').value : '';
        if (scenarioVal) body.scenario_id = scenarioVal;

        // Actions — collect checked actions
        var actionCbs = document.querySelectorAll('#action-options input[type="checkbox"]:checked');
        if (actionCbs.length > 0) {
            body.actions = [];
            actionCbs.forEach(function (cb) { body.actions.push(cb.value); });
        }

        // Verifiers — collect all checked verifier IDs (multi-select)
        var verifierCbs = document.querySelectorAll('#verifier-options input[type="checkbox"]:checked');
        body.verifier_ids = [];
        verifierCbs.forEach(function (cb) { body.verifier_ids.push(cb.value); });
        // Backward compat: also set verifier_id as first selected
        body.verifier_id = body.verifier_ids.length > 0 ? body.verifier_ids[0] : '';
        // Include conditions if any HIL verifier is selected
        var existingHilPanel = document.getElementById('existing-hil-panel');
        if (existingHilPanel && existingHilPanel.style.display !== 'none') {
            body.verifier_conditions = [];
            document.querySelectorAll('#existing-condition-rows .condition-row').forEach(function (row) {
                body.verifier_conditions.push({
                    condition: row.querySelector('.cond-name').value.trim(),
                    weight: parseFloat(row.querySelector('.cond-weight').value) || 0
                });
            });
        }

        showToast('Starting training run: ' + name, 'info');

        fetch((window.API_BASE || '') + '/train/' + encodeURIComponent(envId), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        }).then(function (res) {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.json();
        }).then(function (data) {
            showToast('Training run started successfully!', 'success');
            var newRun = {
                id: data.job_id || 'run_' + Date.now(),
                job_id: data.job_id || 'run_' + Date.now(),
                name: name,
                description: body.description,
                status: 'running',
                environment: envId,
                environmentDisplay: env ? env.name : envId,
                category: env ? env.category : '',
                model: getAgentModel(body.agent),
                algorithm: body.algorithm,
                progress: 0,
                started: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
                episodes: 0,
                successRate: null,
                avgReward: null,
                baselineReward: null,
                results: null,
                baseline_results: null,
                model_saved: false,
                model_url: data.model_url || null,
                hil_required: false,
                human_evaluations: []
            };
            CFG.trainingRuns = CFG.trainingRuns || [];
            CFG.trainingRuns.unshift(newRun);
            showRunDetails(newRun.id);
        }).catch(function (err) {
            showToast('Failed to start training: ' + err.message, 'error');
        });
    }

    // ─── Run Details ────────────────────────────────────────────
    function showRunDetails(runId) {
        var run = (CFG.trainingRuns || []).find(function (r) { return r.id === runId; });
        if (!run) { showToast('Run not found', 'error'); return; }

        showView('details');
        renderRunDetails(run);

        // For real API runs (non-mock IDs), fetch live data and re-render
        if (runId && runId.indexOf('run_') !== 0) {
            fetch((window.API_BASE || '') + '/training/' + encodeURIComponent(runId))
                .then(function (res) { return res.ok ? res.json() : null; })
                .then(function (apiData) {
                    if (!apiData) return;
                    run.status = apiData.status || run.status;
                    run.results = apiData.results || run.results;
                    run.baseline_results = apiData.baseline_results || run.baseline_results;
                    run.model_url = apiData.model_url || run.model_url;
                    run.model_saved = apiData.model_saved || run.model_saved;
                    run.model_metadata = apiData.model_metadata || run.model_metadata;
                    run.hil_required = apiData.hil_required;
                    run.human_evaluations = apiData.human_evaluations || run.human_evaluations;
                    run.progress = apiData.progress != null ? apiData.progress : run.progress;
                    if (apiData.results) {
                        run.avgReward = apiData.results.mean_reward;
                        run.episodes = apiData.results.episodes_completed || apiData.results.total_episodes;
                    }
                    if (apiData.baseline_results) {
                        run.baselineReward = apiData.baseline_results.mean_reward;
                    }
                    renderRunDetails(run);
                })
                .catch(function () { /* keep showing cached data */ });
        }
    }

    function renderRunDetails(run) {
        var envDisplay = run.environmentDisplay || humanizeName(run.environment) || run.environment;
        var apiBase = window.API_BASE || '';
        var statusLabel = capFirst(run.status);

        // Header
        try {
            document.getElementById('detail-title').textContent = run.name;
            var badge = document.getElementById('detail-status');
            badge.textContent = statusLabel;
            badge.className = 'status-badge ' + run.status;
        } catch (e) { console.warn('renderRunDetails: header error', e); }

        // Action buttons
        try {
            var actionsEl = document.getElementById('detail-actions');
            var actionsHtml = '';
            if (run.status === 'completed' || run.status === 'awaiting_human_eval') {
                var hilUrl = '/human-eval?job_id=' + encodeURIComponent(run.job_id || run.id);
                actionsHtml += '<a href="' + esc(hilUrl) + '" class="btn btn-secondary btn-small" target="_blank">' +
                    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><polyline points="17 11 19 13 23 9"/></svg> ' +
                    'Human Evaluation</a>';
            }
            if (run.model_saved && run.model_url) {
                actionsHtml += '<button type="button" class="btn btn-primary btn-small" id="btn-view-model-artifact">' +
                    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> ' +
                    'Export Model</button>';
            }
            actionsEl.innerHTML = actionsHtml;
            var viewArtifactBtn = document.getElementById('btn-view-model-artifact');
            if (viewArtifactBtn) {
                viewArtifactBtn.addEventListener('click', function () {
                    var wrap = document.getElementById('detail-model-artifact-wrap');
                    if (wrap) {
                        wrap.style.display = '';
                        wrap.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                });
            }
        } catch (e) { console.warn('renderRunDetails: actions error', e); }

        // Training Progress Stepper
        try {
            var stepperEl = document.getElementById('detail-stepper');
            if (stepperEl) {
                var steps = [
                    { label: 'Configuration' },
                    { label: 'Baseline Eval' },
                    { label: 'Training' },
                    { label: 'Evaluation' },
                    { label: 'Complete' }
                ];
                var currentStep = 0; // default: config done
                if (run.status === 'running') {
                    var prog = run.progress || 0;
                    if (prog < 10) currentStep = 1;
                    else if (prog < 95) currentStep = 2;
                    else currentStep = 3;
                } else if (run.status === 'completed' || run.status === 'awaiting_human_eval') {
                    currentStep = 5; // all steps completed
                } else if (run.status === 'failed') {
                    currentStep = -1; // show all as pending except config
                }
                var stepperHtml = '';
                for (var si = 0; si < steps.length; si++) {
                    var cls = 'stepper-step';
                    var circleContent = '' + (si + 1);
                    if (currentStep === -1) {
                        // failed: only config completed
                        cls += si === 0 ? ' completed' : '';
                    } else if (si < currentStep) {
                        cls += ' completed';
                        circleContent = '\u2713'; // checkmark
                    } else if (si === currentStep) {
                        cls += ' active';
                    }
                    stepperHtml += '<div class="' + cls + '">' +
                        '<div class="stepper-circle">' + circleContent + '</div>' +
                        '<div class="stepper-label">' + esc(steps[si].label) + '</div>';
                    if (si === currentStep && run.status === 'running' && si === 2) {
                        stepperHtml += '<div class="stepper-progress">' + (run.progress || 0) + '%</div>';
                    }
                    stepperHtml += '</div>';
                }
                stepperEl.innerHTML = stepperHtml;
            }
        } catch (e) { console.warn('renderRunDetails: stepper error', e); }

        // Failure reason panel
        try {
            var failurePanel = document.getElementById('detail-failure-reason');
            if (failurePanel) {
                if (run.status === 'failed') {
                    var reason = run.error || run.fail_reason || 'An unexpected error occurred during training.';
                    failurePanel.style.display = '';
                    failurePanel.innerHTML = '<h4>' +
                        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>' +
                        ' Training Failed</h4>' +
                        '<p class="failure-message">' + esc(reason) + '</p>';
                } else {
                    failurePanel.style.display = 'none';
                    failurePanel.innerHTML = '';
                }
            }
        } catch (e) { console.warn('renderRunDetails: failure panel error', e); }

        // Metric cards
        try {
            var metrics = document.getElementById('detail-metrics');
            var maxRewardLabel = (run.results && run.results.max_reward != null) ? run.results.max_reward.toFixed(2) : '—';
            metrics.innerHTML = metricCard('Episodes', run.episodes || '—') +
                metricCard('Success Rate', run.successRate != null ? run.successRate + '%' : '—') +
                metricCard('Avg Reward', run.avgReward != null ? run.avgReward.toFixed(2) : '—') +
                metricCard('Improvement', run.baselineReward != null && run.avgReward != null
                    ? (function () { var diff = (run.avgReward - run.baselineReward) * 100; return (diff >= 0 ? '+' : '') + diff.toFixed(0) + '%'; })()
                    : '—', true);
        } catch (e) { console.warn('renderRunDetails: metrics error', e); }

        // Training info panel
        try {
            var _trainingInfoHtml = '<h3>Training Information</h3>' +
                infoRow('Environment', envDisplay) +
                infoRow('Category', formatCategory(run.category)) +
                infoRow('Algorithm', run.algorithm) +
                infoRow('Status', statusLabel) +
                infoRow('Started', run.started || '—') +
                (run.completed ? infoRow('Completed', run.completed) : '') +
                infoRow('Progress', run.progress + '%');

            // Show advanced config if present
            if (run.adv_max_steps || run.batch_size || run.rollouts_per_example || run.sampling || run.env_override || run.wandb) {
                _trainingInfoHtml += '<div style="margin-top:0.75rem;padding-top:0.75rem;border-top:1px solid var(--border-color)">' +
                    '<h4 style="font-size:0.85rem;font-weight:600;margin-bottom:0.5rem">Advanced Config</h4>';
                if (run.adv_max_steps) _trainingInfoHtml += infoRow('max_steps', run.adv_max_steps);
                if (run.batch_size) _trainingInfoHtml += infoRow('batch_size', run.batch_size);
                if (run.rollouts_per_example) _trainingInfoHtml += infoRow('rollouts_per_example', run.rollouts_per_example);
                if (run.sampling && run.sampling.max_tokens) _trainingInfoHtml += infoRow('sampling.max_tokens', run.sampling.max_tokens);
                if (run.env_override) {
                    if (run.env_override.id) _trainingInfoHtml += infoRow('env.id', run.env_override.id);
                    if (run.env_override.args) _trainingInfoHtml += infoRow('env.args', '<code style="font-size:0.8rem">' + JSON.stringify(run.env_override.args) + '</code>');
                }
                if (run.wandb) {
                    if (run.wandb.project) _trainingInfoHtml += infoRow('wandb.project', run.wandb.project);
                    if (run.wandb.name) _trainingInfoHtml += infoRow('wandb.name', run.wandb.name);
                }
                _trainingInfoHtml += '</div>';
            }
            document.getElementById('detail-training-info').innerHTML = _trainingInfoHtml;

            // Model / Compute config
            var modelHtml = '<h3>Model &amp; Compute</h3>' +
                infoRow('Base Model', run.model) +
                infoRow('LoRA r', '32') +
                infoRow('LoRA alpha', '16') +
                infoRow('Dropout', '0.05') +
                infoRow('Task Type', 'CAUSAL_LM');
            if (run.results) {
                modelHtml += '<div style="margin-top:0.75rem;padding-top:0.75rem;border-top:1px solid var(--border-color)">' +
                    '<h4 style="font-size:0.85rem;font-weight:600;margin-bottom:0.5rem">Results</h4>' +
                    infoRow('Mean Reward', run.results.mean_reward != null ? run.results.mean_reward.toFixed(4) : '—') +
                    infoRow('Max Reward', run.results.max_reward != null ? run.results.max_reward.toFixed(4) : '—') +
                    infoRow('Min Reward', run.results.min_reward != null ? run.results.min_reward.toFixed(4) : '—') +
                    '</div>';
            }
            if (run.baseline_results) {
                modelHtml += '<div style="margin-top:0.75rem;padding-top:0.75rem;border-top:1px solid var(--border-color)">' +
                    '<h4 style="font-size:0.85rem;font-weight:600;margin-bottom:0.5rem">Baseline</h4>' +
                    infoRow('Mean Reward', run.baseline_results.mean_reward != null ? run.baseline_results.mean_reward.toFixed(4) : '—') +
                    infoRow('Max Reward', run.baseline_results.max_reward != null ? run.baseline_results.max_reward.toFixed(4) : '—') +
                    infoRow('Episodes', run.baseline_results.episodes || '—') +
                    '</div>';
            }
            document.getElementById('detail-model-config').innerHTML = modelHtml;
        } catch (e) { console.warn('renderRunDetails: info/model error', e); }

        // Rollout comparison — only show when training is complete
        try {
            var rolloutEl = document.getElementById('detail-rollout');
            var rolloutWrap = rolloutEl ? rolloutEl.closest('.details-full') : null;
            if (run.status === 'completed' || run.status === 'awaiting_human_eval') {
                if (rolloutWrap) rolloutWrap.style.display = '';
                if (window.renderRolloutComparison) {
                    loadAndRenderRolloutComparison(rolloutEl, run);
                } else {
                    rolloutEl.innerHTML = '<p style="color:var(--text-secondary);padding:1rem;">Rollout comparison module not loaded.</p>';
                }
            } else {
                // Hide rollout for running/pending/failed runs
                if (rolloutWrap) rolloutWrap.style.display = 'none';
            }

            // State diagram — render from rollout data above model artifact
            var diagramEl = document.getElementById('detail-state-diagram');
            if (diagramEl && (run.status === 'completed' || run.status === 'awaiting_human_eval')) {
                renderStateDiagram(diagramEl, run);
            } else if (diagramEl) {
                var diagramWrap = document.getElementById('detail-state-diagram-wrap');
                if (diagramWrap) diagramWrap.style.display = 'none';
            }
        } catch (e) { console.warn('renderRunDetails: rollout/diagram error', e); }

        // Model artifact
        try {
            var artifactWrap = document.getElementById('detail-model-artifact-wrap');
            var artifactPanel = document.getElementById('detail-model-artifact');
            if (run.status === 'completed' && (run.model_url || run.model_saved)) {
                artifactWrap.style.display = '';
                var artifactHtml = '<h3>Model Artifact</h3>' +
                    infoRow('Status', run.model_saved ? 'Saved' : 'Pending') +
                    infoRow('Format', 'stable-baselines3 (.zip)') +
                    infoRow('Algorithm', run.algorithm || '—') +
                    infoRow('Base Model', run.model || '—');
                if (run.model_metadata) {
                    if (run.model_metadata.base_model || run.model_metadata.model) {
                        artifactHtml = artifactHtml.replace(
                            infoRow('Base Model', run.model || '\u2014'),
                            infoRow('Base Model', run.model_metadata.base_model || run.model_metadata.model || run.model || '\u2014')
                        );
                    }
                    artifactHtml += infoRow('Episodes Completed', run.model_metadata.total_episodes_completed || run.model_metadata.num_episodes || '\u2014');
                    if (run.model_metadata.timestamp) {
                        artifactHtml += infoRow('Saved At', fmtTimestamp(run.model_metadata.timestamp));
                    }
                }
                if (run.model_url) {
                    artifactHtml += '<div class="info-row" style="margin-top:0.5rem">' +
                        '<span class="info-label">Model Path</span>' +
                        '<span class="info-value" style="display:flex;align-items:center;gap:0.5rem">' +
                        '<code style="font-size:0.8rem;word-break:break-all">' + esc(run.model_url) + '</code>' +
                        '<button type="button" id="btn-copy-model-path" style="border:none;background:none;cursor:pointer;padding:2px;color:var(--accent-primary);flex-shrink:0" title="Copy path">' +
                        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>' +
                        '</button></span></div>';
                }
                artifactPanel.innerHTML = artifactHtml;
                var copyBtn = document.getElementById('btn-copy-model-path');
                if (copyBtn && run.model_url) {
                    copyBtn.addEventListener('click', function () {
                        navigator.clipboard.writeText(run.model_url).then(function () {
                            showToast('Model path copied to clipboard', 'success');
                        }).catch(function () {
                            showToast(run.model_url, 'info');
                        });
                    });
                }
            } else {
                artifactWrap.style.display = 'none';
            }
        } catch (e) { console.warn('renderRunDetails: artifact error', e); }

        // Canvas charts
        try { renderProgressChart(run); } catch (e) { console.warn('renderRunDetails: progress chart error', e); }
        try { renderFailureChart(run); } catch (e) { console.warn('renderRunDetails: failure chart error', e); }

        // Performance panel
        try {
            document.getElementById('detail-performance').innerHTML =
                '<h3>Performance Improvement</h3>' +
                perfRow('Task Completion', '23%', run.successRate != null ? run.successRate + '%' : '—', run.successRate != null ? '+' + (run.successRate - 23).toFixed(0) + '%' : '') +
                perfRow('Avg Steps', '12.4', run._mock_trained_rollout ? run._mock_trained_rollout.total_steps : '7.1', run._mock_trained_rollout ? '-' + Math.round((1 - run._mock_trained_rollout.total_steps / 12.4) * 100) + '%' : '-43%') +
                perfRow('Error Rate', '31%', '8.2%', '-74%');

            // Efficiency panel
            document.getElementById('detail-efficiency').innerHTML =
                '<h3>Efficiency Gains</h3>' +
                perfRow('Tokens per Episode', '1,240', '890', '-28%') +
                perfRow('Avg Latency', '3.2s', '2.1s', '-34%') +
                perfRow('Tool Calls per Task', '8.5', run._mock_trained_rollout ? String(run._mock_trained_rollout.total_steps) : '5.2', run._mock_trained_rollout ? '-' + Math.round((1 - run._mock_trained_rollout.total_steps / 8.5) * 100) + '%' : '-39%');
        } catch (e) { console.warn('renderRunDetails: performance/efficiency error', e); }

        // Trade-off note
        try {
            var note = document.getElementById('detail-tradeoff');
            if (run.status === 'completed') {
                note.style.display = '';
                note.innerHTML = '<strong>Trade-off Note:</strong> While overall success rate improved significantly, the model shows slightly higher latency on multi-step workflows. Consider fine-tuning with trajectory-focused verifiers for complex scenarios.';
            } else if (run.status === 'awaiting_human_eval') {
                note.style.display = '';
                note.innerHTML = '<strong>Awaiting Human Evaluation:</strong> Training is complete but requires human-in-the-loop review before the model can be deployed. Click "Human Evaluation" above to begin the review process.';
            } else {
                note.style.display = 'none';
            }
        } catch (e) { console.warn('renderRunDetails: tradeoff error', e); }
    }

    // ─── Rollout Comparison ─────────────────────────────────────
    function loadAndRenderRolloutComparison(container, run) {
        var envDisplay = run.environmentDisplay || humanizeName(run.environment) || run.environment;
        var meta = {
            scenarioName: envDisplay,
            envName: run.environment,
            trainedLabel: 'Trained Policy (' + (run.algorithm || 'GRPO') + ')'
        };

        // Mock mode: use inline rollout data
        if (run._mock_baseline_rollout || run._mock_trained_rollout) {
            container.innerHTML = '';
            window.renderRolloutComparison(
                container,
                run._mock_baseline_rollout || null,
                run._mock_trained_rollout || null,
                meta
            );
            return;
        }

        // API mode: fetch from rollout-comparison endpoint
        var jobId = run.job_id || run.id;
        container.innerHTML = '<p style="color:var(--text-secondary);padding:1rem;">Loading rollout comparison...</p>';

        fetch((window.API_BASE || '') + '/api/rollout-comparison/' + encodeURIComponent(run.environment) + '?job_id=' + encodeURIComponent(jobId))
            .then(function (res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function (data) {
                if (!data.baseline && !data.trained) {
                    container.innerHTML = '<p style="color:var(--text-secondary);padding:1rem;">No rollout data available for this run.</p>';
                    return;
                }
                if (data.trained && data.trained.checkpoint_label) {
                    meta.trainedLabel = 'Trained Policy (' + (run.algorithm || 'GRPO') + ' \u00b7 ' + data.trained.checkpoint_label + ')';
                }
                container.innerHTML = '';
                window.renderRolloutComparison(container, data.baseline || null, data.trained || null, meta);
            })
            .catch(function () {
                container.innerHTML = '<p style="color:var(--text-secondary);padding:1rem;">No rollout data available for this run.</p>';
            });
    }

    // ─── Rollout State Diagram (SVG flowchart) ─────────────────
    function renderStateDiagram(container, run) {
        if (!container) return;
        var rollout = run._mock_trained_rollout || run._mock_baseline_rollout || null;
        if (!rollout && run._fetched_trained_rollout) rollout = run._fetched_trained_rollout;
        if (!rollout || !rollout.steps || !rollout.steps.length) {
            container.closest('#detail-state-diagram-wrap').style.display = 'none';
            return;
        }
        container.closest('#detail-state-diagram-wrap').style.display = '';

        /* ── Layout constants ── */
        var NW = 158, NH = 38, BR = 6;
        var PAD = 30;
        var HGAP = 62;
        var VGAP = 52;
        var STACK_GAP = 10;

        /* ── Colour palette per node kind ── */
        var CLR = {
            user: { bg: '#eff6ff', bdr: '#93c5fd', tx: '#1e40af' },
            agent: { bg: '#f0fdf4', bdr: '#86efac', tx: '#166534' },
            tool: { bg: '#fefce8', bdr: '#fde68a', tx: '#92400e' },
            final: { bg: '#f1f5f9', bdr: '#cbd5e1', tx: '#475569' },
            vPass: { bg: '#f0fdf4', bdr: '#86efac', tx: '#166534' },
            vFail: { bg: '#fdf2f8', bdr: '#f9a8d4', tx: '#9d174d' },
            reward: { bg: '#faf5ff', bdr: '#e9d5ff', tx: '#7c3aed' }
        };

        /* ── Helpers ── */
        function trunc(s, m) { return !s ? '' : s.length > m ? s.slice(0, m - 1) + '\u2026' : s; }
        function esvg(s) { return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }

        /* ── Build node / edge arrays ── */
        var gNodes = [], gEdges = [], nMap = {};
        function addN(id, kind, label, detail, x, y) {
            var n = { id: id, kind: kind, label: label, detail: detail || '', x: x, y: y, w: NW, h: NH };
            gNodes.push(n); nMap[id] = n; return n;
        }

        var col = 0;

        // 1) User Request
        var uDet = '';
        var s0 = rollout.steps[0];
        if (s0 && s0.timeline_events) {
            for (var q = 0; q < s0.timeline_events.length; q++) {
                if (s0.timeline_events[q].event_type === 'SYSTEM') { uDet = s0.timeline_events[q].content || ''; break; }
            }
        }
        addN('u0', 'user', 'User Request', trunc(uDet, 26), PAD + col * (NW + HGAP), PAD);
        col++;

        // 2) Steps  →  Agent node + tool chain below
        for (var i = 0; i < rollout.steps.length; i++) {
            var step = rollout.steps[i];
            var cx = PAD + col * (NW + HGAP);
            addN('a' + i, 'agent', 'Agent (Trained)', 'Step ' + step.step, cx, PAD);
            gEdges.push({ f: (i === 0 ? 'u0' : 'a' + (i - 1)), t: 'a' + i, ty: 'solid' });

            var evts = step.timeline_events || [];
            var ti = 0;
            for (var j = 0; j < evts.length; j++) {
                if (evts[j].event_type === 'TOOL_CALL') {
                    var tName = evts[j].tool_name || 'Tool';
                    var tArgs = '';
                    if (evts[j].tool_args) { try { tArgs = JSON.stringify(evts[j].tool_args); } catch (e) { /* */ } }
                    var tid = 't' + i + '_' + ti;
                    var ty = PAD + NH + VGAP + ti * (NH + STACK_GAP);
                    addN(tid, 'tool', trunc(tName, 22), trunc(tArgs, 26), cx, ty);
                    gEdges.push({ f: (ti === 0 ? 'a' + i : 't' + i + '_' + (ti - 1)), t: tid, ty: 'dashed-blue' });
                    ti++;
                }
            }
            if (step.reward != null) {
                var rid = 'r' + i;
                var ry = PAD + NH + VGAP + ti * (NH + STACK_GAP);
                addN(rid, 'reward', 'Reward  +' + step.reward.toFixed(2), '', cx, ry);
                gEdges.push({ f: (ti > 0 ? 't' + i + '_' + (ti - 1) : 'a' + i), t: rid, ty: 'dashed-blue' });
                ti++;
            }
            col++;
        }

        // 3) Final State
        var fs = rollout.final_environment_state || {};
        var fsParts = [];
        for (var fk in fs) { if (fs.hasOwnProperty(fk)) fsParts.push(fk.replace(/_/g, ' ') + ': ' + fs[fk]); }
        var fx = PAD + col * (NW + HGAP);
        addN('fin', 'final', 'Final State', trunc(fsParts.join(', '), 26), fx, PAD);
        gEdges.push({ f: 'a' + (rollout.steps.length - 1), t: 'fin', ty: 'solid' });

        // 4) Verifiers
        var vrs = rollout.verifier_results || [];
        for (var v = 0; v < vrs.length; v++) {
            var vr = vrs[v];
            var vKind = vr.passed ? 'vPass' : 'vFail';
            var vid = 'v' + v;
            var vy = PAD + NH + VGAP + v * (NH + STACK_GAP);
            addN(vid, vKind, (vr.passed ? '\u2713 ' : '\u2717 ') + trunc(vr.check, 19), trunc(vr.detail, 26), fx, vy);
            gEdges.push({ f: 'fin', t: vid, ty: 'dashed-red' });
        }

        /* ── SVG dimensions ── */
        var maxX = 0, maxY = 0;
        for (var ni = 0; ni < gNodes.length; ni++) {
            var nd = gNodes[ni];
            if (nd.x + nd.w > maxX) maxX = nd.x + nd.w;
            if (nd.y + nd.h > maxY) maxY = nd.y + nd.h;
        }
        var svgW = maxX + PAD;
        var svgH = maxY + PAD;

        /* ── Render SVG ── */
        var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + svgW + '" height="' + svgH +
            '" viewBox="0 0 ' + svgW + ' ' + svgH + '" style="font-family:Inter,system-ui,-apple-system,sans-serif;">';

        // Defs: arrowhead markers + drop-shadow
        svg += '<defs>';
        svg += '<marker id="sd-a-s" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0,0L8,3L0,6Z" fill="#64748b"/></marker>';
        svg += '<marker id="sd-a-b" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0,0L8,3L0,6Z" fill="#3b82f6"/></marker>';
        svg += '<marker id="sd-a-r" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0,0L8,3L0,6Z" fill="#f43f5e"/></marker>';
        svg += '<filter id="sd-sh" x="-4%" y="-8%" width="108%" height="120%"><feDropShadow dx="0" dy="1" stdDeviation="2" flood-opacity="0.06"/></filter>';
        svg += '</defs>';

        // ── Edges (drawn first, behind nodes) ──
        for (var ei = 0; ei < gEdges.length; ei++) {
            var ge = gEdges[ei];
            var fn = nMap[ge.f], tn = nMap[ge.t];
            if (!fn || !tn) continue;

            var marker = ge.ty === 'dashed-red' ? 'sd-a-r' : (ge.ty === 'dashed-blue' ? 'sd-a-b' : 'sd-a-s');
            var eCol = ge.ty === 'dashed-red' ? '#f43f5e' : (ge.ty === 'dashed-blue' ? '#3b82f6' : '#64748b');
            var eW = ge.ty === 'solid' ? 1.5 : 1.2;
            var dash = ge.ty === 'solid' ? '' : ' stroke-dasharray="6,3"';

            var horiz = Math.abs(fn.y - tn.y) < 5;
            var sameCol = Math.abs(fn.x - tn.x) < 5;
            var pth;

            if (horiz) {
                // Horizontal: right-center → left-center
                pth = 'M' + (fn.x + fn.w) + ',' + (fn.y + fn.h / 2) + ' L' + tn.x + ',' + (tn.y + tn.h / 2);
            } else if (sameCol) {
                // Vertical: bottom-center → top-center
                pth = 'M' + (fn.x + fn.w / 2) + ',' + (fn.y + fn.h) + ' L' + (tn.x + tn.w / 2) + ',' + tn.y;
            } else {
                // Diagonal: cubic bezier curve
                var sx = fn.x + fn.w / 2, sy = fn.y + fn.h;
                var ex = tn.x + tn.w / 2, ey = tn.y;
                var my = (sy + ey) / 2;
                pth = 'M' + sx + ',' + sy + ' C' + sx + ',' + my + ' ' + ex + ',' + my + ' ' + ex + ',' + ey;
            }

            svg += '<path d="' + pth + '" fill="none" stroke="' + eCol + '" stroke-width="' + eW + '"' + dash + ' marker-end="url(#' + marker + ')"/>';
        }

        // ── Nodes ──
        for (var ni2 = 0; ni2 < gNodes.length; ni2++) {
            var n = gNodes[ni2];
            var c = CLR[n.kind] || CLR.agent;

            svg += '<g filter="url(#sd-sh)">';
            svg += '<rect x="' + n.x + '" y="' + n.y + '" width="' + n.w + '" height="' + n.h + '" rx="' + BR + '" fill="' + c.bg + '" stroke="' + c.bdr + '" stroke-width="1.5"/>';

            if (n.detail) {
                svg += '<text x="' + (n.x + 10) + '" y="' + (n.y + 15) + '" font-size="11" font-weight="600" fill="' + c.tx + '">' + esvg(n.label) + '</text>';
                svg += '<text x="' + (n.x + 10) + '" y="' + (n.y + 28) + '" font-size="9" fill="#64748b">' + esvg(n.detail) + '</text>';
            } else {
                svg += '<text x="' + (n.x + 10) + '" y="' + (n.y + n.h / 2 + 4) + '" font-size="11" font-weight="600" fill="' + c.tx + '">' + esvg(n.label) + '</text>';
            }

            // Tooltip on hover
            svg += '<title>' + esvg(n.label + (n.detail ? ': ' + n.detail : '')) + '</title>';
            svg += '</g>';
        }

        svg += '</svg>';

        // ── Compose full HTML ──
        var out = '<div class="sd-container">';
        out += '<h3 class="sd-title">Rollout State Diagram</h3>';
        out += '<p class="sd-subtitle">' + esc(rollout.scenario_name || rollout.environment_name || '') +
            ' &middot; Policy: ' + esc(rollout.policy_name || '\u2014') +
            ' &middot; ' + rollout.total_steps + ' steps &middot; Reward: ' +
            (rollout.total_reward != null ? rollout.total_reward.toFixed(2) : '\u2014') + '</p>';
        out += '<div class="sd-scroll">' + svg + '</div>';

        // Legend: node types + edge types
        out += '<div class="sd-legend">';
        out += '<span class="sd-legend-item"><span class="sd-legend-dot" style="background:#93c5fd"></span> User</span>';
        out += '<span class="sd-legend-item"><span class="sd-legend-dot" style="background:#86efac"></span> Agent</span>';
        out += '<span class="sd-legend-item"><span class="sd-legend-dot" style="background:#fde68a"></span> Tool Call</span>';
        out += '<span class="sd-legend-item"><span class="sd-legend-dot" style="background:#cbd5e1"></span> Final State</span>';
        out += '<span class="sd-legend-item"><span class="sd-legend-dot" style="background:#e9d5ff"></span> Reward</span>';
        out += '<span class="sd-legend-item"><span class="sd-legend-line" style="color:#64748b"></span> Flow</span>';
        out += '<span class="sd-legend-item"><span class="sd-legend-line dashed" style="color:#3b82f6"></span> Tool</span>';
        out += '<span class="sd-legend-item"><span class="sd-legend-line dashed" style="color:#f43f5e"></span> Verify</span>';
        out += '</div></div>';

        container.innerHTML = out;
    }

    // ─── Canvas Charts ──────────────────────────────────────────

    /** Deterministic seed-based pseudo-random for consistent chart noise */
    function seededRandom(seed) {
        var s = seed;
        return function () {
            s = (s * 16807 + 0) % 2147483647;
            return (s - 1) / 2147483646;
        };
    }

    function renderProgressChart(run) {
        var canvas = document.getElementById('chart-progress');
        if (!canvas || !canvas.getContext) return;
        var ctx = canvas.getContext('2d');

        // HiDPI support
        var dpr = window.devicePixelRatio || 1;
        var rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);
        var w = rect.width, h = rect.height;

        ctx.clearRect(0, 0, w, h);

        var pad = { top: 20, right: 20, bottom: 35, left: 50 };
        var plotW = w - pad.left - pad.right;
        var plotH = h - pad.top - pad.bottom;

        var targetReward = run.avgReward || 0.63;
        var baselineReward = run.baselineReward || 0.22;
        var totalEpisodes = run.episodes || 320;

        // ── Use real per-episode data when available ──
        var perEp = (run._training_metrics && run._training_metrics.per_episode) ? run._training_metrics.per_episode : null;
        var rawPoints = [];  // actual reward values to plot
        var smoothed = [];   // smoothed version

        if (perEp && perEp.length > 0) {
            // Real data path: use actual per-episode rewards
            totalEpisodes = perEp.length;
            for (var i = 0; i < perEp.length; i++) {
                rawPoints.push(perEp[i].reward);
            }
            // Compute running average (window of 3) for smoothed line
            for (var i = 0; i < rawPoints.length; i++) {
                var sum = 0, cnt = 0;
                for (var j = Math.max(0, i - 1); j <= Math.min(rawPoints.length - 1, i + 1); j++) {
                    sum += rawPoints[j]; cnt++;
                }
                smoothed.push(sum / cnt);
            }
        } else {
            // Fallback: generate synthetic curve
            var numPoints = 40;
            var rng = seededRandom(42 + Math.round(targetReward * 1000));
            for (var i = 0; i <= numPoints; i++) {
                var t = i / numPoints;
                var base = baselineReward + (targetReward - baselineReward) * (1 - Math.exp(-4 * t));
                var noise = (rng() - 0.5) * 0.04 * (1 - t * 0.6);
                rawPoints.push(base + noise);
            }
            for (var i = 0; i < rawPoints.length; i++) {
                var sum = 0, cnt = 0;
                for (var j = Math.max(0, i - 2); j <= Math.min(rawPoints.length - 1, i + 2); j++) {
                    sum += rawPoints[j]; cnt++;
                }
                smoothed.push(sum / cnt);
            }
        }

        // ── Dynamic y-axis from actual data range ──
        var allVals = rawPoints.slice();
        allVals.push(baselineReward);
        var dataMin = allVals.reduce(function (a, b) { return Math.min(a, b); }, Infinity);
        var dataMax = allVals.reduce(function (a, b) { return Math.max(a, b); }, -Infinity);
        var dataRange = dataMax - dataMin;
        var margin = Math.max(dataRange * 0.15, 0.1);
        // Nice step size
        var rawRange = (dataMax + margin) - (dataMin - margin);
        var step = rawRange <= 1.0 ? 0.2 : rawRange <= 2.0 ? 0.5 : rawRange <= 5.0 ? 1.0 : 2.0;
        var yMin = Math.floor((dataMin - margin) / step) * step;
        var yMax = Math.ceil((dataMax + margin) / step) * step;
        if (yMin === yMax) yMax = yMin + step;
        var yRange = yMax - yMin;

        // Build y-axis ticks
        var yTicks = [];
        for (var v = yMin; v <= yMax + step * 0.01; v += step) {
            yTicks.push(Math.round(v * 100) / 100);
        }

        // Grid lines
        ctx.strokeStyle = '#f0f0f0';
        ctx.lineWidth = 1;
        yTicks.forEach(function (v) {
            var y = pad.top + plotH - ((v - yMin) / yRange) * plotH;
            ctx.beginPath();
            ctx.moveTo(pad.left, y);
            ctx.lineTo(pad.left + plotW, y);
            ctx.stroke();
        });

        // Zero line (if visible)
        if (yMin < 0 && yMax > 0) {
            var zeroY = pad.top + plotH - ((0 - yMin) / yRange) * plotH;
            ctx.strokeStyle = '#e5e7eb';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(pad.left, zeroY);
            ctx.lineTo(pad.left + plotW, zeroY);
            ctx.stroke();
        }

        // Axes
        ctx.strokeStyle = '#d1d5db';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(pad.left, pad.top);
        ctx.lineTo(pad.left, pad.top + plotH);
        ctx.lineTo(pad.left + plotW, pad.top + plotH);
        ctx.stroke();

        // Y-axis tick labels
        ctx.fillStyle = '#6b7280';
        ctx.font = '11px -apple-system, BlinkMacSystemFont, sans-serif';
        ctx.textAlign = 'right';
        yTicks.forEach(function (v) {
            var y = pad.top + plotH - ((v - yMin) / yRange) * plotH;
            ctx.fillText(v.toFixed(1), pad.left - 6, y + 4);
        });

        // X-axis tick labels
        ctx.textAlign = 'center';
        var xTickCount = 5;
        for (var i = 0; i <= xTickCount; i++) {
            var ep = Math.round((i / xTickCount) * totalEpisodes);
            var x = pad.left + (i / xTickCount) * plotW;
            ctx.fillText(ep, x, pad.top + plotH + 16);
        }

        // Axis labels
        ctx.fillStyle = '#9ca3af';
        ctx.font = '11px -apple-system, BlinkMacSystemFont, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Episodes', pad.left + plotW / 2, h - 4);
        ctx.save();
        ctx.translate(13, pad.top + plotH / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText('Mean Reward', 0, 0);
        ctx.restore();

        var numPts = rawPoints.length;

        // Gradient fill under smoothed curve (down to zero or yMin)
        var fillBase = (yMin < 0 && yMax > 0)
            ? pad.top + plotH - ((0 - yMin) / yRange) * plotH
            : pad.top + plotH;
        var grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + plotH);
        grad.addColorStop(0, 'rgba(192, 38, 211, 0.18)');
        grad.addColorStop(1, 'rgba(192, 38, 211, 0.02)');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.moveTo(pad.left, fillBase);
        smoothed.forEach(function (v, idx) {
            var x = pad.left + (idx / (numPts - 1)) * plotW;
            var y = pad.top + plotH - ((v - yMin) / yRange) * plotH;
            ctx.lineTo(x, y);
        });
        ctx.lineTo(pad.left + (numPts - 1) / (numPts - 1) * plotW, fillBase);
        ctx.closePath();
        ctx.fill();

        // Per-episode scatter dots (light, behind curve)
        if (perEp) {
            ctx.fillStyle = 'rgba(192, 38, 211, 0.25)';
            rawPoints.forEach(function (v, idx) {
                var x = pad.left + (idx / (numPts - 1)) * plotW;
                var y = pad.top + plotH - ((v - yMin) / yRange) * plotH;
                ctx.beginPath();
                ctx.arc(x, y, 3, 0, Math.PI * 2);
                ctx.fill();
            });
        }

        // Smoothed reward curve line
        ctx.strokeStyle = '#c026d3';
        ctx.lineWidth = 2.5;
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';
        ctx.beginPath();
        smoothed.forEach(function (v, idx) {
            var x = pad.left + (idx / (numPts - 1)) * plotW;
            var y = pad.top + plotH - ((v - yMin) / yRange) * plotH;
            if (idx === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();

        // Baseline dashed line (clamp to visible area)
        var clampedBase = Math.max(yMin, Math.min(yMax, baselineReward));
        var baseY = pad.top + plotH - ((clampedBase - yMin) / yRange) * plotH;
        ctx.strokeStyle = '#9ca3af';
        ctx.setLineDash([6, 4]);
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(pad.left, baseY);
        ctx.lineTo(pad.left + plotW, baseY);
        ctx.stroke();
        ctx.setLineDash([]);

        // Legend
        ctx.font = '11px -apple-system, BlinkMacSystemFont, sans-serif';
        var legendX = pad.left + plotW - 120;
        var legendY = pad.top + 8;
        // Trained
        ctx.strokeStyle = '#c026d3';
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(legendX, legendY);
        ctx.lineTo(legendX + 20, legendY);
        ctx.stroke();
        ctx.fillStyle = '#374151';
        ctx.textAlign = 'left';
        ctx.fillText('Trained', legendX + 25, legendY + 4);
        // Baseline
        ctx.strokeStyle = '#9ca3af';
        ctx.setLineDash([6, 4]);
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(legendX, legendY + 18);
        ctx.lineTo(legendX + 20, legendY + 18);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = '#9ca3af';
        ctx.fillText('Baseline', legendX + 25, legendY + 22);
    }

    function renderFailureChart(run) {
        var canvas = document.getElementById('chart-failures');
        if (!canvas || !canvas.getContext) return;
        var ctx = canvas.getContext('2d');

        // HiDPI support
        var dpr = window.devicePixelRatio || 1;
        var rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
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

        var pad = { top: 15, right: 50, bottom: 10, left: 115 };
        var plotW = w - pad.left - pad.right;
        var barH = Math.min(28, (h - pad.top - pad.bottom - (modes.length - 1) * 10) / modes.length);
        var gap = Math.min(12, (h - pad.top - pad.bottom - modes.length * barH) / (modes.length - 1));
        var totalH = modes.length * barH + (modes.length - 1) * gap;
        var startY = pad.top + (h - pad.top - pad.bottom - totalH) / 2;

        modes.forEach(function (m, i) {
            var y = startY + i * (barH + gap);
            var bw = (m.pct / 100) * plotW;
            var radius = 4;

            // Background track
            ctx.fillStyle = '#f3f4f6';
            _roundRect(ctx, pad.left, y, plotW, barH, radius);
            ctx.fill();

            // Filled bar with gradient
            if (bw > 0) {
                var barGrad = ctx.createLinearGradient(pad.left, y, pad.left + bw, y);
                barGrad.addColorStop(0, m.color);
                barGrad.addColorStop(1, _lightenColor(m.color, 0.2));
                ctx.fillStyle = barGrad;
                _roundRect(ctx, pad.left, y, Math.max(bw, radius * 2), barH, radius);
                ctx.fill();
            }

            // Label
            ctx.fillStyle = '#374151';
            ctx.font = '12px -apple-system, BlinkMacSystemFont, sans-serif';
            ctx.textAlign = 'right';
            ctx.textBaseline = 'middle';
            ctx.fillText(m.label, pad.left - 10, y + barH / 2);

            // Value
            ctx.fillStyle = '#6b7280';
            ctx.font = '12px -apple-system, BlinkMacSystemFont, sans-serif';
            ctx.textAlign = 'left';
            ctx.fillText(m.pct + '%', pad.left + bw + 8, y + barH / 2);
        });
        ctx.textBaseline = 'alphabetic';
    }

    /** Draw a rounded rectangle path */
    function _roundRect(ctx, x, y, w, h, r) {
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y);
        ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h - r);
        ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
        ctx.lineTo(x + r, y + h);
        ctx.quadraticCurveTo(x, y + h, x, y + h - r);
        ctx.lineTo(x, y + r);
        ctx.quadraticCurveTo(x, y, x + r, y);
        ctx.closePath();
    }

    /** Lighten a hex color by a factor (0-1) */
    function _lightenColor(hex, factor) {
        var r = parseInt(hex.slice(1, 3), 16);
        var g = parseInt(hex.slice(3, 5), 16);
        var b = parseInt(hex.slice(5, 7), 16);
        r = Math.min(255, Math.round(r + (255 - r) * factor));
        g = Math.min(255, Math.round(g + (255 - g) * factor));
        b = Math.min(255, Math.round(b + (255 - b) * factor));
        return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
    }

    // ─── Helpers ─────────────────────────────────────────────────
    function findEnv(id) {
        return ALL_ENVIRONMENTS.find(function (e) { return e.id === id; });
    }

    function getSelectedAlgorithm() {
        var checked = document.querySelector('input[name="tr-algorithm"]:checked');
        return checked ? checked.value : 'GRPO';
    }

    function getAgentModel(agentId) {
        var a = (CFG.agents || []).find(function (ag) { return ag.id === agentId; });
        return a ? a.base_model : agentId;
    }

    function esc(s) {
        if (s == null) return '';
        var d = document.createElement('div');
        d.textContent = String(s);
        return d.innerHTML;
    }

    function capFirst(s) {
        if (!s) return '';
        if (s === 'awaiting_human_eval') return 'Awaiting Human Eval';
        return s.charAt(0).toUpperCase() + s.slice(1);
    }

    function fmtISODate(iso) {
        if (!iso) return '\u2014';
        try {
            var d = new Date(iso);
            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        } catch (e) { return iso; }
    }

    function fmtTimestamp(val) {
        if (!val) return '\u2014';
        // Handle Unix timestamp (number or numeric string)
        var n = typeof val === 'number' ? val : parseFloat(val);
        if (!isNaN(n) && n > 1e9 && n < 2e10) {
            var d = new Date(n * 1000);
            return d.toISOString().replace('T', ' ').slice(0, 19);
        }
        // Handle ISO string
        if (typeof val === 'string' && val.indexOf('T') > -1) {
            return val.replace('T', ' ').slice(0, 19);
        }
        return String(val);
    }

    function metricCard(label, value, isPositive) {
        return '<div class="metric-card"><div class="mc-label">' + esc(label) + '</div>' +
            '<div class="mc-value' + (isPositive ? ' positive' : '') + '">' + esc(value) + '</div></div>';
    }

    function infoRow(label, value) {
        return '<div class="info-row"><span class="ir-label">' + esc(label) + '</span><span class="ir-value">' + esc(value) + '</span></div>';
    }

    function perfRow(label, oldVal, newVal, delta) {
        var cls = '';
        if (delta && String(delta).indexOf('-') === 0) cls = 'down';
        else if (delta && String(delta).indexOf('+') === 0) cls = 'up';
        return '<div class="perf-row"><span class="perf-label">' + esc(label) + '</span>' +
            '<div class="perf-values"><span class="perf-old">' + esc(oldVal) + '</span> \u2192 <span class="perf-new">' + esc(newVal) + '</span>' +
            (delta ? ' <span class="perf-delta ' + cls + '">' + esc(delta) + '</span>' : '') +
            '</div></div>';
    }

    function showToast(msg, type) {
        if (window.showToast) {
            window.showToast(msg, type);
        } else {
            console.log('[' + (type || 'info') + '] ' + msg);
        }
    }

    // ─── Tab Switching ──────────────────────────────────────────
    function initTabs() {
        var tabs = document.querySelectorAll('#training-tabs .training-tab');
        tabs.forEach(function (tab) {
            tab.addEventListener('click', function () {
                tabs.forEach(function (t) { t.classList.remove('active'); });
                tab.classList.add('active');
                document.querySelectorAll('.training-tab-content').forEach(function (c) { c.classList.remove('active'); });
                var target = document.getElementById('tab-' + tab.getAttribute('data-tab'));
                if (target) target.classList.add('active');
                if (tab.getAttribute('data-tab') === 'rollouts') {
                    loadRolloutList();
                }
            });
        });
    }

    // ─── Rollout List ────────────────────────────────────────────
    var _rolloutCache = [];
    var _rolloutEnvs = [];

    function loadRolloutList(envFilter) {
        var apiBase = window.API_BASE || '';
        var url = apiBase + '/api/rollouts-all?limit=100';
        if (envFilter) url += '&environment_name=' + encodeURIComponent(envFilter);
        fetch(url)
            .then(function (res) { return res.json(); })
            .then(function (data) {
                _rolloutCache = data.rollouts || [];
                _rolloutEnvs = data.environments || [];
                renderRolloutEnvFilter();
                renderRolloutList();
                var footer = document.getElementById('rollout-list-footer');
                if (footer) {
                    footer.style.display = 'block';
                    footer.textContent = 'Showing ' + _rolloutCache.length + ' of ' + data.total + ' rollouts' +
                        (_rolloutCache.length < data.total ? ' \u00b7 Sampled for inspection' : '');
                }
            })
            .catch(function (err) {
                console.warn('Failed to load rollouts:', err);
                document.getElementById('rollout-list-body').innerHTML =
                    '<div style="padding:2rem;text-align:center;color:var(--text-secondary)">No rollouts yet. Run a training session first.</div>';
            });
    }

    function renderRolloutEnvFilter() {
        var sel = document.getElementById('rollout-env-filter');
        if (!sel) return;
        var current = sel.value;
        sel.innerHTML = '<option value="">All Environments</option>';
        _rolloutEnvs.forEach(function (env) {
            sel.innerHTML += '<option value="' + esc(env) + '">' + humanizeName(env) + '</option>';
        });
        sel.value = current;
    }

    function renderRolloutList() {
        var body = document.getElementById('rollout-list-body');
        if (!_rolloutCache.length) {
            body.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--text-secondary)">No rollouts found. Run a training session to generate rollouts.</div>';
            return;
        }

        var envFilter = (document.getElementById('rollout-env-filter') || {}).value;
        var subtitle = document.getElementById('rollout-list-subtitle');
        if (subtitle) {
            var envLabel = envFilter ? humanizeName(envFilter) : 'All';
            subtitle.innerHTML = 'Environment: <span id="rollout-env-label">' + esc(envLabel) + '</span>';
        }

        var html = '<table class="rollout-table"><thead><tr>';
        html += '<th>Episode ID</th><th>Issue Key</th><th>Policy</th><th>Final State</th><th>Tool Calls</th><th>Reward</th><th>Duration</th>';
        html += '</tr></thead><tbody>';

        _rolloutCache.forEach(function (r) {
            var epId = 'ep_' + String(r.episode_number).padStart(6, '0');
            var issueKey = r.issue_key || '—';
            var policyLabel = r.checkpoint_label === 'base' ? 'Baseline' : 'Trained';
            var policyClass = r.checkpoint_label === 'base' ? 'baseline' : 'trained';
            var fsLabel = r.final_state || 'N/A';
            var fsClass = fsLabel.toLowerCase().replace(/[\s-]/g, '');
            if (fsClass === 'done' || fsClass === 'resolved' || fsClass === 'closed') fsClass = 'resolved';
            else if (fsClass === 'open' || fsClass === 'inprogress') fsClass = 'open';
            var toolCalls = r.tool_calls || 0;
            var reward = (r.total_reward != null) ? r.total_reward.toFixed(2) : '0.00';
            var duration = r.duration_s ? (r.duration_s + 's') : '—';

            html += '<tr class="rollout-row" data-rollout-id="' + esc(r.id) + '" data-env="' + esc(r.environment_name) + '">';
            html += '<td class="rl-episode">' + esc(epId) + '</td>';
            html += '<td class="rl-issue">' + esc(issueKey) + '</td>';
            html += '<td><span class="policy-badge ' + policyClass + '">' + policyLabel + '</span></td>';
            html += '<td><span class="final-state-badge ' + fsClass + '">' + esc(fsLabel) + '</span></td>';
            html += '<td>' + toolCalls + '</td>';
            html += '<td>' + reward + '</td>';
            html += '<td>' + esc(duration) + '</td>';
            html += '</tr>';
        });

        html += '</tbody></table>';
        body.innerHTML = html;

        // Click handler: open rollout detail
        body.querySelectorAll('.rollout-row').forEach(function (row) {
            row.addEventListener('click', function () {
                var rid = row.getAttribute('data-rollout-id');
                var env = row.getAttribute('data-env');
                showRolloutDetail(env, rid);
            });
        });
    }

    // ─── Rollout Detail ──────────────────────────────────────────
    function showRolloutDetail(envName, rolloutId) {
        var apiBase = window.API_BASE || '';
        fetch(apiBase + '/api/rollouts/' + encodeURIComponent(envName) + '/' + encodeURIComponent(rolloutId))
            .then(function (res) {
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function (rollout) {
                _currentRolloutDetail = rollout;
                renderRolloutDetailHeader(rollout);
                renderRolloutDetailContent(rollout, 'messages');
                renderRolloutTrajectory(rollout);
                showView('rollout-detail');
            })
            .catch(function (err) {
                showToast('Failed to load rollout: ' + err.message, 'error');
            });
    }

    var _currentRolloutDetail = null;

    function renderRolloutDetailHeader(r) {
        var hdr = document.getElementById('rollout-detail-header');
        var epId = 'ep_' + String(r.episode_number || 0).padStart(6, '0');
        var fs = r.final_environment_state || {};
        var issueKey = fs.issue_key || r.environment_name || '';
        var policyLabel = r.checkpoint_label === 'base' ? 'Baseline' : 'Trained';
        hdr.innerHTML =
            '<h2><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg> Episode Detail</h2>' +
            '<div class="rollout-detail-meta">' +
            '<span><span class="rdm-label">Episode:</span><span class="rdm-value">' + esc(epId) + '</span></span>' +
            '<span>\u00b7</span>' +
            '<span><span class="rdm-label">Issue:</span><span class="rdm-value">' + esc(issueKey) + '</span></span>' +
            '<span>\u00b7</span>' +
            '<span><span class="rdm-label">Policy:</span><span class="rdm-value">' + esc(policyLabel) + '</span></span>' +
            '</div>';
    }

    function renderRolloutDetailContent(r, mode) {
        var container = document.getElementById('rollout-detail-content');
        if (mode === 'messages') {
            // Build messages JSON view
            var messages = buildMessagesFromSteps(r);
            container.innerHTML = '<pre>' + syntaxHighlight(JSON.stringify(messages, null, 2)) + '</pre>';
        } else if (mode === 'toolcalls') {
            var toolCalls = extractToolCalls(r);
            container.innerHTML = '<pre>' + syntaxHighlight(JSON.stringify(toolCalls, null, 2)) + '</pre>';
        } else if (mode === 'json') {
            container.innerHTML = '<pre>' + syntaxHighlight(JSON.stringify(r, null, 2)) + '</pre>';
        }
    }

    function buildMessagesFromSteps(r) {
        var messages = [];
        var steps = r.steps || [];
        // System message
        messages.push({ role: 'system', content: 'You are an LLM/Agent to resolve JIRA tickets...' });
        // User message
        var fs = r.final_environment_state || {};
        messages.push({ role: 'user', content: 'Resolve ticket ' + (fs.issue_key || r.environment_name || '') });

        steps.forEach(function (step) {
            var events = step.timeline_events || [];
            events.forEach(function (evt) {
                if (evt.event_type === 'TOOL_CALL' && evt.tool_name) {
                    messages.push({
                        role: 'assistant',
                        content: '',
                        tool_calls: [{
                            name: evt.tool_name,
                            arguments: evt.tool_args || {}
                        }]
                    });
                } else if (evt.event_type === 'TOOL_RESULT') {
                    messages.push({
                        role: 'tool',
                        name: evt.tool_name || 'get_transitions',
                        content: evt.content || ''
                    });
                }
            });
        });
        return messages;
    }

    function extractToolCalls(r) {
        var calls = [];
        (r.steps || []).forEach(function (step) {
            (step.timeline_events || []).forEach(function (evt) {
                if (evt.event_type === 'TOOL_CALL' && evt.tool_name) {
                    calls.push({
                        step: step.step,
                        tool: evt.tool_name,
                        args: evt.tool_args || {},
                        timestamp_ms: evt.timestamp_ms
                    });
                }
            });
        });
        return calls;
    }

    function syntaxHighlight(json) {
        return json
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"([^"]+)":/g, '<span style="color:#1e40af">"$1"</span>:')
            .replace(/: "([^"]*)"/g, ': <span style="color:#047857">"$1"</span>')
            .replace(/: (\d+\.?\d*)/g, ': <span style="color:#b45309">$1</span>')
            .replace(/: (true|false|null)/g, ': <span style="color:#9333ea">$1</span>');
    }

    function renderRolloutTrajectory(r) {
        var container = document.getElementById('rollout-detail-trajectory');
        var html = '';
        // Legend
        html += '<div class="traj-legend">' +
            '<span class="traj-legend-item"><span class="traj-legend-dot agent"></span> User/Agent</span>' +
            '<span class="traj-legend-item"><span class="traj-legend-dot tool"></span> Tool Call</span>' +
            '<span class="traj-legend-item"><span class="traj-legend-dot verifier"></span> Verifier</span>' +
            '<span class="traj-legend-item"><span class="traj-legend-dot reward"></span> Reward</span>' +
            '</div>';

        html += '<div class="traj-flow">';

        // System node
        html += buildTrajNode('system', 'SYS', 'System', 'Agent policy + tool schema');

        // User request
        var fs = r.final_environment_state || {};
        html += buildTrajNode('agent', 'USR', 'User Request', 'Scenario prompt: Resolve ' + esc(fs.issue_key || ''));

        // Steps
        (r.steps || []).forEach(function (step) {
            (step.timeline_events || []).forEach(function (evt) {
                if (evt.event_type === 'TOOL_CALL' && evt.tool_name) {
                    var argsStr = evt.tool_args ? Object.keys(evt.tool_args).map(function (k) { return k + '=' + evt.tool_args[k]; }).join(', ') : '';
                    html += buildTrajNode('tool', 'TC', evt.tool_name, argsStr ? '<span class="traj-node-args">' + esc(argsStr) + '</span>' : '');
                } else if (evt.event_type === 'TOOL_RESULT') {
                    html += buildTrajNode('result', 'TR', 'Result', esc(evt.content || ''));
                }
            });
        });

        // Verifier results
        (r.verifier_results || []).forEach(function (v) {
            var icon = v.passed ? '\u2705' : '\u274c';
            html += buildTrajNode('verifier', icon, v.check, esc(v.detail || ''));
        });

        html += '</div>';
        container.innerHTML = html;
    }

    function buildTrajNode(type, iconText, title, detail) {
        return '<div class="traj-node">' +
            '<div class="traj-node-icon ' + type + '">' + iconText + '</div>' +
            '<div class="traj-node-body">' +
            '<div class="traj-node-title">' + title + '</div>' +
            (detail ? '<div class="traj-node-detail">' + detail + '</div>' : '') +
            '</div></div>';
    }

    function initRolloutDetailTabs() {
        var tabs = document.querySelectorAll('#rollout-detail-tabs .rollout-dtab');
        tabs.forEach(function (tab) {
            tab.addEventListener('click', function () {
                tabs.forEach(function (t) { t.classList.remove('active'); });
                tab.classList.add('active');
                if (_currentRolloutDetail) {
                    renderRolloutDetailContent(_currentRolloutDetail, tab.getAttribute('data-dtab'));
                }
            });
        });
    }

    // ─── Init ───────────────────────────────────────────────────
    function refreshAndRenderList() {
        fetchLiveJobs().then(function () { renderTrainingList(); });
    }

    function init() {
        // Load environments and agents/algorithms in parallel; agents/algorithms
        // tries the backend API first, falls back to hardcoded sample data
        Promise.all([loadEnvironments(), loadScenarios(), loadVerifiers(), fetchAgentsAndAlgorithms()]).then(function () {
            populateSystems();
            populateCategories();
            populateEnvironments();
            populateAlgorithms();
            populateVerifiers();
            filterScenarios();
            filterAgents();
            refreshAndRenderList();

            // Handle ?env=, ?preselect_env=, ?run=, and ?agent= params
            var urlParams = new URLSearchParams(window.location.search);
            var directEnv = urlParams.get('env');
            var deferredEnv = urlParams.get('preselect_env');
            var directRunId = urlParams.get('run');
            var directAgent = urlParams.get('agent');

            if (directRunId) {
                // Direct navigation to a specific run's full report
                // (e.g. /training-console?run=abc123 — from env card "View Full Report")
                showRunDetails(directRunId);
                history.replaceState(null, '', window.location.pathname);
            } else if (directAgent) {
                // Direct navigation from agent console (e.g. /training-console?agent=agent_qwen17)
                showView('new');
                _applyAgentPreselection(directAgent);
                history.replaceState(null, '', window.location.pathname);
            } else if (directEnv) {
                // Direct navigation (e.g. /training-console?env=X) — auto-open new form with env locked
                showView('new');
                _applyEnvPreselection(directEnv, true);
                history.replaceState(null, '', window.location.pathname);
            } else if (deferredEnv) {
                // Embedded popup — store env for later, stay on list view
                _preselectedEnv = deferredEnv;
                // Set persistent category filter for the training runs list
                var deferredEnvObj = findEnv(deferredEnv);
                if (deferredEnvObj) {
                    _envFilterCategory = deferredEnvObj.category || null;
                }
                // Re-render list with filter applied
                renderTrainingList();
                // Clean the preselect_env param from URL, keep embedded
                var cleanSearch = window.location.search
                    .replace(/[?&]preselect_env=[^&]*/g, '')
                    .replace(/^\?&/, '?')
                    .replace(/^\?$/, '');
                history.replaceState(null, '', window.location.pathname + cleanSearch);
            }
        });

        // Navigation
        document.getElementById('btn-new-run').addEventListener('click', function () {
            showView('new');
            if (_preselectedEnv) {
                _applyEnvPreselection(_preselectedEnv);
                _preselectedEnv = null;
            }
        });
        document.getElementById('btn-back-list').addEventListener('click', function () { showView('list'); refreshAndRenderList(); });
        document.getElementById('btn-back-list-2').addEventListener('click', function () { showView('list'); refreshAndRenderList(); });
        document.getElementById('btn-cancel-new').addEventListener('click', function () { showView('list'); });

        // Back from rollout detail
        var btnBackRollouts = document.getElementById('btn-back-rollouts');
        if (btnBackRollouts) {
            btnBackRollouts.addEventListener('click', function () {
                showView('list');
                // Activate rollouts tab
                var rolloutTab = document.querySelector('#training-tabs .training-tab[data-tab="rollouts"]');
                if (rolloutTab) rolloutTab.click();
            });
        }

        // System filter (Environment dropdown now shows systems)
        var systemSel = document.getElementById('tr-env-system');
        if (systemSel) systemSel.addEventListener('change', onSystemChange);

        // Hidden category filter (backward compat)
        document.getElementById('tr-env-category').addEventListener('change', onCategoryChange);

        // Environment change cascades (Scenario dropdown selects RL environment)
        document.getElementById('tr-env').addEventListener('change', onEnvironmentChange);

        // Scenario change — show actions only after scenario is selected
        var scenarioSel = document.getElementById('tr-scenario');
        if (scenarioSel) scenarioSel.addEventListener('change', onScenarioChange);

        // Verifier
        initVerifierToggle();
        initVerifierType();
        initConditionRows();
        initExistingVerifierChange();
        initExistingConditionRows();

        // LoRA
        initLoraToggle();

        // Submit
        document.getElementById('btn-start-training').addEventListener('click', submitNewTraining);

        // Tabs (Training Runs / Rollouts)
        initTabs();

        // Rollout detail tabs
        initRolloutDetailTabs();

        // Rollout environment filter
        var rolloutEnvFilter = document.getElementById('rollout-env-filter');
        if (rolloutEnvFilter) {
            rolloutEnvFilter.addEventListener('change', function () {
                loadRolloutList(rolloutEnvFilter.value || undefined);
            });
        }

    }

    // ─── Scenario Library UI (removed — managed via API only) ─────
    function initScenarioLibrary() { /* no-op */ }
    window._renderCustomScenarioList = function () { /* no-op */ };
    function renderCustomScenarioList() { /* no-op */ }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
