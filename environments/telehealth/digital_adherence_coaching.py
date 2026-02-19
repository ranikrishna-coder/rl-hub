"""Digital Adherence Coaching Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class DigitalAdherenceCoachingEnv(HealthcareRLEnvironment):
    INTERVENTIONS = ["medication_reminder", "lifestyle_coaching", "symptom_tracking", "education", "no_intervention"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.INTERVENTIONS))
        self.patients = []
        self.interventions_applied = []
        self.adherence_score = 0.6
    def _initialize_state(self) -> np.ndarray:
        self.patients = [{"adherence": self.np_random.uniform(0.4, 0.8), "engagement": self.np_random.uniform(0.3, 0.9)} for _ in range(8)]
        self.interventions_applied = []
        self.adherence_score = 0.6
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            len(self.patients) / 10.0,
            len(self.interventions_applied) / 10.0,
            self.adherence_score,
            np.mean([p["adherence"] for p in self.patients[:5]]) if self.patients else 0.0,
            *[0.0] * 11
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        intervention = self.INTERVENTIONS[action]
        if self.patients and intervention != "no_intervention":
            patient = self.patients[0]
            self.interventions_applied.append({**patient, "intervention": intervention})
            patient["adherence"] = min(1.0, patient["adherence"] + 0.1)
            self.adherence_score = np.mean([p["adherence"] for p in self.patients])
        return {"intervention": intervention}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.adherence_score
        efficiency_score = len(self.interventions_applied) / 10.0
        financial_score = self.adherence_score * 0.9
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.adherence_score,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 25 or (self.adherence_score > 0.85 and len(self.patients) == 0)
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"adherence_score": self.adherence_score},
            operational_efficiency={"interventions_applied": len(self.interventions_applied)},
            financial_metrics={"coaching_cost": len(self.interventions_applied) * 50},
            patient_satisfaction=self.adherence_score,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

