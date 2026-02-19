"""Drug Dosage Trial Sequencing Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class DrugDosageTrialSequencingEnv(HealthcareRLEnvironment):
    DOSAGES = ["dose_1", "dose_2", "dose_3", "escalate", "de_escalate", "maintain"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.DOSAGES))
        self.current_dose = 1
        self.efficacy = 0.4
        self.safety = 0.9
        self.patients_treated = 0
    def _initialize_state(self) -> np.ndarray:
        self.current_dose = 1
        self.efficacy = 0.4
        self.safety = 0.9
        self.patients_treated = 0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            self.current_dose / 3.0,
            self.efficacy,
            self.safety,
            self.patients_treated / 50.0,
            *[0.0] * 11
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        dosage = self.DOSAGES[action]
        if dosage == "escalate" or dosage == "dose_2":
            self.current_dose = min(3, self.current_dose + 1)
            self.efficacy = min(1.0, self.efficacy + 0.15)
            self.safety = max(0, self.safety - 0.1)
        elif dosage == "de_escalate":
            self.current_dose = max(1, self.current_dose - 1)
            self.safety = min(1.0, self.safety + 0.1)
            self.efficacy = max(0, self.efficacy - 0.1)
        self.patients_treated += 1
        return {"dosage": dosage}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.efficacy * self.safety
        efficiency_score = self.patients_treated / 50.0
        financial_score = self.efficacy
        risk_penalty = 1.0 - self.safety if self.safety < 0.7 else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.efficacy,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 30 or (self.efficacy > 0.8 and self.safety > 0.75)
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"efficacy": self.efficacy, "safety": self.safety},
            operational_efficiency={"patients_treated": self.patients_treated},
            financial_metrics={"trial_value": self.efficacy * 100000},
            patient_satisfaction=self.efficacy,
            risk_score=1.0 - self.safety,
            compliance_score=1.0,
            timestamp=self.time_step
        )

