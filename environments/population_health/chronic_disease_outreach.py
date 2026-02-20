"""Chronic Disease Outreach Environment - Manages chronic disease outreach (Health Catalyst, Innovaccer)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class ChronicDiseaseOutreachEnv(HealthcareRLEnvironment):
    ACTIONS = ["phone_outreach", "text_outreach", "mail_outreach", "in_person_visit", "defer", "escalate"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.outreach_queue = []
        self.completed_outreach = []
        self.engagement_rate = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.outreach_queue = [{"patient": self.patient_generator.generate_patient(), "risk_level": self.np_random.uniform(0, 1), "disease_type": self.np_random.choice(["diabetes", "hypertension", "copd", "heart_failure"]), "days_since_last_contact": 0.0} for _ in range(15)]
        self.completed_outreach = []
        self.engagement_rate = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.outreach_queue) / 20.0
        state[1] = len(self.completed_outreach) / 20.0
        if self.outreach_queue:
            state[2] = self.outreach_queue[0]["risk_level"]
            state[3] = self.outreach_queue[0]["days_since_last_contact"] / 90.0
        state[4] = self.engagement_rate
        state[5] = np.mean([o["risk_level"] for o in self.outreach_queue[:5]]) if self.outreach_queue else 0.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.outreach_queue:
            outreach = self.outreach_queue.pop(0)
            if action_name in ["phone_outreach", "text_outreach", "mail_outreach", "in_person_visit"]:
                engagement = 0.3 if action_name == "phone_outreach" else (0.2 if action_name == "text_outreach" else (0.1 if action_name == "mail_outreach" else 0.5))
                self.completed_outreach.append({**outreach, "method": action_name, "engagement": engagement})
                self.engagement_rate = min(1.0, self.engagement_rate + engagement / 10.0)
            elif action_name == "escalate":
                self.completed_outreach.append({**outreach, "method": "escalated", "engagement": 0.4})
                self.engagement_rate = min(1.0, self.engagement_rate + 0.04)
            elif action_name == "defer":
                self.outreach_queue.append(outreach)
                outreach["days_since_last_contact"] += 7.0
        for outreach in self.outreach_queue:
            outreach["days_since_last_contact"] += 1.0
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = 1.0 - len([o for o in self.outreach_queue if o["risk_level"] > 0.8]) / 15.0
        efficiency_score = self.engagement_rate
        financial_score = len(self.completed_outreach) / 20.0
        risk_penalty = len([o for o in self.outreach_queue if o["risk_level"] > 0.9 and o["days_since_last_contact"] > 60.0]) * 0.2
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
        return self.time_step >= 50 or len(self.outreach_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"high_risk_waiting": len([o for o in self.outreach_queue if o["risk_level"] > 0.8]), "engagement_rate": self.engagement_rate},
            operational_efficiency={"queue_length": len(self.outreach_queue), "outreach_completed": len(self.completed_outreach)},
            financial_metrics={"completed_count": len(self.completed_outreach)},
            patient_satisfaction=self.engagement_rate,
            risk_score=len([o for o in self.outreach_queue if o["risk_level"] > 0.9 and o["days_since_last_contact"] > 60.0]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

