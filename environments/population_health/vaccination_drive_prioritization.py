"""Vaccination Drive Prioritization Environment - Prioritizes vaccination drives (Health Catalyst, Innovaccer)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class VaccinationDrivePrioritizationEnv(HealthcareRLEnvironment):
    ACTIONS = ["prioritize_high_risk", "prioritize_elderly", "prioritize_children", "batch_vaccinate", "defer", "mobile_clinic"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.vaccination_queue = []
        self.vaccinated_patients = []
        self.vaccination_coverage = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.vaccination_queue = [{"patient": self.patient_generator.generate_patient(), "risk_level": self.np_random.uniform(0, 1), "age_group": self.np_random.choice(["elderly", "adult", "child"]), "priority": self.np_random.uniform(0, 1)} for _ in range(15)]
        self.vaccinated_patients = []
        self.vaccination_coverage = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.vaccination_queue) / 20.0
        state[1] = len(self.vaccinated_patients) / 20.0
        if self.vaccination_queue:
            state[2] = self.vaccination_queue[0]["risk_level"]
            state[3] = self.vaccination_queue[0]["priority"]
            state[4] = 1.0 if self.vaccination_queue[0]["age_group"] == "elderly" else (0.5 if self.vaccination_queue[0]["age_group"] == "adult" else 0.0)
        state[5] = self.vaccination_coverage
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.vaccination_queue:
            if action_name == "prioritize_high_risk":
                high_risk = [p for p in self.vaccination_queue if p["risk_level"] > 0.7][:3]
                for p in high_risk:
                    self.vaccinated_patients.append({**p, "vaccinated": True})
                    if p in self.vaccination_queue:
                        self.vaccination_queue.remove(p)
                    self.vaccination_coverage = min(1.0, self.vaccination_coverage + 0.1)
            elif action_name == "prioritize_elderly":
                elderly = [p for p in self.vaccination_queue if p["age_group"] == "elderly"][:3]
                for p in elderly:
                    self.vaccinated_patients.append({**p, "vaccinated": True})
                    if p in self.vaccination_queue:
                        self.vaccination_queue.remove(p)
                    self.vaccination_coverage = min(1.0, self.vaccination_coverage + 0.1)
            elif action_name == "prioritize_children":
                children = [p for p in self.vaccination_queue if p["age_group"] == "child"][:3]
                for p in children:
                    self.vaccinated_patients.append({**p, "vaccinated": True})
                    if p in self.vaccination_queue:
                        self.vaccination_queue.remove(p)
                    self.vaccination_coverage = min(1.0, self.vaccination_coverage + 0.1)
            elif action_name == "batch_vaccinate":
                batch = self.vaccination_queue[:5]
                for p in batch:
                    self.vaccinated_patients.append({**p, "vaccinated": True})
                    if p in self.vaccination_queue:
                        self.vaccination_queue.remove(p)
                    self.vaccination_coverage = min(1.0, self.vaccination_coverage + 0.1)
            elif action_name == "mobile_clinic":
                mobile = self.vaccination_queue[:8]
                for p in mobile:
                    self.vaccinated_patients.append({**p, "vaccinated": True, "method": "mobile"})
                    if p in self.vaccination_queue:
                        self.vaccination_queue.remove(p)
                    self.vaccination_coverage = min(1.0, self.vaccination_coverage + 0.1)
            elif action_name == "defer":
                pass
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.vaccination_coverage
        efficiency_score = len(self.vaccinated_patients) / 20.0
        financial_score = len(self.vaccinated_patients) / 20.0
        risk_penalty = len([p for p in self.vaccination_queue if p["risk_level"] > 0.8]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.vaccination_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.vaccination_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"vaccination_coverage": self.vaccination_coverage, "high_risk_waiting": len([p for p in self.vaccination_queue if p["risk_level"] > 0.8])},
            operational_efficiency={"queue_length": len(self.vaccination_queue), "patients_vaccinated": len(self.vaccinated_patients)},
            financial_metrics={"vaccinated_count": len(self.vaccinated_patients)},
            patient_satisfaction=1.0 - len(self.vaccination_queue) / 20.0,
            risk_score=len([p for p in self.vaccination_queue if p["risk_level"] > 0.8]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

