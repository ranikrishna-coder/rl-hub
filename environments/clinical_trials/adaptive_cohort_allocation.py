"""Adaptive Cohort Allocation Environment - Allocates adaptive cohorts (Veeva, IQVIA)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class AdaptiveCohortAllocationEnv(HealthcareRLEnvironment):
    ACTIONS = ["allocate_cohort_a", "allocate_cohort_b", "allocate_control", "adaptive_reallocate", "defer", "exclude"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.allocation_queue = []
        self.allocated_patients = []
        self.cohort_balance = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.allocation_queue = [{"patient": self.patient_generator.generate_patient(), "eligibility_score": self.np_random.uniform(0.5, 1.0), "biomarker_match": self.np_random.uniform(0, 1), "cohort_preference": self.np_random.choice(["A", "B", "control"])} for _ in range(15)]
        self.allocated_patients = []
        self.cohort_balance = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.allocation_queue) / 20.0
        state[1] = len(self.allocated_patients) / 20.0
        if self.allocation_queue:
            state[2] = self.allocation_queue[0]["eligibility_score"]
            state[3] = self.allocation_queue[0]["biomarker_match"]
        state[4] = self.cohort_balance
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.allocation_queue:
            patient = self.allocation_queue.pop(0)
            if action_name == "allocate_cohort_a":
                self.allocated_patients.append({**patient, "cohort": "A"})
                self.cohort_balance = min(1.0, self.cohort_balance + 0.1)
            elif action_name == "allocate_cohort_b":
                self.allocated_patients.append({**patient, "cohort": "B"})
                self.cohort_balance = min(1.0, self.cohort_balance + 0.1)
            elif action_name == "allocate_control":
                self.allocated_patients.append({**patient, "cohort": "control"})
                self.cohort_balance = min(1.0, self.cohort_balance + 0.1)
            elif action_name == "adaptive_reallocate":
                # Reallocate based on interim results
                patient["biomarker_match"] = min(1.0, patient["biomarker_match"] + 0.2)
                self.allocated_patients.append({**patient, "cohort": "adaptive"})
                self.cohort_balance = min(1.0, self.cohort_balance + 0.15)
            elif action_name == "exclude":
                self.allocated_patients.append({**patient, "cohort": "excluded"})
            elif action_name == "defer":
                self.allocation_queue.append(patient)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.cohort_balance
        efficiency_score = len(self.allocated_patients) / 20.0
        financial_score = len(self.allocated_patients) / 20.0
        risk_penalty = len([p for p in self.allocation_queue if p["eligibility_score"] < 0.6]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.allocation_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.allocation_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"cohort_balance": self.cohort_balance, "low_eligibility_waiting": len([p for p in self.allocation_queue if p["eligibility_score"] < 0.6])},
            operational_efficiency={"queue_length": len(self.allocation_queue), "patients_allocated": len(self.allocated_patients)},
            financial_metrics={"allocated_count": len(self.allocated_patients)},
            patient_satisfaction=1.0 - len(self.allocation_queue) / 20.0,
            risk_score=len([p for p in self.allocation_queue if p["eligibility_score"] < 0.6]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

