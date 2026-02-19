"""Value-Based Care Optimization Environment - Optimizes value-based care metrics"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class ValueBasedCareOptimizationEnv(HealthcareRLEnvironment):
    ACTIONS = ["improve_quality", "reduce_cost", "enhance_outcomes", "optimize_value", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.quality_score = 0.7
        self.cost_score = 0.6
        self.value_score = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.quality_score = 0.7
        self.cost_score = 0.6
        self.value_score = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            self.quality_score, self.cost_score, self.value_score,
            (self.quality_score + (1.0 - self.cost_score)) / 2.0,
            *[0.0] * 12
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if action_name == "improve_quality":
            self.quality_score = min(1.0, self.quality_score + 0.1)
        elif action_name == "reduce_cost":
            self.cost_score = min(1.0, self.cost_score + 0.1)
        elif action_name == "optimize_value":
            self.quality_score = min(1.0, self.quality_score + 0.05)
            self.cost_score = min(1.0, self.cost_score + 0.05)
        self.value_score = (self.quality_score + (1.0 - self.cost_score)) / 2.0
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.quality_score
        efficiency_score = 1.0 - self.cost_score
        financial_score = self.value_score
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.value_score,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 30 or self.value_score > 0.85
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"quality_score": self.quality_score},
            operational_efficiency={"cost_score": self.cost_score},
            financial_metrics={"value_score": self.value_score},
            patient_satisfaction=self.value_score,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

