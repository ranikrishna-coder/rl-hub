/**
 * Rollout Comparison — Shared renderer for side-by-side pre vs post training rollout view.
 * Loaded by both index.html (catalog) and simulation-console.html.
 */
(function() {
    'use strict';

    function _esc(s) {
        if (typeof s !== 'string') s = String(s == null ? '' : s);
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function _fmtTime(ms) {
        if (typeof ms !== 'number' || isNaN(ms)) return '[ — ]';
        return '[ ' + (ms / 1000).toFixed(3) + 's ]';
    }

    function _renderColumn(rollout, title, cssClass) {
        if (!rollout) {
            return '<div class="rc-column ' + cssClass + '">' +
                '<h4 class="rc-col-title">' + _esc(title) + '</h4>' +
                '<p class="rc-empty">No rollout data available.</p></div>';
        }

        var html = '<div class="rc-column ' + cssClass + '">';
        html += '<h4 class="rc-col-title">' + _esc(title) + '</h4>';

        // Policy info
        html += '<div class="rc-policy-info">';
        html += '<span>Policy: <strong>' + _esc(rollout.policy_name || rollout.source || 'unknown') + '</strong></span>';
        html += '<span>Checkpoint: <code>' + _esc(rollout.checkpoint_label || '—') + '</code></span>';
        html += '</div>';

        // Timeline
        html += '<h5 style="font-size:0.85rem;margin:0.5rem 0 0.35rem;">Timeline</h5>';
        html += '<div class="rc-timeline">';

        if (rollout.steps && rollout.steps.length > 0) {
            rollout.steps.forEach(function(step) {
                var events = step.timeline_events || [];
                if (events.length === 0) {
                    // Fallback: synthesize events from basic step data
                    events = [];
                    if (step.step === 1) {
                        events.push({ timestamp_ms: 0, event_type: 'SYSTEM', content: 'Episode started' });
                    }
                    events.push({
                        timestamp_ms: (step.step || 0) * 100,
                        event_type: 'TOOL_CALL',
                        tool_name: String(step.action || 'action_' + step.step),
                        tool_args: null
                    });
                    events.push({
                        timestamp_ms: (step.step || 0) * 100 + 10,
                        event_type: 'TOOL_RESULT',
                        content: 'reward: ' + (step.reward || 0).toFixed(4),
                        reward: step.reward
                    });
                }
                events.forEach(function(evt) {
                    var evtType = (evt.event_type || 'unknown').toLowerCase().replace(/_/g, '-');
                    html += '<div class="rc-event rc-event-' + evtType + '">';
                    html += '<div class="rc-event-time">' + _fmtTime(evt.timestamp_ms) + '</div>';
                    html += '<div class="rc-event-type">' + _esc(evt.event_type || '') + '</div>';
                    html += '<div class="rc-event-body">';
                    if (evt.event_type === 'TOOL_CALL') {
                        html += '<strong>' + _esc(evt.tool_name || '') + '</strong>';
                        if (evt.tool_args && typeof evt.tool_args === 'object' && Object.keys(evt.tool_args).length > 0) {
                            html += '<pre class="rc-event-args">';
                            Object.keys(evt.tool_args).forEach(function(k) {
                                html += '  ' + _esc(k) + ': ' + _esc(JSON.stringify(evt.tool_args[k])) + '\n';
                            });
                            html += '</pre>';
                        }
                    } else if (evt.event_type === 'TOOL_RESULT') {
                        var resultContent = evt.content || '';
                        if (evt.state_snapshot && typeof evt.state_snapshot === 'object') {
                            Object.keys(evt.state_snapshot).forEach(function(k) {
                                resultContent += (resultContent ? '\n' : '') + k + ': ' + _esc(JSON.stringify(evt.state_snapshot[k]));
                            });
                        }
                        html += '<span>' + _esc(resultContent) + '</span>';
                    } else {
                        html += '<span>' + _esc(evt.content || '') + '</span>';
                    }
                    html += '</div></div>';
                });
            });
        } else {
            html += '<p class="rc-empty"><em>— none —</em></p>';
        }
        html += '</div>';

        // Tool calls summary
        if (rollout.steps && rollout.steps.length > 0) {
            var toolCounts = {};
            rollout.steps.forEach(function(s) {
                var name = String(s.action == null ? 'unknown' : s.action);
                toolCounts[name] = (toolCounts[name] || 0) + 1;
            });
            html += '<div class="rc-summary"><h5>Tool calls</h5>';
            var toolKeys = Object.keys(toolCounts);
            if (toolKeys.length === 0 || (toolKeys.length === 1 && toolKeys[0] === 'null')) {
                html += '<em class="rc-empty">— none —</em>';
            } else {
                toolKeys.forEach(function(k) {
                    if (k !== 'null') html += '<span class="rc-tool-badge">' + _esc(k) + ' ×' + toolCounts[k] + '</span> ';
                });
            }
            html += '</div>';
        }

        // Final environment state
        if (rollout.final_environment_state || rollout.final_outcome) {
            var stateObj = rollout.final_environment_state || rollout.final_outcome;
            html += '<div class="rc-summary"><h5>Final environment state</h5>';
            html += '<pre class="rc-code">';
            Object.keys(stateObj).forEach(function(k) {
                html += '  ' + _esc(k) + ': ' + _esc(JSON.stringify(stateObj[k])) + '\n';
            });
            html += '</pre></div>';
        }

        // Verifier results
        if (rollout.verifier_results && rollout.verifier_results.length > 0) {
            html += '<div class="rc-summary"><h5>Verifier results</h5>';
            rollout.verifier_results.forEach(function(vr) {
                var passed = vr.passed;
                var cls = passed ? 'rc-verifier-pass' : 'rc-verifier-fail';
                var icon = passed ? '✓' : '✗';
                html += '<div class="rc-verifier-check ' + cls + '">';
                html += '<span>' + icon + '</span> ';
                html += '<strong>' + _esc(vr.check || vr.name || '') + '</strong>';
                if (vr.detail || vr.reason) html += '<br><span style="font-size:0.78rem;color:var(--text-secondary);">Reason: ' + _esc(vr.detail || vr.reason) + '</span>';
                html += '</div>';
            });
            html += '</div>';
        }

        html += '</div>';
        return html;
    }

    /**
     * Render a side-by-side rollout comparison.
     * @param {HTMLElement} container - Target DOM element
     * @param {Object|null} baseline - Pre-training rollout
     * @param {Object|null} trained - Post-training rollout
     * @param {Object} meta - { scenarioName, envName, trainedLabel }
     */
    window.renderRolloutComparison = function(container, baseline, trained, meta) {
        if (!container) return;
        meta = meta || {};

        var html = '<div class="rc-container">';

        // Header
        html += '<div class="rc-header">';
        html += '<h3 class="rc-title">Rollout Comparison</h3>';
        html += '<div class="rc-meta">';
        if (meta.scenarioName) html += '<span class="rc-meta-item">Scenario: <strong>' + _esc(meta.scenarioName) + '</strong></span>';
        html += '<span class="rc-meta-item">Environment: <strong>' + _esc(meta.envName || '—') + '</strong></span>';
        if (baseline && baseline.id) html += '<span class="rc-meta-item">Pre-trained episode: <code>' + _esc(String(baseline.id).substring(0, 12)) + '</code></span>';
        if (trained && trained.id) html += '<span class="rc-meta-item">Post-training episode: <code>' + _esc(String(trained.id).substring(0, 12)) + '</code></span>';
        html += '</div></div>';

        // Two columns
        html += '<div class="rc-columns">';
        html += _renderColumn(baseline, 'Pre-trained Policy (Baseline)', 'rc-col-baseline');
        html += _renderColumn(trained, meta.trainedLabel || 'Trained Policy', 'rc-col-trained');
        html += '</div>';

        html += '</div>';
        container.innerHTML = html;
    };

})();
