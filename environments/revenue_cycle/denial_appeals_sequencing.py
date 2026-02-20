"""Denial Appeals Sequencing Environment - Sequences denial appeals (Change Healthcare)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class DenialAppealsSequencingEnv(HealthcareRLEnvironment):
    ACTIONS = ["file_appeal", "expedite_appeal", "provide_evidence", "escalate_appeal", "defer", "accept_denial"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.appeals_queue = []
        self.successful_appeals = []
        self.appeal_success_rate = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.appeals_queue = [{"patient": self.patient_generator.generate_patient(), "denied_amount": self.np_random.uniform(500, 5000), "appeal_strength": self.np_random.uniform(0.3, 0.9), "days_since_denial": self.np_random.uniform(0, 60), "success_probability": self.np_random.uniform(0.2, 0.8)} for _ in range(15)]
        self.successful_appeals = []
        self.appeal_success_rate = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.appeals_queue) / 20.0
        state[1] = len(self.successful_appeals) / 20.0
        if self.appeals_queue:
            state[2] = self.appeals_queue[0]["denied_amount"] / 5000.0
            state[3] = self.appeals_queue[0]["appeal_strength"]
            state[4] = self.appeals_queue[0]["success_probability"]
            state[5] = self.appeals_queue[0]["days_since_denial"] / 90.0
        state[6] = self.appeal_success_rate
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.appeals_queue:
            appeal = self.appeals_queue.pop(0)
            if action_name == "file_appeal":
                success = self.np_random.random() < appeal["success_probability"]
                if success:
                    self.successful_appeals.append({**appeal, "status": "successful"})
                    self.appeal_success_rate = min(1.0, self.appeal_success_rate + 0.1)
            elif action_name == "expedite_appeal":
                success = self.np_random.random() < min(1.0, appeal["success_probability"] + 0.1)
                if success:
                    self.successful_appeals.append({**appeal, "status": "successful", "expedited": True})
                    self.appeal_success_rate = min(1.0, self.appeal_success_rate + 0.12)
            elif action_name == "provide_evidence":
                appeal["success_probability"] = min(1.0, appeal["success_probability"] + 0.2)
                appeal["appeal_strength"] = min(1.0, appeal["appeal_strength"] + 0.15)
                self.appeals_queue.insert(0, appeal)
            elif action_name == "escalate_appeal":
                success = self.np_random.random() < min(1.0, appeal["success_probability"] + 0.25)
                if success:
                    self.successful_appeals.append({**appeal, "status": "successful", "escalated": True})
                    self.appeal_success_rate = min(1.0, self.appeal_success_rate + 0.15)
            elif action_name == "accept_denial":
                self.successful_appeals.append({**appeal, "status": "accepted_denial"})
            elif action_name == "defer":
                appeal["days_since_denial"] += 7.0
                self.appeals_queue.append(appeal)
        for appeal in self.appeals_queue:
            appeal["days_since_denial"] += 1.0
            appeal["success_probability"] = max(0.1, appeal["success_probability"] - 0.005)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.appeal_success_rate
        efficiency_score = len(self.successful_appeals) / 20.0
        financial_score = self.appeal_success_rate
        risk_penalty = len([a for a in self.appeals_queue if a["days_since_denial"] > 60 and a["success_probability"] < 0.3]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.appeals_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.appeals_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"appeal_success_rate": self.appeal_success_rate, "old_appeals_waiting": len([a for a in self.appeals_queue if a["days_since_denial"] > 60])},
            operational_efficiency={"queue_length": len(self.appeals_queue), "successful_appeals": len(self.successful_appeals)},
            financial_metrics={"success_rate": self.appeal_success_rate},
            patient_satisfaction=1.0 - len(self.appeals_queue) / 20.0,
            risk_score=len([a for a in self.appeals_queue if a["days_since_denial"] > 60 and a["success_probability"] < 0.3]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

