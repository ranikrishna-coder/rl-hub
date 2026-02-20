"""High-Risk Patient Engagement Environment - Engages high-risk patients (Health Catalyst, Innovaccer)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class HighRiskPatientEngagementEnv(HealthcareRLEnvironment):
    ACTIONS = ["intensive_outreach", "care_coordination", "medication_adherence", "lifestyle_coaching", "defer", "escalate"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.engagement_queue = []
        self.engaged_patients = []
        self.engagement_rate = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.engagement_queue = [{"patient": self.patient_generator.generate_patient(), "risk_score": self.np_random.uniform(0.6, 1.0), "engagement_level": 0.0, "days_since_engagement": 0.0} for _ in range(15)]
        self.engaged_patients = []
        self.engagement_rate = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.engagement_queue) / 20.0
        state[1] = len(self.engaged_patients) / 20.0
        if self.engagement_queue:
            state[2] = self.engagement_queue[0]["risk_score"]
            state[3] = self.engagement_queue[0]["engagement_level"]
            state[4] = self.engagement_queue[0]["days_since_engagement"] / 90.0
        state[5] = self.engagement_rate
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.engagement_queue:
            patient = self.engagement_queue.pop(0)
            if action_name == "intensive_outreach":
                patient["engagement_level"] = min(1.0, patient["engagement_level"] + 0.3)
                self.engaged_patients.append({**patient, "intervention": "intensive"})
                self.engagement_rate = min(1.0, self.engagement_rate + 0.1)
            elif action_name == "care_coordination":
                patient["engagement_level"] = min(1.0, patient["engagement_level"] + 0.25)
                self.engaged_patients.append({**patient, "intervention": "coordination"})
                self.engagement_rate = min(1.0, self.engagement_rate + 0.08)
            elif action_name == "medication_adherence":
                patient["engagement_level"] = min(1.0, patient["engagement_level"] + 0.2)
                self.engaged_patients.append({**patient, "intervention": "medication"})
                self.engagement_rate = min(1.0, self.engagement_rate + 0.06)
            elif action_name == "lifestyle_coaching":
                patient["engagement_level"] = min(1.0, patient["engagement_level"] + 0.15)
                self.engaged_patients.append({**patient, "intervention": "lifestyle"})
                self.engagement_rate = min(1.0, self.engagement_rate + 0.05)
            elif action_name == "escalate":
                patient["engagement_level"] = min(1.0, patient["engagement_level"] + 0.35)
                self.engaged_patients.append({**patient, "intervention": "escalated"})
                self.engagement_rate = min(1.0, self.engagement_rate + 0.12)
            elif action_name == "defer":
                self.engagement_queue.append(patient)
                patient["days_since_engagement"] += 7.0
        for patient in self.engagement_queue:
            patient["days_since_engagement"] += 1.0
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.engagement_rate
        efficiency_score = len(self.engaged_patients) / 20.0
        financial_score = len(self.engaged_patients) / 20.0
        risk_penalty = len([p for p in self.engagement_queue if p["risk_score"] > 0.9 and p["days_since_engagement"] > 30.0]) * 0.3
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.engagement_rate,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.engagement_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"engagement_rate": self.engagement_rate, "high_risk_waiting": len([p for p in self.engagement_queue if p["risk_score"] > 0.9])},
            operational_efficiency={"queue_length": len(self.engagement_queue), "patients_engaged": len(self.engaged_patients)},
            financial_metrics={"engaged_count": len(self.engaged_patients)},
            patient_satisfaction=self.engagement_rate,
            risk_score=len([p for p in self.engagement_queue if p["risk_score"] > 0.9 and p["days_since_engagement"] > 30.0]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

