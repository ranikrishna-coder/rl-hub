"""Chronic Disease Management Environment - Manages long-term chronic conditions"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class ChronicDiseaseManagementEnv(HealthcareRLEnvironment):
    ACTIONS = ["medication_adjust", "lifestyle_counseling", "monitoring", "specialist_referral", "education", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(18,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.current_patient = None
        self.management_plan = []
        self.disease_control_score = 0.5
        self.time_in_care = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.current_patient = self.patient_generator.generate_patient()
        self.management_plan = []
        self.disease_control_score = 0.5
        self.time_in_care = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        if not self.current_patient:
            return np.zeros(18, dtype=np.float32)
        p = self.current_patient
        return np.array([
            p.age / 100.0, self.disease_control_score, len(p.conditions) / 5.0,
            p.risk_score, len(p.medications) / 10.0, self.time_in_care / 365.0,
            1.0 if "diabetes" in p.conditions else 0.0,
            1.0 if "hypertension" in p.conditions else 0.0,
            1.0 if "copd" in p.conditions else 0.0,
            p.vitals.get("bp_systolic", 120) / 200.0,
            p.lab_results.get("glucose", 100) / 200.0,
            p.lab_results.get("creatinine", 1.0) / 2.0,
            len(self.management_plan) / 10.0,
            1.0 if "lifestyle_counseling" in self.management_plan else 0.0,
            1.0 if "medication_adjust" in self.management_plan else 0.0,
            p.readmission_risk, len(p.comorbidities) / 5.0,
            p.social_determinants.get("health_literacy", 0.5)
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        self.management_plan.append(action_name)
        self.time_in_care += 30.0  # 30 days per step
        if action_name == "medication_adjust" and self.current_patient:
            self.current_patient.risk_score = max(0, self.current_patient.risk_score - 0.05)
            self.disease_control_score = min(1.0, self.disease_control_score + 0.1)
        elif action_name == "lifestyle_counseling":
            self.disease_control_score = min(1.0, self.disease_control_score + 0.08)
        elif action_name == "monitoring":
            self.disease_control_score = min(1.0, self.disease_control_score + 0.02)
        if self.current_patient:
            self.current_patient = self.patient_generator.evolve_patient(self.current_patient, 30.0)
        return {"action": action_name, "control_score": self.disease_control_score}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        if not self.current_patient:
            return {k: 0.0 for k in RewardComponent}
        p = self.current_patient
        clinical_score = self.disease_control_score
        efficiency_score = 1.0 - len(self.management_plan) / 20.0 if self.disease_control_score > 0.7 else 0.5
        financial_score = 1.0 / (1.0 + len(self.management_plan) * 150 / 10000.0)
        risk_penalty = p.risk_score if p.risk_score > 0.5 else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.disease_control_score,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 12 or (self.disease_control_score > 0.8 and self.current_patient and self.current_patient.risk_score < 0.3)
    def _get_kpis(self) -> KPIMetrics:
        if not self.current_patient:
            return KPIMetrics({}, {}, {}, 0.0, 0.0, 0.0, self.time_step)
        p = self.current_patient
        return KPIMetrics(
            clinical_outcomes={"disease_control": self.disease_control_score, "risk_score": p.risk_score},
            operational_efficiency={"management_plan_items": len(self.management_plan), "time_in_care": self.time_in_care},
            financial_metrics={"management_cost": len(self.management_plan) * 150},
            patient_satisfaction=self.disease_control_score,
            risk_score=p.risk_score,
            compliance_score=1.0,
            timestamp=self.time_step
        )

