"""Patient Financial Counseling Environment - Provides financial counseling (Change Healthcare)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class PatientFinancialCounselingEnv(HealthcareRLEnvironment):
    ACTIONS = ["provide_counseling", "payment_plan_setup", "financial_assistance", "defer", "escalate", "self_pay_option"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.counseling_queue = []
        self.counseled_patients = []
        self.payment_compliance = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.counseling_queue = [{"patient": self.patient_generator.generate_patient(), "financial_burden": self.np_random.uniform(0, 1), "payment_capacity": self.np_random.uniform(0.2, 1.0), "counseling_need": self.np_random.uniform(0.4, 1.0)} for _ in range(15)]
        self.counseled_patients = []
        self.payment_compliance = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.counseling_queue) / 20.0
        state[1] = len(self.counseled_patients) / 20.0
        if self.counseling_queue:
            state[2] = self.counseling_queue[0]["financial_burden"]
            state[3] = self.counseling_queue[0]["payment_capacity"]
            state[4] = self.counseling_queue[0]["counseling_need"]
        state[5] = self.payment_compliance
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.counseling_queue:
            patient = self.counseling_queue.pop(0)
            if action_name == "provide_counseling":
                patient["payment_capacity"] = min(1.0, patient["payment_capacity"] + 0.1)
                patient["financial_burden"] = max(0, patient["financial_burden"] - 0.1)
                self.counseled_patients.append({**patient, "counseling": "provided"})
                self.payment_compliance = min(1.0, self.payment_compliance + 0.08)
            elif action_name == "payment_plan_setup":
                patient["payment_capacity"] = min(1.0, patient["payment_capacity"] + 0.15)
                patient["financial_burden"] = max(0, patient["financial_burden"] - 0.15)
                self.counseled_patients.append({**patient, "counseling": "payment_plan"})
                self.payment_compliance = min(1.0, self.payment_compliance + 0.12)
            elif action_name == "financial_assistance":
                patient["payment_capacity"] = min(1.0, patient["payment_capacity"] + 0.2)
                patient["financial_burden"] = max(0, patient["financial_burden"] - 0.25)
                self.counseled_patients.append({**patient, "counseling": "assistance"})
                self.payment_compliance = min(1.0, self.payment_compliance + 0.15)
            elif action_name == "self_pay_option":
                patient["payment_capacity"] = min(1.0, patient["payment_capacity"] + 0.1)
                self.counseled_patients.append({**patient, "counseling": "self_pay"})
                self.payment_compliance = min(1.0, self.payment_compliance + 0.1)
            elif action_name == "escalate":
                patient["payment_capacity"] = min(1.0, patient["payment_capacity"] + 0.25)
                patient["financial_burden"] = max(0, patient["financial_burden"] - 0.2)
                self.counseled_patients.append({**patient, "counseling": "escalated"})
                self.payment_compliance = min(1.0, self.payment_compliance + 0.18)
            elif action_name == "defer":
                self.counseling_queue.append(patient)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.payment_compliance
        efficiency_score = len(self.counseled_patients) / 20.0
        financial_score = self.payment_compliance
        risk_penalty = len([p for p in self.counseling_queue if p["financial_burden"] > 0.8]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.payment_compliance,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.counseling_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"payment_compliance": self.payment_compliance, "high_burden_waiting": len([p for p in self.counseling_queue if p["financial_burden"] > 0.8])},
            operational_efficiency={"queue_length": len(self.counseling_queue), "patients_counseled": len(self.counseled_patients)},
            financial_metrics={"payment_compliance": self.payment_compliance},
            patient_satisfaction=self.payment_compliance,
            risk_score=len([p for p in self.counseling_queue if p["financial_burden"] > 0.8]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

