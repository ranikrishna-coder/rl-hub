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

    function _hasRealContent(rollout) {
        if (!rollout || !rollout.steps || rollout.steps.length === 0) return false;
        // Only consider "real" content if steps have actual timeline events (not just numeric actions)
        for (var i = 0; i < rollout.steps.length; i++) {
            var evts = rollout.steps[i].timeline_events || [];
            for (var j = 0; j < evts.length; j++) {
                if (evts[j].event_type === 'TOOL_CALL' || evts[j].event_type === 'TOOL_RESULT') return true;
                if (evts[j].event_type === 'SYSTEM' || evts[j].event_type === 'MODEL_THOUGHT') return true;
                if (evts[j].content && evts[j].content.length > 0) return true;
            }
        }
        return false;
    }

    function _hasNumericActions(rollout) {
        if (!rollout || !rollout.steps) return false;
        for (var i = 0; i < rollout.steps.length; i++) {
            if (rollout.steps[i].action != null) return true;
        }
        return false;
    }

    function _renderEmptyTimeline(stepsCount) {
        return '<div class="rc-empty-state">' +
            '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--text-secondary);opacity:0.5">' +
            '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>' +
            '<p>No timeline events recorded</p>' +
            (stepsCount > 0 ? '<span>' + stepsCount + ' step' + (stepsCount === 1 ? '' : 's') + ' completed</span>' : '') +
            '</div>';
    }

    function _renderColumn(rollout, title, cssClass) {
        if (!rollout) {
            return '<div class="rc-column ' + cssClass + '">' +
                '<h4 class="rc-col-title">' + _esc(title) + '</h4>' +
                '<div class="rc-empty-state">' +
                '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--text-secondary);opacity:0.5">' +
                '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>' +
                '<p>No rollout data available</p>' +
                '</div></div>';
        }

        var html = '<div class="rc-column ' + cssClass + '">';
        html += '<h4 class="rc-col-title">' + _esc(title) + '</h4>';

        // Policy info — compact inline
        html += '<div class="rc-policy-info">';
        html += '<span>Policy: <strong>' + _esc(rollout.policy_name || rollout.source || 'unknown') + '</strong></span>';
        html += '<span>Checkpoint: <code>' + _esc(rollout.checkpoint_label || '—') + '</code></span>';
        if (rollout.total_reward != null) {
            html += '<span>Reward: <strong>' + Number(rollout.total_reward).toFixed(2) + '</strong></span>';
        }
        html += '</div>';

        var hasContent = _hasRealContent(rollout);
        var hasActions = _hasNumericActions(rollout);

        if (!hasContent && !hasActions) {
            // No data at all
            html += _renderEmptyTimeline(rollout.steps ? rollout.steps.length : 0);
        } else if (!hasContent && hasActions) {
            // Numeric actions only (RL env) — show clean summary instead of fake timeline
            html += '<div class="rc-action-summary">';
            var totalReward = 0;
            var stepCount = 0;
            rollout.steps.forEach(function(step) {
                if (step.action != null) {
                    stepCount++;
                    totalReward += (step.reward || 0);
                }
            });
            html += '<div class="rc-summary-stat"><span class="rc-summary-label">Steps</span><span class="rc-summary-value">' + stepCount + '</span></div>';
            html += '<div class="rc-summary-stat"><span class="rc-summary-label">Total Reward</span><span class="rc-summary-value">' + totalReward.toFixed(4) + '</span></div>';
            if (rollout.steps.length > 0) {
                html += '<div class="rc-summary-stat"><span class="rc-summary-label">Avg Reward/Step</span><span class="rc-summary-value">' + (totalReward / (stepCount || 1)).toFixed(4) + '</span></div>';
            }
            html += '</div>';
        } else {
            // Rich timeline — render events
            html += '<div class="rc-timeline">';
            rollout.steps.forEach(function(step) {
                var events = step.timeline_events || [];
                if (events.length === 0) {
                    // Skip steps with no timeline events
                    return;
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
            html += '</div>';
        }

        // Tool calls summary — only show for named actions (not numeric indices)
        if (hasContent && rollout.steps && rollout.steps.length > 0) {
            var toolCounts = {};
            var hasNamedActions = false;
            rollout.steps.forEach(function(s) {
                if (s.action != null) {
                    var name = String(s.action);
                    // Skip purely numeric action indices
                    if (/^\d+$/.test(name)) return;
                    hasNamedActions = true;
                    toolCounts[name] = (toolCounts[name] || 0) + 1;
                }
            });
            var toolKeys = Object.keys(toolCounts);
            if (hasNamedActions && toolKeys.length > 0) {
                html += '<div class="rc-summary"><h5>Tool calls</h5>';
                toolKeys.forEach(function(k) {
                    html += '<span class="rc-tool-badge">' + _esc(k) + ' \u00d7' + toolCounts[k] + '</span> ';
                });
                html += '</div>';
            }
        }

        // Final environment state
        if (rollout.final_environment_state || rollout.final_outcome) {
            var stateObj = rollout.final_environment_state || rollout.final_outcome;
            html += '<div class="rc-summary"><h5>Final state</h5>';
            html += '<pre class="rc-code">';
            Object.keys(stateObj).forEach(function(k) {
                var val = stateObj[k];
                // Format long floating point numbers
                if (typeof val === 'number' && !Number.isInteger(val)) {
                    val = val.toFixed(4);
                } else {
                    val = JSON.stringify(val);
                }
                html += '  ' + _esc(k) + ': ' + _esc(val) + '\n';
            });
            html += '</pre></div>';
        }

        // Verifier results — compact chip layout
        if (rollout.verifier_results && rollout.verifier_results.length > 0) {
            html += '<div class="rc-summary"><h5>Verifier results</h5><div class="rc-verifier-list">';
            rollout.verifier_results.forEach(function(vr) {
                var passed = vr.passed;
                var cls = passed ? 'rc-verifier-pass' : 'rc-verifier-fail';
                var icon = passed ? '\u2713' : '\u2717';
                html += '<div class="rc-verifier-chip ' + cls + '" title="' + _esc(vr.detail || vr.reason || '') + '">';
                html += '<span>' + icon + '</span> ';
                html += _esc(vr.check || vr.name || '');
                html += '</div>';
            });
            html += '</div></div>';
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
