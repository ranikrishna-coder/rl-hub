"""Follow-up Optimization Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class FollowUpOptimizationEnv(HealthcareRLEnvironment):
    FOLLOWUPS = ["immediate", "1_week", "2_weeks", "1_month", "3_months", "no_followup"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.FOLLOWUPS))
        self.patients = []
        self.followups_scheduled = []
        self.adherence_rate = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.patients = [{"risk": self.np_random.uniform(0, 1), "condition": self.np_random.choice(["chronic", "acute", "preventive"])} for _ in range(10)]
        self.followups_scheduled = []
        self.adherence_rate = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            len(self.patients) / 15.0,
            len(self.followups_scheduled) / 10.0,
            self.adherence_rate,
            np.mean([p["risk"] for p in self.patients[:5]]) if self.patients else 0.0,
            *[0.0] * 11
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        followup = self.FOLLOWUPS[action]
        if self.patients and followup != "no_followup":
            patient = self.patients.pop(0)
            self.followups_scheduled.append({**patient, "followup": followup})
            self.adherence_rate = min(1.0, self.adherence_rate + 0.1)
        return {"followup": followup}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.adherence_rate
        efficiency_score = len(self.followups_scheduled) / 10.0
        financial_score = self.adherence_rate * 0.9
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.adherence_rate,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 20 or len(self.patients) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"adherence_rate": self.adherence_rate},
            operational_efficiency={"followups_scheduled": len(self.followups_scheduled)},
            financial_metrics={"followup_revenue": len(self.followups_scheduled) * 100},
            patient_satisfaction=self.adherence_rate,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

