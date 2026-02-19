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

