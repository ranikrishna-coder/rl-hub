"""Enrollment Funnel Optimization Environment - Optimizes enrollment funnel (Veeva, IQVIA)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class EnrollmentFunnelOptimizationEnv(HealthcareRLEnvironment):
    ACTIONS = ["screen_patient", "enroll_patient", "optimize_criteria", "expand_outreach", "defer", "exclude"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.enrollment_queue = []
        self.enrolled_patients = []
        self.enrollment_rate = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.enrollment_queue = [{"patient": self.patient_generator.generate_patient(), "eligibility_score": self.np_random.uniform(0.4, 1.0), "enrollment_probability": self.np_random.uniform(0.3, 0.9), "funnel_stage": self.np_random.choice(["screening", "consent", "baseline"])} for _ in range(15)]
        self.enrolled_patients = []
        self.enrollment_rate = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.enrollment_queue) / 20.0
        state[1] = len(self.enrolled_patients) / 20.0
        if self.enrollment_queue:
            state[2] = self.enrollment_queue[0]["eligibility_score"]
            state[3] = self.enrollment_queue[0]["enrollment_probability"]
            state[4] = 1.0 if self.enrollment_queue[0]["funnel_stage"] == "screening" else (0.5 if self.enrollment_queue[0]["funnel_stage"] == "consent" else 0.0)
        state[5] = self.enrollment_rate
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.enrollment_queue:
            patient = self.enrollment_queue.pop(0)
            if action_name == "screen_patient":
                if patient["eligibility_score"] > 0.6:
                    patient["funnel_stage"] = "consent"
                    patient["enrollment_probability"] = min(1.0, patient["enrollment_probability"] + 0.1)
                    self.enrollment_queue.insert(0, patient)
            elif action_name == "enroll_patient":
                enrolled = self.np_random.random() < patient["enrollment_probability"]
                if enrolled:
                    self.enrolled_patients.append({**patient, "status": "enrolled"})
                    self.enrollment_rate = min(1.0, self.enrollment_rate + 0.1)
            elif action_name == "optimize_criteria":
                patient["eligibility_score"] = min(1.0, patient["eligibility_score"] + 0.15)
                patient["enrollment_probability"] = min(1.0, patient["enrollment_probability"] + 0.1)
                self.enrollment_queue.insert(0, patient)
            elif action_name == "expand_outreach":
                patient["enrollment_probability"] = min(1.0, patient["enrollment_probability"] + 0.2)
                self.enrollment_queue.insert(0, patient)
            elif action_name == "exclude":
                self.enrolled_patients.append({**patient, "status": "excluded"})
            elif action_name == "defer":
                self.enrollment_queue.append(patient)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.enrollment_rate
        efficiency_score = len(self.enrolled_patients) / 20.0
        financial_score = len(self.enrolled_patients) / 20.0
        risk_penalty = len([p for p in self.enrollment_queue if p["eligibility_score"] < 0.5]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.enrollment_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.enrollment_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"enrollment_rate": self.enrollment_rate, "low_eligibility_waiting": len([p for p in self.enrollment_queue if p["eligibility_score"] < 0.5])},
            operational_efficiency={"queue_length": len(self.enrollment_queue), "patients_enrolled": len(self.enrolled_patients)},
            financial_metrics={"enrolled_count": len(self.enrolled_patients)},
            patient_satisfaction=1.0 - len(self.enrollment_queue) / 20.0,
            risk_score=len([p for p in self.enrollment_queue if p["eligibility_score"] < 0.5]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

