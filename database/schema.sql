-- PostgreSQL Database Schema for RL Hub

-- Training Jobs Table
CREATE TABLE IF NOT EXISTS training_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment_name VARCHAR(255) NOT NULL,
    algorithm VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    config JSONB,
    num_episodes INTEGER NOT NULL,
    max_steps INTEGER NOT NULL,
    progress INTEGER DEFAULT 0,
    results JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- KPI Metrics Table
CREATE TABLE IF NOT EXISTS kpi_metrics (
    metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES training_jobs(job_id),
    environment_name VARCHAR(255) NOT NULL,
    episode_number INTEGER,
    time_step INTEGER,
    clinical_outcomes JSONB,
    operational_efficiency JSONB,
    financial_metrics JSONB,
    patient_satisfaction FLOAT,
    risk_score FLOAT,
    compliance_score FLOAT,
    total_reward FLOAT,
    reward_components JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Environment Configurations Table
CREATE TABLE IF NOT EXISTS environment_configs (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment_name VARCHAR(255) NOT NULL,
    config_name VARCHAR(255) NOT NULL,
    config_data JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(environment_name, config_name)
);

-- Reward Weight Configurations
CREATE TABLE IF NOT EXISTS reward_weights (
    weight_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_name VARCHAR(255) NOT NULL,
    clinical_weight FLOAT DEFAULT 0.3,
    efficiency_weight FLOAT DEFAULT 0.2,
    financial_weight FLOAT DEFAULT 0.2,
    patient_satisfaction_weight FLOAT DEFAULT 0.1,
    risk_penalty_weight FLOAT DEFAULT 0.1,
    compliance_penalty_weight FLOAT DEFAULT 0.1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(config_name)
);

-- Episode Summaries
CREATE TABLE IF NOT EXISTS episode_summaries (
    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES training_jobs(job_id),
    episode_number INTEGER NOT NULL,
    total_reward FLOAT,
    mean_reward FLOAT,
    episode_length INTEGER,
    final_kpis JSONB,
    kpi_trends JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cross-Workflow Orchestration Logs
CREATE TABLE IF NOT EXISTS orchestration_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    orchestration_id VARCHAR(255) NOT NULL,
    environment_name VARCHAR(255) NOT NULL,
    action_taken VARCHAR(255),
    state_before JSONB,
    state_after JSONB,
    reward FLOAT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_training_jobs_status ON training_jobs(status);
CREATE INDEX IF NOT EXISTS idx_training_jobs_environment ON training_jobs(environment_name);
CREATE INDEX IF NOT EXISTS idx_kpi_metrics_job_id ON kpi_metrics(job_id);
CREATE INDEX IF NOT EXISTS idx_kpi_metrics_environment ON kpi_metrics(environment_name);
CREATE INDEX IF NOT EXISTS idx_kpi_metrics_timestamp ON kpi_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_episode_summaries_job_id ON episode_summaries(job_id);
CREATE INDEX IF NOT EXISTS idx_orchestration_logs_orchestration_id ON orchestration_logs(orchestration_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for training_jobs
CREATE TRIGGER update_training_jobs_updated_at BEFORE UPDATE ON training_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VERIFIER ARCHITECTURE TABLES
-- ============================================================================

-- Verifier Configurations Table
CREATE TABLE IF NOT EXISTS verifier_configs (
    verifier_config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment_name VARCHAR(255) NOT NULL,
    verifier_type VARCHAR(100) NOT NULL,  -- 'clinical', 'operational', 'financial', 'compliance', 'ensemble'
    verifier_name VARCHAR(255) NOT NULL,
    weights JSONB NOT NULL,  -- Component weights
    thresholds JSONB,  -- Threshold values
    enabled BOOLEAN DEFAULT TRUE,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(environment_name, verifier_name)
);

-- Reward Logs Table
CREATE TABLE IF NOT EXISTS reward_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id VARCHAR(255) NOT NULL,
    step_id INTEGER NOT NULL,
    state_id VARCHAR(255),
    action VARCHAR(255),
    reward FLOAT NOT NULL,
    reward_breakdown JSONB NOT NULL,  -- Component breakdown
    verifier_name VARCHAR(255) NOT NULL,
    environment_name VARCHAR(255) NOT NULL,
    metadata JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Action Traces Table
CREATE TABLE IF NOT EXISTS action_traces (
    trace_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id VARCHAR(255) NOT NULL,
    step_id INTEGER NOT NULL,
    before_state JSONB NOT NULL,
    action VARCHAR(255) NOT NULL,
    after_state JSONB NOT NULL,
    transition_info JSONB,
    environment_name VARCHAR(255) NOT NULL,
    metadata JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Episode Metrics Table
CREATE TABLE IF NOT EXISTS episode_metrics (
    metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id VARCHAR(255) NOT NULL UNIQUE,
    environment_name VARCHAR(255) NOT NULL,
    cumulative_reward FLOAT NOT NULL,
    clinical_score FLOAT,
    efficiency_score FLOAT,
    financial_score FLOAT,
    compliance_violations INTEGER DEFAULT 0,
    episode_length INTEGER NOT NULL,
    final_risk_score FLOAT,
    total_cost FLOAT,
    metadata JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Compliance Violations Table
CREATE TABLE IF NOT EXISTS compliance_violations (
    violation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id VARCHAR(255) NOT NULL,
    step_id INTEGER,
    environment_name VARCHAR(255) NOT NULL,
    rule_name VARCHAR(255) NOT NULL,
    rule_type VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL,  -- 'warning', 'error', 'critical'
    message TEXT NOT NULL,
    violation_details JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Governance Configurations Table
CREATE TABLE IF NOT EXISTS governance_configs (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment_name VARCHAR(255) NOT NULL,
    max_risk_threshold FLOAT DEFAULT 0.8,
    compliance_hard_stop BOOLEAN DEFAULT TRUE,
    human_in_the_loop BOOLEAN DEFAULT FALSE,
    override_actions JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(environment_name)
);

-- Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,  -- 'verifier_evaluation', 'action_taken', 'compliance_violation', etc.
    episode_id VARCHAR(255),
    step_id INTEGER,
    environment_name VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    details JSONB,
    user_id VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for verifier architecture tables
CREATE INDEX IF NOT EXISTS idx_reward_logs_episode ON reward_logs(episode_id);
CREATE INDEX IF NOT EXISTS idx_reward_logs_environment ON reward_logs(environment_name);
CREATE INDEX IF NOT EXISTS idx_reward_logs_timestamp ON reward_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_reward_logs_verifier ON reward_logs(verifier_name);

CREATE INDEX IF NOT EXISTS idx_action_traces_episode ON action_traces(episode_id);
CREATE INDEX IF NOT EXISTS idx_action_traces_environment ON action_traces(environment_name);
CREATE INDEX IF NOT EXISTS idx_action_traces_timestamp ON action_traces(timestamp);

CREATE INDEX IF NOT EXISTS idx_episode_metrics_episode ON episode_metrics(episode_id);
CREATE INDEX IF NOT EXISTS idx_episode_metrics_environment ON episode_metrics(environment_name);
CREATE INDEX IF NOT EXISTS idx_episode_metrics_timestamp ON episode_metrics(timestamp);

CREATE INDEX IF NOT EXISTS idx_compliance_violations_episode ON compliance_violations(episode_id);
CREATE INDEX IF NOT EXISTS idx_compliance_violations_environment ON compliance_violations(environment_name);
CREATE INDEX IF NOT EXISTS idx_compliance_violations_severity ON compliance_violations(severity);
CREATE INDEX IF NOT EXISTS idx_compliance_violations_timestamp ON compliance_violations(timestamp);

CREATE INDEX IF NOT EXISTS idx_audit_logs_episode ON audit_logs(episode_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_environment ON audit_logs(environment_name);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);

CREATE INDEX IF NOT EXISTS idx_verifier_configs_environment ON verifier_configs(environment_name);
CREATE INDEX IF NOT EXISTS idx_governance_configs_environment ON governance_configs(environment_name);

