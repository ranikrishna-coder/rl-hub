// Simulation Console for ImagingOrderPrioritization Environment

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
let simulationState = null;
let simulationInterval = null;
let stepCount = 0;
let metricsHistory = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    setupRangeInputs();
});

function setupEventListeners() {
    document.getElementById('btn-initialize').addEventListener('click', initializeEnvironment);
    document.getElementById('btn-reset').addEventListener('click', resetSimulation);
    document.getElementById('btn-step').addEventListener('click', runStep);
    document.getElementById('btn-auto').addEventListener('click', startAutoRun);
    document.getElementById('btn-stop').addEventListener('click', stopAutoRun);
}

function setupRangeInputs() {
    ['ct', 'mri', 'xray'].forEach(type => {
        const slider = document.getElementById(`${type}-availability`);
        const display = document.getElementById(`${type}-value`);
        slider.addEventListener('input', (e) => {
            display.textContent = `${e.target.value}%`;
        });
    });
}

async function initializeEnvironment() {
    const config = getConfiguration();
    
    try {
        // Create environment instance via API
        const response = await fetch(`${API_BASE}/kpis/ImagingOrderPrioritization`);
        if (!response.ok) throw new Error('Failed to initialize environment');
        
        simulationState = {
            config: config,
            queue: generateInitialQueue(config),
            processed: [],
            metrics: {
                queueLength: config.queueSize,
                urgentWaiting: Math.floor(config.queueSize * config.highUrgencyPct / 100),
                utilization: 0,
                processed: 0,
                waitTime: 0,
                revenue: 0
            },
            step: 0
        };
        
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
    return {
        queueSize: parseInt(document.getElementById('queue-size').value),
        highUrgencyPct: parseInt(document.getElementById('high-urgency-pct').value),
        avgOrderValue: parseInt(document.getElementById('avg-order-value').value),
        ctAvailability: parseInt(document.getElementById('ct-availability').value) / 100,
        mriAvailability: parseInt(document.getElementById('mri-availability').value) / 100,
        xrayAvailability: parseInt(document.getElementById('xray-availability').value) / 100,
        agentStrategy: document.getElementById('agent-strategy').value
    };
}

function generateInitialQueue(config) {
    const queue = [];
    const urgentCount = Math.floor(config.queueSize * config.highUrgencyPct / 100);
    
    for (let i = 0; i < config.queueSize; i++) {
        const isUrgent = i < urgentCount;
        const urgency = isUrgent ? 
            Math.random() * 0.3 + 0.7 : // 0.7-1.0 for urgent
            Math.random() * 0.5 + 0.2;  // 0.2-0.7 for routine
        
        queue.push({
            id: `ORD-${String(i + 1).padStart(4, '0')}`,
            type: ['ct', 'mri', 'xray', 'ultrasound', 'pet'][Math.floor(Math.random() * 5)],
            urgency: urgency,
            value: config.avgOrderValue * (0.8 + Math.random() * 0.4),
            clinicalIndication: Math.random(),
            waitTime: 0
        });
    }
    
    return queue.sort((a, b) => b.urgency - a.urgency);
}

function runStep() {
    if (!simulationState || simulationState.queue.length === 0) {
        stopAutoRun();
        return;
    }
    
    const config = simulationState.config;
    const order = selectNextOrder(config.agentStrategy);
    
    if (!order) return;
    
    // Remove from queue
    const orderIndex = simulationState.queue.indexOf(order);
    simulationState.queue.splice(orderIndex, 1);
    
    // Determine priority based on agent strategy
    const priority = determinePriority(order, config.agentStrategy);
    
    // Process order
    const processed = {
        ...order,
        priority: priority,
        processedAt: stepCount,
        waitTime: order.waitTime
    };
    
    simulationState.processed.push(processed);
    
    // Update metrics
    updateMetricsAfterStep(processed);
    stepCount++;
    simulationState.step = stepCount;
    
    // Update display
    updateDisplay();
    updateMetrics();
    updateActionDisplay(order, priority);
    showRecommendations();
    
    // Check if done
    if (simulationState.queue.length === 0) {
        stopAutoRun();
        showFinalResults();
    }
}

function selectNextOrder(strategy) {
    if (simulationState.queue.length === 0) return null;
    
    switch (strategy) {
        case 'urgency_first':
            return simulationState.queue.reduce((max, order) => 
                order.urgency > max.urgency ? order : max
            );
        case 'value_first':
            return simulationState.queue.reduce((max, order) => 
                order.value > max.value ? order : max
            );
        case 'balanced':
            // RL-optimized: balance urgency and value
            return simulationState.queue.reduce((best, order) => {
                const bestScore = best.urgency * 0.6 + (best.value / 1000) * 0.4;
                const orderScore = order.urgency * 0.6 + (order.value / 1000) * 0.4;
                return orderScore > bestScore ? order : best;
            });
        default: // random
            return simulationState.queue[Math.floor(Math.random() * simulationState.queue.length)];
    }
}

function determinePriority(order, strategy) {
    if (order.urgency > 0.8) return 'stat';
    if (order.urgency > 0.6) return 'urgent';
    if (order.urgency > 0.4) return 'routine';
    return 'defer';
}

function updateMetricsAfterStep(processed) {
    const metrics = simulationState.metrics;
    
    metrics.queueLength = simulationState.queue.length;
    metrics.urgentWaiting = simulationState.queue.filter(o => o.urgency > 0.7).length;
    metrics.processed++;
    
    // Calculate utilization
    const totalCapacity = 10;
    metrics.utilization = Math.min(100, (metrics.processed / totalCapacity) * 100);
    
    // Update wait time (average)
    const totalWait = simulationState.processed.reduce((sum, o) => sum + o.waitTime, 0);
    metrics.waitTime = metrics.processed > 0 ? Math.round(totalWait / metrics.processed) : 0;
    
    // Update revenue
    metrics.revenue += processed.value;
    
    // Increment wait time for remaining orders
    simulationState.queue.forEach(order => order.waitTime++);
    
    // Store history
    metricsHistory.push({
        step: stepCount,
        queueLength: metrics.queueLength,
        urgentWaiting: metrics.urgentWaiting,
        utilization: metrics.utilization
    });
}

function updateDisplay() {
    updateQueueDisplay();
    updateProcessedDisplay();
}

function updateQueueDisplay() {
    const queueDiv = document.getElementById('order-queue');
    
    if (!simulationState || simulationState.queue.length === 0) {
        queueDiv.innerHTML = '<div class="empty-state">Queue is empty</div>';
        return;
    }
    
    queueDiv.innerHTML = simulationState.queue.map(order => {
        const urgencyClass = order.urgency > 0.8 ? 'urgent' : 
                           order.urgency > 0.6 ? 'high' : 
                           order.urgency > 0.4 ? 'medium' : 'low';
        const badgeClass = order.urgency > 0.8 ? 'badge-urgent' : 
                          order.urgency > 0.6 ? 'badge-high' : 
                          order.urgency > 0.4 ? 'badge-medium' : 'badge-low';
        const priorityText = order.urgency > 0.8 ? 'STAT' : 
                            order.urgency > 0.6 ? 'URGENT' : 
                            order.urgency > 0.4 ? 'ROUTINE' : 'LOW';
        
        return `
            <div class="order-item ${urgencyClass}">
                <div class="order-info">
                    <div class="order-id">${order.id}</div>
                    <div class="order-details">
                        Type: ${order.type.toUpperCase()} | 
                        Value: $${Math.round(order.value)} | 
                        Wait: ${order.waitTime} min
                    </div>
                </div>
                <span class="order-badge ${badgeClass}">${priorityText}</span>
            </div>
        `;
    }).join('');
}

function updateProcessedDisplay() {
    const processedDiv = document.getElementById('processed-list');
    
    if (!simulationState || simulationState.processed.length === 0) {
        processedDiv.innerHTML = '<div class="empty-state">No orders processed yet</div>';
        return;
    }
    
    const recent = simulationState.processed.slice(-5).reverse();
    processedDiv.innerHTML = recent.map(order => {
        return `
            <div class="order-item">
                <div class="order-info">
                    <div class="order-id">${order.id}</div>
                    <div class="order-details">
                        Priority: ${order.priority.toUpperCase()} | 
                        Value: $${Math.round(order.value)}
                    </div>
                </div>
                <span class="order-badge badge-low">PROCESSED</span>
            </div>
        `;
    }).join('');
}

function updateActionDisplay(order, priority) {
    const actionDiv = document.getElementById('action-display');
    
    if (!order) {
        actionDiv.innerHTML = '<div class="empty-state">No action</div>';
        return;
    }
    
    actionDiv.innerHTML = `
        <div class="action-priority">${priority.toUpperCase()}</div>
        <div class="action-description">
            Processing ${order.id}<br>
            Type: ${order.type.toUpperCase()}<br>
            Urgency: ${(order.urgency * 100).toFixed(0)}%
        </div>
    `;
}

function updateMetrics() {
    if (!simulationState) return;
    
    const m = simulationState.metrics;
    
    document.getElementById('metric-queue').textContent = m.queueLength;
    document.getElementById('metric-urgent').textContent = m.urgentWaiting;
    document.getElementById('metric-utilization').textContent = `${m.utilization.toFixed(0)}%`;
    document.getElementById('metric-processed').textContent = m.processed;
    document.getElementById('metric-wait').textContent = `${m.waitTime} min`;
    document.getElementById('metric-revenue').textContent = `$${Math.round(m.revenue)}`;
    
    // Update trends (simplified)
    updateTrend('queue', m.queueLength);
    updateTrend('urgent', m.urgentWaiting);
    updateTrend('utilization', m.utilization);
}

function updateTrend(metric, currentValue) {
    const trendEl = document.getElementById(`trend-${metric}`);
    if (metricsHistory.length < 2) {
        trendEl.textContent = '-';
        return;
    }
    
    const prev = metricsHistory[metricsHistory.length - 2];
    const prevValue = prev[metric === 'queue' ? 'queueLength' : 
                       metric === 'urgent' ? 'urgentWaiting' : 'utilization'];
    
    if (currentValue > prevValue) {
        trendEl.textContent = '↗ Increasing';
        trendEl.className = 'metric-trend trend-up';
    } else if (currentValue < prevValue) {
        trendEl.textContent = '↘ Decreasing';
        trendEl.className = 'metric-trend trend-down';
    } else {
        trendEl.textContent = '→ Stable';
        trendEl.className = 'metric-trend';
    }
}

function showRecommendations() {
    if (!simulationState) return;
    
    const recommendations = [];
    const metrics = simulationState.metrics;
    
    if (metrics.urgentWaiting > 3) {
        recommendations.push('⚠️ High number of urgent orders waiting. Consider prioritizing STAT orders immediately.');
    }
    
    if (metrics.utilization < 50) {
        recommendations.push('💡 Equipment utilization is low. You can process more orders.');
    }
    
    if (metrics.waitTime > 30) {
        recommendations.push('⏱️ Average wait time is high. Consider increasing processing capacity.');
    }
    
    if (simulationState.queue.length > 10) {
        recommendations.push('📋 Large queue detected. The RL agent recommends balanced prioritization strategy.');
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
        if (simulationState.queue.length === 0) {
            stopAutoRun();
        }
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
    
    document.getElementById('order-queue').innerHTML = '<div class="empty-state">Click "Initialize Environment" to start</div>';
    document.getElementById('processed-list').innerHTML = '<div class="empty-state">No orders processed yet</div>';
    document.getElementById('action-display').innerHTML = '<div class="empty-state">Waiting for initialization...</div>';
    
    updateMetrics();
    showRecommendations();
    showFinalResults();
}

function showFinalResults() {
    if (!simulationState) {
        document.getElementById('results-clinical').textContent = '-';
        document.getElementById('results-efficiency').textContent = '-';
        document.getElementById('results-financial').textContent = '-';
        document.getElementById('results-roi').textContent = '-';
        return;
    }
    
    const m = simulationState.metrics;
    const totalOrders = m.processed + m.queueLength;
    const completionRate = totalOrders > 0 ? (m.processed / totalOrders * 100).toFixed(1) : 0;
    
    // Clinical Outcomes
    const urgentProcessed = simulationState.processed.filter(o => o.urgency > 0.7).length;
    const urgentRate = m.processed > 0 ? (urgentProcessed / m.processed * 100).toFixed(1) : 0;
    document.getElementById('results-clinical').innerHTML = `
        <strong>Urgent Orders Processed:</strong> ${urgentProcessed}<br>
        <strong>Urgency Handling Rate:</strong> ${urgentRate}%<br>
        <strong>Average Wait Time:</strong> ${m.waitTime} min
    `;
    
    // Operational Efficiency
    document.getElementById('results-efficiency').innerHTML = `
        <strong>Completion Rate:</strong> ${completionRate}%<br>
        <strong>Equipment Utilization:</strong> ${m.utilization.toFixed(1)}%<br>
        <strong>Orders Processed:</strong> ${m.processed}
    `;
    
    // Financial Impact
    const avgOrderValue = m.processed > 0 ? (m.revenue / m.processed).toFixed(0) : 0;
    document.getElementById('results-financial').innerHTML = `
        <strong>Total Revenue:</strong> $${Math.round(m.revenue)}<br>
        <strong>Avg Order Value:</strong> $${avgOrderValue}<br>
        <strong>Revenue per Hour:</strong> $${Math.round(m.revenue / (stepCount / 60)) || 0}
    `;
    
    // ROI Assessment
    const efficiencyGain = m.utilization > 70 ? 'High' : m.utilization > 50 ? 'Medium' : 'Low';
    const recommendation = m.urgentWaiting === 0 ? 
        '✅ Excellent prioritization. All urgent orders processed.' :
        '⚠️ Some urgent orders remain. Consider adjusting strategy.';
    
    document.getElementById('results-roi').innerHTML = `
        <strong>Efficiency:</strong> ${efficiencyGain}<br>
        <strong>Strategy:</strong> ${simulationState.config.agentStrategy}<br>
        ${recommendation}
    `;
}

