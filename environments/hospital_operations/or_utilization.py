"""OR Utilization Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class ORUtilizationEnv(HealthcareRLEnvironment):
    ACTIONS = ["schedule_case", "block_time", "emergency_case", "cancel", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.or_utilization = 0.0
        self.cases_scheduled = 0
        self.blocked_time = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.or_utilization = 0.0
        self.cases_scheduled = 0
        self.blocked_time = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            self.or_utilization,
            self.cases_scheduled / 20.0,
            self.blocked_time / 10.0,
            *[0.0] * 13
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if action_name == "schedule_case":
            self.or_utilization = min(1.0, self.or_utilization + 0.1)
            self.cases_scheduled += 1
        elif action_name == "block_time":
            self.blocked_time += 1.0
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        efficiency_score = self.or_utilization if self.or_utilization < 0.9 else 1.0 - (self.or_utilization - 0.9) * 10
        financial_score = self.or_utilization * 0.9
        return {
            RewardComponent.CLINICAL: self.cases_scheduled / 20.0,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.or_utilization,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 35
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"cases_scheduled": self.cases_scheduled},
            operational_efficiency={"or_utilization": self.or_utilization},
            financial_metrics={"or_revenue": self.or_utilization * 100000},
            patient_satisfaction=self.or_utilization,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

