# AgentWork Simulator

A production-grade platform with **50 fully implemented Gymnasium-compatible RL environments** for healthcare systems optimization.

## Overview

This platform provides comprehensive reinforcement learning environments modeling major healthcare systems including Epic, Cerner, Allscripts, Meditech, Philips, GE Healthcare, Health Catalyst, Innovaccer, Change Healthcare, Veeva, IQVIA, Teladoc, Amwell, InterSystems, and Orion Health.

## Architecture

```
agentwork-simulator/
├── apps/                   # Workflow definitions
│   └── workflow_definitions/  # Jira workflows (jira_workflows.json)
├── environments/          # RL environment implementations
│   ├── clinical/        # Clinical environments
│   ├── imaging/          # Imaging environments
│   ├── jira/             # Jira workflow envs (follow apps/workflow_definitions)
│   ├── population_health/ # 5 population health environments
│   ├── revenue_cycle/    # 5 revenue cycle environments
│   ├── clinical_trials/  # 5 clinical trial environments
│   ├── hospital_operations/ # 5 hospital operations environments
│   ├── telehealth/       # 5 telehealth environments
│   ├── interoperability/ # 5 interoperability environments
│   └── cross_workflow/   # 5 multi-agent cross-workflow environments
├── simulator/            # Simulation engines
│   ├── patient_generator.py
│   ├── hospital_simulator.py
│   ├── financial_simulator.py
│   └── clinical_trial_simulator.py
├── api/                  # FastAPI backend
│   └── main.py           # REST API endpoints
├── portal/               # UI metadata and registry
│   ├── environment_registry.py
│   └── environment_registry.json
├── database/             # Database schemas
│   └── schema.sql        # PostgreSQL schema
├── orchestration/        # Cross-workflow optimization
│   └── cross_workflow_orchestrator.py
├── training/             # Training scripts
│   ├── train_ppo.py
│   └── train_dqn.py
└── requirements.txt
```

## Features

- **50 Gymnasium-compatible RL environments** across 8 categories
- **Multi-agent support** for complex cross-workflow optimization
- **Digital twin simulations** of major healthcare systems
- **FastAPI REST API** for training and monitoring
- **PostgreSQL database** for metrics storage
- **Cross-workflow orchestration engine** for system-wide optimization
- **Comprehensive KPI tracking** (clinical, operational, financial)
- **Configurable reward functions** with weighted components

## Testing

The test suite validates Jira workflow definitions, Jira RL environments, registry integration, and coexistence with healthcare envs. Run before producing a deployable artifact:

```bash
pip install -r requirements.txt
python -m pytest tests/ -v --tb=short
```

- **tests/test_jira_workflow_definition.py** – Validates `apps/workflow_definitions/jira_workflows.json` and tool orders.
- **tests/test_jira_environments.py** – Jira env reset/step, rewards, workflow order.
- **tests/test_environment_registry_jira.py** – Jira envs registered and loadable.
- **tests/test_integration_jira_healthcare.py** – Jira and healthcare envs coexist.

CI and Docker build run this suite before deploy.

## Installation

```bash
# Clone repository
git clone git@github.com:ranikrishna-coder/rl-hub.git
cd rl-hub

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your Jira credentials (ask team lead if needed)

# Run test suite (recommended before deploy)
python -m pytest tests/ -v --tb=short

# (Optional) Set up PostgreSQL database
psql -U postgres -f database/schema.sql
```

## Quick Start

### Start API Server

```bash
pip install -r requirements.txt
python -m api.main
```

### Access the Web Catalog

Once the server is running, open your browser to:

**🌐 http://localhost:8000**

- **Catalog** — `/catalog` — Interactive catalog of all environments
- **Simulation Console** — `/test-console` — Run simulations for any environment
- **Training Console** — `/training-console` — Configure and monitor RL training runs
- **Dashboard** — `/dashboard` — Analytics and activity history

This displays a **beautiful interactive catalog** of all 50 environments with:
- Visual environment cards
- Search and filter capabilities  
- Detailed environment information
- Interactive "Test Environment" buttons
- "Simulation Console" for ImagingOrderPrioritization
- "Start Training" functionality

See [CATALOG_GUIDE.md](CATALOG_GUIDE.md) for full details.

API will be available at `http://localhost:8000`

### Train an Environment

```python
from training.train_ppo import train_ppo

# Train PPO on Treatment Pathway Optimization
model = train_ppo(
    environment_name="TreatmentPathwayOptimization",
    total_timesteps=100000
)
```

### Use API Endpoints

