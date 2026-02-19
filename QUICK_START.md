# Quick Start Guide

## Option 1: Start the API Server (Recommended)

### Using the start script:
```bash
cd rl-hub
./start_server.sh
```

### Or manually:
```bash
cd rl-hub

# Create virtual environment (first time only)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (first time only)
pip install -r requirements.txt

# Start the server
python -m api.main
```

The API will be available at:
- **API Server**: http://localhost:8000
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## Option 2: Use Environments Directly in Python

```python
# Example: Using an environment directly
import sys
sys.path.append('rl-hub')

from environments.clinical.treatment_pathway_optimization import TreatmentPathwayOptimizationEnv

# Create environment
env = TreatmentPathwayOptimizationEnv()

# Reset environment
state, info = env.reset()

# Run an episode
for step in range(100):
    action = env.action_space.sample()  # Random action
    state, reward, terminated, truncated, info = env.step(action)
    
    if terminated or truncated:
        break

# Get KPIs
kpis = env.get_kpis()
print(f"KPIs: {kpis}")
```

## Option 3: Train an Agent

```python
# Train using PPO
from training.train_ppo import train_ppo

model = train_ppo(
    environment_name="TreatmentPathwayOptimization",
    total_timesteps=10000  # Start with fewer steps for testing
)
```

## Accessing the API

Once the server is running, you can:

### 1. View API Documentation
Open your browser to: **http://localhost:8000/docs**

This provides an interactive Swagger UI where you can:
- See all available endpoints
- Test endpoints directly
- View request/response schemas

### 2. List All Environments
```bash
curl http://localhost:8000/environments
```

Or visit: http://localhost:8000/environments

### 3. Start Training
```bash
curl -X POST "http://localhost:8000/train/TreatmentPathwayOptimization" \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm": "PPO",
    "num_episodes": 100,
    "max_steps": 1000
  }'
```

### 4. Get KPIs
```bash
curl http://localhost:8000/kpis/TreatmentPathwayOptimization
```

### 5. Check Training Status
```bash
# Use the job_id from the training response
curl http://localhost:8000/training/{job_id}
```

## Available Environments

You can access any of the 50 environments. Some examples:

- `TreatmentPathwayOptimization`
- `SepsisEarlyIntervention`
- `ICUResourceAllocation`
- `ImagingOrderPrioritization`
- `RiskStratification`
- `ClaimsRouting`
- `TrialPatientMatching`
- `StaffingAllocation`
- `VirtualVisitRouting`
- `DataReconciliation`
- `PatientJourneyOptimization`

See full list: http://localhost:8000/environments

## Troubleshooting

### Port Already in Use
If port 8000 is already in use, modify `api/main.py`:
```python
uvicorn.run(app, host="0.0.0.0", port=8001)  # Change port
```

### Missing Dependencies
```bash
pip install -r requirements.txt
```

### Import Errors
Make sure you're in the project root directory and have activated the virtual environment.

