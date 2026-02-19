"""Protocol Deviation Mitigation Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class ProtocolDeviationMitigationEnv(HealthcareRLEnvironment):
    MITIGATIONS = ["retrain_site", "increase_monitoring", "corrective_action", "site_audit", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.MITIGATIONS))
        self.deviation_rate = 0.2
        self.mitigations_applied = []
        self.compliance_score = 0.8
    def _initialize_state(self) -> np.ndarray:
        self.deviation_rate = 0.2
        self.mitigations_applied = []
        self.compliance_score = 0.8
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            self.deviation_rate,
            self.compliance_score,
            len(self.mitigations_applied) / 5.0,
            *[0.0] * 13
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        mitigation = self.MITIGATIONS[action]
        if mitigation != "no_action":
            self.mitigations_applied.append(mitigation)
            self.deviation_rate = max(0, self.deviation_rate - 0.05)
            self.compliance_score = min(1.0, self.compliance_score + 0.1)
        return {"mitigation": mitigation}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.compliance_score
        efficiency_score = 1.0 - self.deviation_rate
        financial_score = self.compliance_score
        risk_penalty = self.deviation_rate if self.deviation_rate > 0.3 else 0.0
        compliance_penalty = 1.0 - self.compliance_score if self.compliance_score < 0.7 else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.compliance_score,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 25 or (self.deviation_rate < 0.1 and self.compliance_score > 0.9)
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"deviation_rate": self.deviation_rate, "compliance_score": self.compliance_score},
            operational_efficiency={"mitigations_applied": len(self.mitigations_applied)},
            financial_metrics={"compliance_value": self.compliance_score * 50000},
            patient_satisfaction=self.compliance_score,
            risk_score=self.deviation_rate,
            compliance_score=self.compliance_score,
            timestamp=self.time_step
        )

