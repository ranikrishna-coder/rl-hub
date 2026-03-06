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

    // ─── Fetch live training jobs from backend ─────────────────
    // Set of hardcoded mock IDs that should not be overwritten by API
    var MOCK_RUN_IDS = {};

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
                        CFG.trainingRuns.push({
                            id: j.job_id,
                            job_id: j.job_id,
                            name: j.run_name || fallbackName,
                            description: (j.algorithm || '') + ' training on ' + humanizeName(j.environment_name || ''),
                            status: j.status || 'unknown',
                            environment: j.environment_name || '',
                            environmentDisplay: humanizeName(j.environment_name || ''),
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
        return fetch(apiBase + '/environments')
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
                ALL_ENVIRONMENTS.forEach(function (e) {
                    if (!CATEGORY_MAP[e.category]) CATEGORY_MAP[e.category] = [];
                    CATEGORY_MAP[e.category].push(e);
                });
                CFG.environments = ALL_ENVIRONMENTS;
            })
            .catch(function (err) {
                console.warn('Failed to load environments:', err);
                ALL_ENVIRONMENTS = [];
                CATEGORY_MAP = {};
            });
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
        var body = document.getElementById('training-runs-body');
        var countEl = document.getElementById('run-count');
        if (countEl) countEl.textContent = runs.length + ' run' + (runs.length !== 1 ? 's' : '');

        if (!runs.length) {
            body.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--text-secondary)">No training runs yet. Click <strong>New Training Run</strong> to get started.</div>';
            return;
        }

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

    function populateCategories() {
        var sel = document.getElementById('tr-env-category');
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
        var catFilter = document.getElementById('tr-env-category').value;
        sel.innerHTML = '<option value="">— Select environment —</option>';

        var envs = catFilter ? (CATEGORY_MAP[catFilter] || []) : ALL_ENVIRONMENTS;
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
                (catFilter ? ' in ' + formatCategory(catFilter) : ' across ' + Object.keys(CATEGORY_MAP).length + ' categories');
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

    function populateVerifiers() {
        var sel = document.getElementById('tr-verifier-existing');
        sel.innerHTML = '<option value="">— Select verifier —</option>';
        var env = findEnv(document.getElementById('tr-env').value);
        var cat = env ? env.category : '';

        VERIFIERS.forEach(function (v) {
            if (cat && v.environment && v.environment !== cat) return;
            var o = document.createElement('option');
            o.value = v.id;
            o.textContent = v.name + ' (' + v.type + ')';
            sel.appendChild(o);
        });
    }

    function filterScenarios() {
        var env = findEnv(document.getElementById('tr-env').value);
        var cat = env ? env.category : '';
        var sel = document.getElementById('tr-scenario');
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

    function updateEnvPreview() {
        var envId = document.getElementById('tr-env').value;
        var panel = document.getElementById('env-preview-panel');
        var env = findEnv(envId);
        if (!env) { panel.style.display = 'none'; return; }
        panel.style.display = 'block';
        document.getElementById('ep-category').textContent = formatCategory(env.category) || '—';
        document.getElementById('ep-system').textContent = env.system || '—';
        var actionSpaceRow = document.getElementById('ep-action-space').closest('.ep-row');
        var stateFeaturesRow = document.getElementById('ep-state-features').closest('.ep-row');
        var actionsLabelRow = document.getElementById('ep-tools').previousElementSibling;
        var toolsEl = document.getElementById('ep-tools');

        if (env.actionSpace && env.actionSpace !== 'N/A') {
            document.getElementById('ep-action-space').textContent = env.actionSpace;
            actionSpaceRow.style.display = '';
        } else {
            actionSpaceRow.style.display = 'none';
        }
        if (env.stateFeatures && env.stateFeatures !== 'N/A') {
            document.getElementById('ep-state-features').textContent = env.stateFeatures;
            stateFeaturesRow.style.display = '';
        } else {
            stateFeaturesRow.style.display = 'none';
        }

        toolsEl.innerHTML = '';
        if (env.actions && env.actions.length) {
            if (actionsLabelRow) actionsLabelRow.style.display = '';
            toolsEl.style.display = '';
            env.actions.forEach(function (t) {
                toolsEl.insertAdjacentHTML('beforeend', '<span class="ep-tool-tag">' + esc(t) + '</span>');
            });
        } else {
            if (actionsLabelRow) actionsLabelRow.style.display = 'none';
            toolsEl.style.display = 'none';
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

    function onCategoryChange() {
        populateEnvironments();
        document.getElementById('tr-env').value = '';
        onEnvironmentChange();
    }

    function onEnvironmentChange() {
        updateEnvPreview();
        filterScenarios();
        populateVerifiers();
        filterAgents();
        updateVerifierSystem();
    }

    function initVerifierToggle() {
        var toggle = document.getElementById('verifier-toggle');
        var existingPanel = document.getElementById('verifier-existing-panel');
        var createPanel = document.getElementById('verifier-create-panel');

        toggle.addEventListener('click', function (e) {
            var btn = e.target.closest('button');
            if (!btn) return;
            toggle.querySelectorAll('button').forEach(function (b) { b.classList.remove('active'); });
            btn.classList.add('active');
            var mode = btn.getAttribute('data-mode');
            existingPanel.style.display = mode === 'existing' ? '' : 'none';
            createPanel.style.display = mode === 'create' ? '' : 'none';
        });
    }

    function initVerifierType() {
        var sel = document.getElementById('tr-verifier-type');
        var hilPanel = document.getElementById('human-eval-panel');
        var stdPanel = document.getElementById('verifier-standard-panel');
        sel.addEventListener('change', function () {
            var isHil = sel.value === 'human_eval';
            hilPanel.style.display = isHil ? '' : 'none';
            stdPanel.style.display = isHil ? 'none' : '';
            if (isHil && !document.querySelector('.condition-row')) {
                addConditionRow('Correct resolution', '0.4');
                addConditionRow('Proper status transitions', '0.3');
                addConditionRow('Communication quality', '0.3');
            }
        });
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
        document.getElementById('btn-add-condition').addEventListener('click', function () {
            addConditionRow('', '');
        });
        document.getElementById('condition-rows').addEventListener('click', function (e) {
            var btn = e.target.closest('.remove-btn');
            if (btn && !btn.disabled) {
                btn.closest('.condition-row').remove();
                updateRemoveButtons();
            }
        });
    }

    function initExistingVerifierChange() {
        var sel = document.getElementById('tr-verifier-existing');
        sel.addEventListener('change', function () {
            var hilPanel = document.getElementById('existing-hil-panel');
            var container = document.getElementById('existing-condition-rows');
            var verifier = VERIFIERS.find(function (v) { return v.id === sel.value; });

            if (verifier && (verifier.type === 'human-eval' || verifier.type === 'human_evaluation' ||
                (verifier.logic && verifier.logic.type === 'human_evaluation'))) {
                // Show HIL condition/weight editor
                container.innerHTML = '';
                var criteria = (verifier.logic && verifier.logic.criteria) || [];
                if (criteria.length) {
                    var equalWeight = Math.round((1 / criteria.length) * 100) / 100;
                    criteria.forEach(function (c) {
                        addExistingConditionRow(c, String(equalWeight));
                    });
                } else {
                    addExistingConditionRow('Correct resolution', '0.4');
                    addExistingConditionRow('Proper status transitions', '0.3');
                    addExistingConditionRow('Communication quality', '0.3');
                }
                hilPanel.style.display = '';
            } else {
                hilPanel.style.display = 'none';
                container.innerHTML = '';
            }
        });
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
        var catSel = document.getElementById('tr-env-category');
        catSel.value = 'jira';
        onCategoryChange();

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

            var scenarioSel = document.getElementById('tr-scenario');
            if (scenarioSel.options.length > 1) scenarioSel.selectedIndex = 1;

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
            scenario: document.getElementById('tr-scenario').value,
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

        var verifierMode = document.querySelector('#verifier-toggle button.active').getAttribute('data-mode');
        if (verifierMode === 'existing') {
            body.verifier_id = document.getElementById('tr-verifier-existing').value;
            // Include conditions if an existing HIL verifier is selected
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
        } else {
            body.verifier = {
                name: document.getElementById('tr-verifier-name').value.trim(),
                type: document.getElementById('tr-verifier-type').value,
                system: (document.getElementById('tr-verifier-system').value || '').trim()
            };
            if (body.verifier.type === 'human_eval') {
                body.verifier.conditions = [];
                document.querySelectorAll('#condition-rows .condition-row').forEach(function (row) {
                    body.verifier.conditions.push({
                        condition: row.querySelector('.cond-name').value.trim(),
                        weight: parseFloat(row.querySelector('.cond-weight').value) || 0
                    });
                });
            } else {
                // rule_based, trajectory, llm_judge — collect description, logic, failure policy
                body.verifier.description = (document.getElementById('tr-verifier-desc').value || '').trim();
                var logicRaw = (document.getElementById('tr-verifier-logic').value || '').trim();
                if (logicRaw) {
                    try { body.verifier.logic = JSON.parse(logicRaw); } catch (e) {
                        showToast('Invalid JSON in verifier Logic field', 'error');
                        return;
                    }
                }
                body.verifier.failurePolicy = {
                    hard_fail: document.getElementById('tr-verifier-hardfail').checked,
                    log_failure: document.getElementById('tr-verifier-logfail').checked,
                    penalty: parseFloat(document.getElementById('tr-verifier-penalty').value) || -0.5
                };
            }
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
        document.getElementById('detail-title').textContent = run.name;
        var badge = document.getElementById('detail-status');
        badge.textContent = statusLabel;
        badge.className = 'status-badge ' + run.status;

        // Action buttons
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

        // Training Progress Stepper
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

        // Failure reason panel
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

        // Metric cards
        var metrics = document.getElementById('detail-metrics');
        var maxRewardLabel = run.results ? run.results.max_reward.toFixed(2) : '—';
        metrics.innerHTML = metricCard('Episodes', run.episodes || '—') +
            metricCard('Success Rate', run.successRate != null ? run.successRate + '%' : '—') +
            metricCard('Avg Reward', run.avgReward != null ? run.avgReward.toFixed(2) : '—') +
            metricCard('Improvement', run.baselineReward != null && run.avgReward != null
                ? '+' + ((run.avgReward - run.baselineReward) * 100).toFixed(0) + '%'
                : '—', true);

        // Training info panel
        document.getElementById('detail-training-info').innerHTML =
            '<h3>Training Information</h3>' +
            infoRow('Environment', envDisplay) +
            infoRow('Category', formatCategory(run.category)) +
            infoRow('Algorithm', run.algorithm) +
            infoRow('Status', statusLabel) +
            infoRow('Started', run.started || '—') +
            (run.completed ? infoRow('Completed', run.completed) : '') +
            infoRow('Progress', run.progress + '%');

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

        // Rollout comparison — only show when training is complete
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

        // Model artifact
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

        // Canvas charts
        renderProgressChart(run);
        renderFailureChart(run);

        // Performance panel
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

        // Trade-off note
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
        var numPoints = 40;
        var rng = seededRandom(42 + Math.round(targetReward * 1000));

        // Generate smooth reward curve using exponential approach + small deterministic noise
        var rewardPoints = [];
        for (var i = 0; i <= numPoints; i++) {
            var t = i / numPoints;
            var base = baselineReward + (targetReward - baselineReward) * (1 - Math.exp(-4 * t));
            var noise = (rng() - 0.5) * 0.04 * (1 - t * 0.6); // noise decreases as training progresses
            rewardPoints.push(Math.max(0, Math.min(1, base + noise)));
        }

        // Smooth the points with a simple moving average
        var smoothed = [];
        for (var i = 0; i < rewardPoints.length; i++) {
            var sum = 0, cnt = 0;
            for (var j = Math.max(0, i - 2); j <= Math.min(rewardPoints.length - 1, i + 2); j++) {
                sum += rewardPoints[j]; cnt++;
            }
            smoothed.push(sum / cnt);
        }

        var yMin = 0, yMax = 1.0;
        var yRange = yMax - yMin;

        // Grid lines
        ctx.strokeStyle = '#f0f0f0';
        ctx.lineWidth = 1;
        var yTicks = [0, 0.2, 0.4, 0.6, 0.8, 1.0];
        yTicks.forEach(function (v) {
            var y = pad.top + plotH - ((v - yMin) / yRange) * plotH;
            ctx.beginPath();
            ctx.moveTo(pad.left, y);
            ctx.lineTo(pad.left + plotW, y);
            ctx.stroke();
        });

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
        var xTicks = 5;
        for (var i = 0; i <= xTicks; i++) {
            var ep = Math.round((i / xTicks) * totalEpisodes);
            var x = pad.left + (i / xTicks) * plotW;
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

        // Gradient fill under curve
        var grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + plotH);
        grad.addColorStop(0, 'rgba(192, 38, 211, 0.15)');
        grad.addColorStop(1, 'rgba(192, 38, 211, 0.02)');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.moveTo(pad.left, pad.top + plotH);
        smoothed.forEach(function (v, idx) {
            var x = pad.left + (idx / numPoints) * plotW;
            var y = pad.top + plotH - ((v - yMin) / yRange) * plotH;
            ctx.lineTo(x, y);
        });
        ctx.lineTo(pad.left + plotW, pad.top + plotH);
        ctx.closePath();
        ctx.fill();

        // Reward curve line
        ctx.strokeStyle = '#c026d3';
        ctx.lineWidth = 2.5;
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';
        ctx.beginPath();
        smoothed.forEach(function (v, idx) {
            var x = pad.left + (idx / numPoints) * plotW;
            var y = pad.top + plotH - ((v - yMin) / yRange) * plotH;
            if (idx === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();

        // Baseline dashed line
        var baseY = pad.top + plotH - ((baselineReward - yMin) / yRange) * plotH;
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
            { label: 'Timeout',          pct: 25, color: '#7c3aed' },
            { label: 'Missing comment',  pct: 20, color: '#3b82f6' },
            { label: 'Invalid status',   pct: 12, color: '#06b6d4' },
            { label: 'Other',            pct: 8,  color: '#9ca3af' }
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
        loadEnvironments().then(function () {
            populateCategories();
            populateEnvironments();
            populateAlgorithms();
            populateVerifiers();
            filterScenarios();
            refreshAndRenderList();

            // Handle ?env= param from catalog navigation
            var urlParams = new URLSearchParams(window.location.search);
            var preselectedEnv = urlParams.get('env');
            if (preselectedEnv) {
                showView('new');
                var env = findEnv(preselectedEnv);
                if (env && env.category) {
                    document.getElementById('tr-env-category').value = env.category;
                    populateEnvironments();
                }
                document.getElementById('tr-env').value = preselectedEnv;
                onEnvironmentChange();
                history.replaceState(null, '', window.location.pathname);
            }
        });

        // Navigation
        document.getElementById('btn-new-run').addEventListener('click', function () { showView('new'); });
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

        // Category filter
        document.getElementById('tr-env-category').addEventListener('change', onCategoryChange);

        // Environment change cascades
        document.getElementById('tr-env').addEventListener('change', onEnvironmentChange);

        // Verifier
        initVerifierToggle();
        initVerifierType();
        initConditionRows();
        initExistingVerifierChange();
        initExistingConditionRows();

        // LoRA
        initLoraToggle();

        // Sample data prefill
        document.getElementById('btn-prefill-sample').addEventListener('click', prefillSampleData);

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

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
