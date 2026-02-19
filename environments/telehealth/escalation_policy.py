"""Escalation Policy Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class EscalationPolicyEnv(HealthcareRLEnvironment):
    ESCALATIONS = ["no_escalation", "provider_escalate", "specialist_escalate", "ed_referral", "urgent_care"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ESCALATIONS))
        self.patient_cases = []
        self.escalations = []
        self.appropriate_escalations = 0
    def _initialize_state(self) -> np.ndarray:
        self.patient_cases = [{"severity": self.np_random.uniform(0, 1), "risk": self.np_random.uniform(0, 1)} for _ in range(10)]
        self.escalations = []
        self.appropriate_escalations = 0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            len(self.patient_cases) / 15.0,
            len(self.escalations) / 10.0,
            np.mean([c["severity"] for c in self.patient_cases[:5]]) if self.patient_cases else 0.0,
            self.appropriate_escalations / 10.0,
            *[0.0] * 11
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        escalation = self.ESCALATIONS[action]
        if self.patient_cases:
            case = self.patient_cases.pop(0)
            self.escalations.append({**case, "escalation": escalation})
            if (case["severity"] > 0.7 and escalation in ["ed_referral", "urgent_care"]) or (case["severity"] > 0.5 and escalation in ["provider_escalate", "specialist_escalate"]):
                self.appropriate_escalations += 1
        return {"escalation": escalation}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.appropriate_escalations / 10.0
        efficiency_score = 1.0 - len(self.patient_cases) / 15.0
        financial_score = self.appropriate_escalations / 10.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.appropriate_escalations / 10.0,
            RewardComponent.RISK_PENALTY: len([c for c in self.patient_cases if c["severity"] > 0.8]) / 10.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 25 or len(self.patient_cases) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"appropriate_escalations": self.appropriate_escalations},
            operational_efficiency={"cases_processed": len(self.escalations)},
            financial_metrics={"escalation_cost": len(self.escalations) * 200},
            patient_satisfaction=self.appropriate_escalations / 10.0,
            risk_score=len([c for c in self.patient_cases if c["severity"] > 0.8]) / 10.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

