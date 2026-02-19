"""Medication Dosing Optimization Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class MedicationDosingOptimizationEnv(HealthcareRLEnvironment):
    DOSES = ["low", "medium", "high", "adjust", "discontinue"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.DOSES))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.current_patient = None
        self.current_dose = "medium"
        self.dosing_history = []
    def _initialize_state(self) -> np.ndarray:
        self.current_patient = self.patient_generator.generate_patient()
        self.current_dose = "medium"
        self.dosing_history = []
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        if not self.current_patient:
            return np.zeros(15, dtype=np.float32)
        p = self.current_patient
        dose_enc = {"low": 0.33, "medium": 0.66, "high": 1.0}.get(self.current_dose, 0.5)
        return np.array([
            p.age / 100.0, p.risk_score, p.vitals.get("bp_systolic", 120) / 200.0,
            p.vitals.get("heart_rate", 72) / 150.0, p.lab_results.get("creatinine", 1.0) / 2.0,
            p.lab_results.get("glucose", 100) / 200.0, dose_enc, len(self.dosing_history) / 10.0,
            p.vitals.get("pain_score", 0) / 10.0, 1.0 if "diabetes" in p.conditions else 0.0,
            1.0 if "hypertension" in p.conditions else 0.0, p.readmission_risk,
            len(p.medications) / 5.0, self.current_patient.length_of_stay / 30.0,
            p.vitals.get("temperature", 98.6) / 105.0
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        dose = self.DOSES[action]
        self.dosing_history.append(dose)
        if dose != "adjust":
            self.current_dose = dose
        if dose == "high" and self.current_patient:
            self.current_patient.vitals["pain_score"] = max(0, self.current_patient.vitals["pain_score"] - 1.5)
            self.current_patient.risk_score = max(0, self.current_patient.risk_score - 0.1)
        elif dose == "low" and self.current_patient:
            self.current_patient.vitals["pain_score"] = min(10, self.current_patient.vitals["pain_score"] + 0.5)
        if self.current_patient:
            self.current_patient = self.patient_generator.evolve_patient(self.current_patient, 1.0)
        return {"dose": dose}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        if not self.current_patient:
            return {k: 0.0 for k in RewardComponent}
        p = self.current_patient
        clinical_score = 1.0 - p.risk_score
        efficiency_score = 1.0 - len(self.dosing_history) / 10.0 if p.risk_score < 0.3 else 0.5
        financial_score = 1.0 / (1.0 + len(self.dosing_history) * 50 / 1000.0)
        risk_penalty = p.risk_score if p.risk_score > 0.6 else 0.0
        compliance_penalty = 0.2 if self.current_dose == "high" and p.vitals.get("creatinine", 1.0) > 1.5 else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - p.vitals.get("pain_score", 0) / 10.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 20 or (self.current_patient and self.current_patient.risk_score < 0.2)
    def _get_kpis(self) -> KPIMetrics:
        if not self.current_patient:
            return KPIMetrics({}, {}, {}, 0.0, 0.0, 0.0, self.time_step)
        p = self.current_patient
        return KPIMetrics(
            clinical_outcomes={"risk_score": p.risk_score, "pain_score": p.vitals.get("pain_score", 0)},
            operational_efficiency={"dosing_adjustments": len(self.dosing_history)},
            financial_metrics={"medication_cost": len(self.dosing_history) * 50},
            patient_satisfaction=1.0 - p.vitals.get("pain_score", 0) / 10.0,
            risk_score=p.risk_score,
            compliance_score=1.0 - (0.2 if self.current_dose == "high" and p.lab_results.get("creatinine", 1.0) > 1.5 else 0.0),
            timestamp=self.time_step
        )

