# Verifier Architecture Quick Start Guide

## What Changed?

The **TreatmentPathwayOptimization** environment has been refactored to use a **verifier-based architecture** instead of direct reward calculation.

### Before (Old Architecture)
```python
# Reward calculated directly in environment
def _calculate_reward_components(self, state, action, info):
    # Direct calculation logic here
    return reward_components
```

### After (New Architecture)
```python
# Reward delegated to verifier
reward, breakdown = self.verifier.evaluate(state, action, next_state, info)
# Breakdown logged to observability layer
```

## Key Components

### 1. Verifiers
- **ClinicalVerifier**: Evaluates clinical outcomes
- **OperationalVerifier**: Evaluates efficiency metrics
- **FinancialVerifier**: Evaluates cost-effectiveness
- **ComplianceVerifier**: Evaluates compliance (returns penalties)
- **EnsembleVerifier**: Combines multiple verifiers

### 2. Observability
- **RewardLogger**: Logs all reward calculations
- **ActionTraceLogger**: Logs state transitions
- **EpisodeMetrics**: Tracks aggregate metrics
- **AuditLogger**: Logs all system events

### 3. Governance
- **SafetyGuardrails**: Validates actions before execution
- **RiskThresholds**: Manages risk thresholds
- **ComplianceRules**: Enforces compliance rules

## Usage

### Basic Usage (Default Configuration)
```python
from environments.clinical.treatment_pathway_optimization import TreatmentPathwayOptimizationEnv

# Creates environment with default ensemble verifier
env = TreatmentPathwayOptimizationEnv()

# Use as normal Gymnasium environment
state, info = env.reset()
next_state, reward, done, truncated, info = env.step(action)

# Access reward breakdown
breakdown = info['reward_breakdown']
print(breakdown)  # Shows all reward components
```

### Custom Verifier
```python
from verifiers.verifier_registry import VerifierRegistry

# Create custom ensemble
verifier = VerifierRegistry.create_default_ensemble()
env = TreatmentPathwayOptimizationEnv(verifier=verifier)
```

### Access Observability Data
```python
# After running episode
observability_data = env.get_observability_data()

# Contains:
# - reward_summary: Episode reward statistics
# - action_traces: All state transitions
# - episode_metrics: Aggregate metrics
# - audit_log: All audit events
```

## API Endpoints

### List Verifiers
```bash
GET /verifiers
```

### Configure Verifier
```bash
POST /verifiers/configure
{
  "verifier_type": "clinical",
  "environment_name": "TreatmentPathwayOptimization",
  "weights": {"risk_improvement": 0.5},
  "thresholds": {"max_risk_score": 0.8}
}
```

### Get Reward Breakdown
```bash
GET /episodes/{episode_id}/reward-breakdown
```

### Get Audit Log
```bash
GET /episodes/{episode_id}/audit-log
```

### Configure Governance
```bash
POST /governance/configure
{
  "environment_name": "TreatmentPathwayOptimization",
  "max_risk_threshold": 0.8,
  "compliance_hard_stop": true
}
```

## Testing

Run the test script:
```bash
python3 test_verifier_refactor.py
```

## Next Steps

1. Test the refactored environment
2. Verify reward breakdowns are correct
3. Check observability logs
4. Test governance overrides
5. Roll out to other environments

