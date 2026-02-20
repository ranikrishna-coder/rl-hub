"""Readmission Risk Mitigation Environment - Mitigates readmission risk (Health Catalyst, Innovaccer)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class ReadmissionRiskMitigationEnv(HealthcareRLEnvironment):
    ACTIONS = ["discharge_planning", "medication_reconciliation", "followup_scheduling", "care_transition", "defer", "escalate"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.mitigation_queue = []
        self.mitigated_patients = []
        self.readmission_risk_reduction = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.mitigation_queue = [{"patient": self.patient_generator.generate_patient(), "readmission_risk": self.np_random.uniform(0.3, 1.0), "days_to_discharge": self.np_random.uniform(0, 7), "interventions_applied": 0} for _ in range(15)]
        self.mitigated_patients = []
        self.readmission_risk_reduction = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.mitigation_queue) / 20.0
        state[1] = len(self.mitigated_patients) / 20.0
        if self.mitigation_queue:
            state[2] = self.mitigation_queue[0]["readmission_risk"]
            state[3] = self.mitigation_queue[0]["days_to_discharge"] / 7.0
        state[4] = self.readmission_risk_reduction
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.mitigation_queue:
            patient = self.mitigation_queue.pop(0)
            if action_name == "discharge_planning":
                patient["readmission_risk"] = max(0, patient["readmission_risk"] - 0.15)
                patient["interventions_applied"] += 1
                self.mitigated_patients.append({**patient, "intervention": "discharge_planning"})
                self.readmission_risk_reduction = min(1.0, self.readmission_risk_reduction + 0.1)
            elif action_name == "medication_reconciliation":
                patient["readmission_risk"] = max(0, patient["readmission_risk"] - 0.12)
                patient["interventions_applied"] += 1
                self.mitigated_patients.append({**patient, "intervention": "medication"})
                self.readmission_risk_reduction = min(1.0, self.readmission_risk_reduction + 0.08)
            elif action_name == "followup_scheduling":
                patient["readmission_risk"] = max(0, patient["readmission_risk"] - 0.1)
                patient["interventions_applied"] += 1
                self.mitigated_patients.append({**patient, "intervention": "followup"})
                self.readmission_risk_reduction = min(1.0, self.readmission_risk_reduction + 0.06)
            elif action_name == "care_transition":
                patient["readmission_risk"] = max(0, patient["readmission_risk"] - 0.2)
                patient["interventions_applied"] += 1
                self.mitigated_patients.append({**patient, "intervention": "transition"})
                self.readmission_risk_reduction = min(1.0, self.readmission_risk_reduction + 0.15)
            elif action_name == "escalate":
                patient["readmission_risk"] = max(0, patient["readmission_risk"] - 0.25)
                patient["interventions_applied"] += 1
                self.mitigated_patients.append({**patient, "intervention": "escalated"})
                self.readmission_risk_reduction = min(1.0, self.readmission_risk_reduction + 0.2)
            elif action_name == "defer":
                self.mitigation_queue.append(patient)
                patient["days_to_discharge"] = max(0, patient["days_to_discharge"] - 1)
        for patient in self.mitigation_queue:
            patient["days_to_discharge"] = max(0, patient["days_to_discharge"] - 1)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.readmission_risk_reduction
        efficiency_score = len(self.mitigated_patients) / 20.0
        financial_score = len(self.mitigated_patients) / 20.0
        risk_penalty = len([p for p in self.mitigation_queue if p["readmission_risk"] > 0.8 and p["days_to_discharge"] < 1]) * 0.3
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.mitigation_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.mitigation_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"readmission_risk_reduction": self.readmission_risk_reduction, "high_risk_waiting": len([p for p in self.mitigation_queue if p["readmission_risk"] > 0.8])},
            operational_efficiency={"queue_length": len(self.mitigation_queue), "patients_mitigated": len(self.mitigated_patients)},
            financial_metrics={"mitigated_count": len(self.mitigated_patients)},
            patient_satisfaction=1.0 - len(self.mitigation_queue) / 20.0,
            risk_score=len([p for p in self.mitigation_queue if p["readmission_risk"] > 0.8 and p["days_to_discharge"] < 1]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

