"""Enrollment Acceleration Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class EnrollmentAccelerationEnv(HealthcareRLEnvironment):
    STRATEGIES = ["expand_sites", "increase_outreach", "relax_criteria", "incentivize", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.STRATEGIES))
        self.current_enrollment = 50
        self.target_enrollment = 200
        self.enrollment_rate = 2.0
        self.strategies_applied = []
    def _initialize_state(self) -> np.ndarray:
        self.current_enrollment = 50
        self.target_enrollment = 200
        self.enrollment_rate = 2.0
        self.strategies_applied = []
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            self.current_enrollment / self.target_enrollment,
            self.enrollment_rate / 10.0,
            len(self.strategies_applied) / 5.0,
            *[0.0] * 12
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        strategy = self.STRATEGIES[action]
        if strategy != "no_action":
            self.strategies_applied.append(strategy)
            self.enrollment_rate = min(10.0, self.enrollment_rate + 0.5)
        self.current_enrollment = min(self.target_enrollment, self.current_enrollment + int(self.enrollment_rate))
        return {"strategy": strategy}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.current_enrollment / self.target_enrollment
        efficiency_score = self.enrollment_rate / 10.0
        financial_score = self.current_enrollment / self.target_enrollment
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.current_enrollment / self.target_enrollment,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 35 or self.current_enrollment >= self.target_enrollment
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"enrollment": self.current_enrollment, "enrollment_rate": self.enrollment_rate},
            operational_efficiency={"enrollment_progress": self.current_enrollment / self.target_enrollment},
            financial_metrics={"trial_value": self.current_enrollment * 5000},
            patient_satisfaction=self.current_enrollment / self.target_enrollment,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

