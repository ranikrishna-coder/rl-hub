-- AgentWork Simulator — MariaDB schema
-- Run after: CREATE DATABASE IF NOT EXISTS agentwork_simulator;
-- Usage: mysql -u agentwork -p agentwork_simulator < database/schema_mariadb.sql
--
-- No default/seed data is required. All tables may start empty. The app creates
-- environments, scenarios, and verifiers via the UI; contact and health data
-- are written at runtime.

-- 1. User / imported environments
CREATE TABLE IF NOT EXISTS user_environments (
    name       VARCHAR(255) PRIMARY KEY,
    data       LONGTEXT NOT NULL,
    source     VARCHAR(64) DEFAULT 'custom',
    created_at VARCHAR(32) NOT NULL,
    updated_at VARCHAR(32) NOT NULL
);

-- 2. Environment backups (snapshots)
CREATE TABLE IF NOT EXISTS environment_backups (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    backup_data LONGTEXT NOT NULL,
    env_count   INT NOT NULL DEFAULT 0,
    created_at  VARCHAR(32) NOT NULL,
    label       VARCHAR(255) NULL
);

-- 3. Health check snapshots
CREATE TABLE IF NOT EXISTS health_snapshots (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    snapshot   LONGTEXT NOT NULL,
    created_at VARCHAR(32) NOT NULL
);

-- 4. User / imported scenarios
CREATE TABLE IF NOT EXISTS user_scenarios (
    id         VARCHAR(255) PRIMARY KEY,
    data       LONGTEXT NOT NULL,
    product    VARCHAR(255) DEFAULT '',
    source     VARCHAR(64) DEFAULT 'custom',
    created_at VARCHAR(32) NOT NULL,
    updated_at VARCHAR(32) NOT NULL
);

-- 5. User / custom verifier definitions
CREATE TABLE IF NOT EXISTS user_verifiers (
    id          VARCHAR(255) PRIMARY KEY,
    data        LONGTEXT NOT NULL,
    environment VARCHAR(255) DEFAULT '',
    source      VARCHAR(64) DEFAULT 'custom',
    created_at  VARCHAR(32) NOT NULL,
    updated_at  VARCHAR(32) NOT NULL
);

-- 6. Contact form submissions
CREATE TABLE IF NOT EXISTS contact_submissions (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    name           VARCHAR(255) NOT NULL,
    email          VARCHAR(255) NOT NULL,
    organization   VARCHAR(255) NOT NULL,
    subject        VARCHAR(512) NULL,
    use_case       TEXT NOT NULL,
    created_at     VARCHAR(32) NOT NULL
);
