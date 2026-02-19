"""Population Cost Optimization Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class PopulationCostOptimizationEnv(HealthcareRLEnvironment):
    INTERVENTIONS = ["preventive_care", "care_coordination", "medication_optimization", "reduce_ed_visits", "no_intervention"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.INTERVENTIONS))
        self.population_size = 1000
        self.total_cost = 0.0
        self.cost_savings = 0.0
        self.interventions_applied = []
    def _initialize_state(self) -> np.ndarray:
        self.population_size = 1000
        self.total_cost = 500000.0
        self.cost_savings = 0.0
        self.interventions_applied = []
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            self.population_size / 2000.0,
            self.total_cost / 1000000.0,
            self.cost_savings / 200000.0,
            len(self.interventions_applied) / 10.0,
            *[0.0] * 11
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        intervention = self.INTERVENTIONS[action]
        if intervention != "no_intervention":
            self.interventions_applied.append(intervention)
            savings = {"preventive_care": 5000, "care_coordination": 3000, "medication_optimization": 4000, "reduce_ed_visits": 8000}.get(intervention, 0)
            self.cost_savings += savings
            self.total_cost = max(0, self.total_cost - savings)
        return {"intervention": intervention}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = 1.0 - self.total_cost / 1000000.0
        efficiency_score = self.cost_savings / 200000.0
        financial_score = self.cost_savings / 200000.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - self.total_cost / 1000000.0,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 20 or self.total_cost < 200000
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={},
            operational_efficiency={"cost_savings": self.cost_savings, "interventions": len(self.interventions_applied)},
            financial_metrics={"total_cost": self.total_cost, "cost_per_member": self.total_cost / self.population_size},
            patient_satisfaction=1.0 - self.total_cost / 1000000.0,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

