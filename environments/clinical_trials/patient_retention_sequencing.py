"""Patient Retention Sequencing Environment - Sequences patient retention (Veeva, IQVIA)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class PatientRetentionSequencingEnv(HealthcareRLEnvironment):
    ACTIONS = ["retention_outreach", "incentive_program", "care_coordination", "reduce_burden", "defer", "escalate"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.retention_queue = []
        self.retained_patients = []
        self.retention_rate = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.retention_queue = [{"patient": self.patient_generator.generate_patient(), "retention_risk": self.np_random.uniform(0.3, 1.0), "engagement_level": self.np_random.uniform(0.2, 0.9), "days_since_contact": self.np_random.uniform(0, 60)} for _ in range(15)]
        self.retained_patients = []
        self.retention_rate = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.retention_queue) / 20.0
        state[1] = len(self.retained_patients) / 20.0
        if self.retention_queue:
            state[2] = self.retention_queue[0]["retention_risk"]
            state[3] = self.retention_queue[0]["engagement_level"]
            state[4] = self.retention_queue[0]["days_since_contact"] / 90.0
        state[5] = self.retention_rate
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.retention_queue:
            patient = self.retention_queue.pop(0)
            if action_name == "retention_outreach":
                patient["engagement_level"] = min(1.0, patient["engagement_level"] + 0.15)
                patient["retention_risk"] = max(0, patient["retention_risk"] - 0.1)
                self.retained_patients.append({**patient, "intervention": "outreach"})
                self.retention_rate = min(1.0, self.retention_rate + 0.1)
            elif action_name == "incentive_program":
                patient["engagement_level"] = min(1.0, patient["engagement_level"] + 0.2)
                patient["retention_risk"] = max(0, patient["retention_risk"] - 0.15)
                self.retained_patients.append({**patient, "intervention": "incentive"})
                self.retention_rate = min(1.0, self.retention_rate + 0.12)
            elif action_name == "care_coordination":
                patient["engagement_level"] = min(1.0, patient["engagement_level"] + 0.18)
                patient["retention_risk"] = max(0, patient["retention_risk"] - 0.12)
                self.retained_patients.append({**patient, "intervention": "coordination"})
                self.retention_rate = min(1.0, self.retention_rate + 0.1)
            elif action_name == "reduce_burden":
                patient["engagement_level"] = min(1.0, patient["engagement_level"] + 0.25)
                patient["retention_risk"] = max(0, patient["retention_risk"] - 0.2)
                self.retained_patients.append({**patient, "intervention": "burden_reduction"})
                self.retention_rate = min(1.0, self.retention_rate + 0.15)
            elif action_name == "escalate":
                patient["engagement_level"] = min(1.0, patient["engagement_level"] + 0.3)
                patient["retention_risk"] = max(0, patient["retention_risk"] - 0.25)
                self.retained_patients.append({**patient, "intervention": "escalated"})
                self.retention_rate = min(1.0, self.retention_rate + 0.18)
            elif action_name == "defer":
                patient["days_since_contact"] += 7.0
                patient["retention_risk"] = min(1.0, patient["retention_risk"] + 0.05)
                self.retention_queue.append(patient)
        for patient in self.retention_queue:
            patient["days_since_contact"] += 1.0
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.retention_rate
        efficiency_score = len(self.retained_patients) / 20.0
        financial_score = len(self.retained_patients) / 20.0
        risk_penalty = len([p for p in self.retention_queue if p["retention_risk"] > 0.8 and p["days_since_contact"] > 30]) * 0.3
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.retention_rate,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.retention_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"retention_rate": self.retention_rate, "high_risk_waiting": len([p for p in self.retention_queue if p["retention_risk"] > 0.8])},
            operational_efficiency={"queue_length": len(self.retention_queue), "patients_retained": len(self.retained_patients)},
            financial_metrics={"retained_count": len(self.retained_patients)},
            patient_satisfaction=self.retention_rate,
            risk_score=len([p for p in self.retention_queue if p["retention_risk"] > 0.8 and p["days_since_contact"] > 30]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