```bash
# List all environments
curl http://localhost:8000/environments

# Start training
curl -X POST http://localhost:8000/train/TreatmentPathwayOptimization \
  -H "Content-Type: application/json" \
  -d '{"algorithm": "PPO", "num_episodes": 1000}'

# Get KPIs
curl http://localhost:8000/kpis/TreatmentPathwayOptimization
```

## Environment Categories

### Clinical (10 environments)
- Treatment Pathway Optimization
- Sepsis Early Intervention
- ICU Resource Allocation
- Surgical Scheduling
- Diagnostic Test Sequencing
- Medication Dosing Optimization
- Readmission Reduction
- Care Coordination
- Chronic Disease Management
- Emergency Triage

### Imaging (5 environments)
- Imaging Order Prioritization
- Radiology Scheduling
- Scan Parameter Optimization
- Imaging Workflow Routing
- Equipment Utilization

### Population Health (5 environments)
- Risk Stratification
- Preventive Outreach
- Vaccination Allocation
- High Risk Monitoring
- Population Cost Optimization

### Revenue Cycle (5 environments)
- Claims Routing
- Denial Intervention
- Payment Plan Sequencing
- Billing Code Optimization
- Revenue Leakage Detection

### Clinical Trials (5 environments)
- Trial Patient Matching
- Adaptive Trial Design
- Enrollment Acceleration
- Protocol Deviation Mitigation
- Drug Dosage Trial Sequencing

### Hospital Operations (5 environments)
- Staffing Allocation
- OR Utilization
- Supply Chain Inventory
- Bed Turnover Optimization
- Equipment Maintenance

### Telehealth (5 environments)
- Virtual Visit Routing
- Escalation Policy
- Provider Load Balancing
- Follow-up Optimization
- Digital Adherence Coaching

### Interoperability (5 environments)
- Data Reconciliation
- Cross-System Alert Prioritization
- Duplicate Record Resolution
- Inter-Facility Transfer
- HIE Routing

### Cross-Workflow (5 multi-agent environments)
- Patient Journey Optimization
- Hospital Throughput
- Clinical-Financial Tradeoff
- Value-Based Care Optimization
- Multi-Hospital Network Coordination

## Reward Function Design

All environments use a weighted reward function:

```
Reward = w1 * clinical_score
       + w2 * efficiency_score
       + w3 * financial_score
       - w4 * risk_penalty
       - w5 * compliance_penalty
```

Default weights are configurable per environment.

## API Endpoints

- `GET /` - API information
- `GET /environments` - List all environments
- `POST /train/{environment_name}` - Start training
- `GET /training/{job_id}` - Get training status
- `GET /kpis/{environment_name}` - Get KPI metrics
- `GET /environment/{environment_name}/metadata` - Get environment metadata

## Database Schema

PostgreSQL tables:
- `training_jobs` - Training job tracking
- `kpi_metrics` - KPI metrics storage
- `environment_configs` - Environment configurations
- `reward_weights` - Reward weight configurations
- `episode_summaries` - Episode summaries
- `orchestration_logs` - Cross-workflow orchestration logs

## Training Examples

### PPO Training

```python
from training.train_ppo import train_ppo

model = train_ppo(
    environment_name="SepsisEarlyIntervention",
    total_timesteps=100000,
    learning_rate=3e-4
)
```

### DQN Training

```python
from training.train_dqn import train_dqn

model = train_dqn(
    environment_name="ICUResourceAllocation",
    total_timesteps=100000,
    learning_rate=1e-4
)
```

## Cross-Workflow Orchestration

```python
from orchestration.cross_workflow_orchestrator import CrossWorkflowOrchestrator

orchestrator = CrossWorkflowOrchestrator(
    environments={...},
    strategy=OrchestrationStrategy.COORDINATED
)

# Coordinate across workflows
result = orchestrator.coordinate_step()
```

## Extensibility

The platform is designed for extensibility to 200+ environments:

1. **Base Environment Class**: All environments inherit from `HealthcareRLEnvironment`
2. **Simulator Engines**: Reusable simulation components
3. **Registry System**: Automatic environment discovery
4. **Modular Design**: Easy to add new categories and environments

## Documentation

- **Repository structure (for new AI engineers):** [REPO_STRUCTURE.md](REPO_STRUCTURE.md)
- Environment registry: `portal/environment_registry.json`
- API documentation: Available at `http://localhost:8000/docs` when server is running
- Database schema: `database/schema.sql`

## License

[Specify your license]

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, coding standards, branching strategy, and PR guidelines.

