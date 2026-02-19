"""Readmission Reduction Environment - Reduces 30-day readmissions"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class ReadmissionReductionEnv(HealthcareRLEnvironment):
    INTERVENTIONS = ["discharge", "extended_monitoring", "home_health", "followup_appointment", "medication_review", "education"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.INTERVENTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.current_patient = None
        self.interventions_applied = []
        self.readmission_risk = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.current_patient = self.patient_generator.generate_patient()
        self.interventions_applied = []
        self.readmission_risk = self.current_patient.readmission_risk
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        if not self.current_patient:
            return np.zeros(17, dtype=np.float32)
        p = self.current_patient
        return np.array([
            p.age / 100.0, p.readmission_risk, len(p.conditions) / 5.0,
            len(p.comorbidities) / 5.0, len(p.medications) / 10.0,
            p.risk_score, p.length_of_stay / 30.0,
            1.0 if "diabetes" in p.conditions else 0.0,
            1.0 if "heart_failure" in p.conditions else 0.0,
            p.social_determinants.get("housing_stability", 0.5),
            p.social_determinants.get("food_security", 0.5),
            p.social_determinants.get("transportation", 0.5),
            len(self.interventions_applied) / 6.0,
            1.0 if "home_health" in self.interventions_applied else 0.0,
            1.0 if "followup_appointment" in self.interventions_applied else 0.0,
            1.0 if "medication_review" in self.interventions_applied else 0.0,
            self.readmission_risk
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        intervention = self.INTERVENTIONS[action]
        self.interventions_applied.append(intervention)
        if intervention == "home_health":
            self.readmission_risk = max(0, self.readmission_risk - 0.15)
        elif intervention == "followup_appointment":
            self.readmission_risk = max(0, self.readmission_risk - 0.1)
        elif intervention == "medication_review":
            self.readmission_risk = max(0, self.readmission_risk - 0.08)
        elif intervention == "education":
            self.readmission_risk = max(0, self.readmission_risk - 0.05)
        return {"intervention": intervention, "readmission_risk": self.readmission_risk}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = 1.0 - self.readmission_risk
        efficiency_score = 1.0 - len(self.interventions_applied) / 6.0 if self.readmission_risk < 0.2 else 0.5
        financial_score = 1.0 / (1.0 + len(self.interventions_applied) * 200 / 5000.0)
        risk_penalty = self.readmission_risk if self.readmission_risk > 0.3 else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - self.readmission_risk,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.INTERVENTIONS[self.action_space.sample()] == "discharge" if hasattr(self, 'action_space') else len(self.interventions_applied) >= 3 or self.readmission_risk < 0.15
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"readmission_risk": self.readmission_risk},
            operational_efficiency={"interventions_count": len(self.interventions_applied)},
            financial_metrics={"intervention_cost": len(self.interventions_applied) * 200},
            patient_satisfaction=1.0 - self.readmission_risk,
            risk_score=self.readmission_risk,
            compliance_score=1.0,
            timestamp=self.time_step
        )

