"""Pre-Authorization Workflow Environment - Manages pre-authorization workflow (Change Healthcare)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class PreAuthorizationWorkflowEnv(HealthcareRLEnvironment):
    ACTIONS = ["submit_authorization", "expedite_authorization", "provide_additional_info", "appeal_denial", "defer", "bypass"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.auth_queue = []
        self.approved_auths = []
        self.approval_rate = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.auth_queue = [{"patient": self.patient_generator.generate_patient(), "procedure_cost": self.np_random.uniform(1000, 20000), "urgency": self.np_random.uniform(0, 1), "approval_probability": self.np_random.uniform(0.4, 0.95), "days_waiting": 0.0} for _ in range(15)]
        self.approved_auths = []
        self.approval_rate = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.auth_queue) / 20.0
        state[1] = len(self.approved_auths) / 20.0
        if self.auth_queue:
            state[2] = self.auth_queue[0]["procedure_cost"] / 20000.0
            state[3] = self.auth_queue[0]["urgency"]
            state[4] = self.auth_queue[0]["approval_probability"]
            state[5] = self.auth_queue[0]["days_waiting"] / 30.0
        state[6] = self.approval_rate
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.auth_queue:
            auth = self.auth_queue.pop(0)
            if action_name == "submit_authorization":
                approved = self.np_random.random() < auth["approval_probability"]
                if approved:
                    self.approved_auths.append({**auth, "status": "approved"})
                    self.approval_rate = min(1.0, self.approval_rate + 0.1)
                else:
                    auth["approval_probability"] = max(0.1, auth["approval_probability"] - 0.1)
                    self.auth_queue.append(auth)
            elif action_name == "expedite_authorization":
                approved = self.np_random.random() < min(1.0, auth["approval_probability"] + 0.15)
                if approved:
                    self.approved_auths.append({**auth, "status": "approved", "expedited": True})
                    self.approval_rate = min(1.0, self.approval_rate + 0.12)
            elif action_name == "provide_additional_info":
                auth["approval_probability"] = min(1.0, auth["approval_probability"] + 0.2)
                self.auth_queue.insert(0, auth)
            elif action_name == "appeal_denial":
                approved = self.np_random.random() < min(1.0, auth["approval_probability"] + 0.25)
                if approved:
                    self.approved_auths.append({**auth, "status": "appealed_approved"})
                    self.approval_rate = min(1.0, self.approval_rate + 0.15)
            elif action_name == "bypass":
                self.approved_auths.append({**auth, "status": "bypassed"})
            elif action_name == "defer":
                auth["days_waiting"] += 7.0
                self.auth_queue.append(auth)
        for auth in self.auth_queue:
            auth["days_waiting"] += 1.0
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.approval_rate
        efficiency_score = len(self.approved_auths) / 20.0
        financial_score = self.approval_rate
        risk_penalty = len([a for a in self.auth_queue if a["urgency"] > 0.8 and a["days_waiting"] > 14]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.auth_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.auth_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"approval_rate": self.approval_rate, "urgent_waiting": len([a for a in self.auth_queue if a["urgency"] > 0.8])},
            operational_efficiency={"queue_length": len(self.auth_queue), "auths_approved": len(self.approved_auths)},
            financial_metrics={"approval_rate": self.approval_rate},
            patient_satisfaction=1.0 - len(self.auth_queue) / 20.0,
            risk_score=len([a for a in self.auth_queue if a["urgency"] > 0.8 and a["days_waiting"] > 14]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

