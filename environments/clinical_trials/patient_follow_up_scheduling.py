"""Patient Follow-Up Scheduling Environment - Schedules patient follow-ups (Veeva, IQVIA)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class PatientFollowUpSchedulingEnv(HealthcareRLEnvironment):
    ACTIONS = ["schedule_followup", "expedite_followup", "batch_schedule", "reschedule", "defer", "cancel"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.followup_queue = []
        self.scheduled_followups = []
        self.followup_compliance = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.followup_queue = [{"patient": self.patient_generator.generate_patient(), "days_since_last_visit": self.np_random.uniform(0, 90), "compliance_risk": self.np_random.uniform(0, 0.6), "visit_importance": self.np_random.uniform(0.4, 1.0)} for _ in range(15)]
        self.scheduled_followups = []
        self.followup_compliance = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.followup_queue) / 20.0
        state[1] = len(self.scheduled_followups) / 20.0
        if self.followup_queue:
            state[2] = self.followup_queue[0]["days_since_last_visit"] / 90.0
            state[3] = self.followup_queue[0]["compliance_risk"]
            state[4] = self.followup_queue[0]["visit_importance"]
        state[5] = self.followup_compliance
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.followup_queue:
            followup = self.followup_queue.pop(0)
            if action_name == "schedule_followup":
                self.scheduled_followups.append({**followup, "status": "scheduled"})
                self.followup_compliance = min(1.0, self.followup_compliance + 0.1)
            elif action_name == "expedite_followup":
                self.scheduled_followups.append({**followup, "status": "expedited"})
                self.followup_compliance = min(1.0, self.followup_compliance + 0.12)
            elif action_name == "batch_schedule":
                similar = [f for f in self.followup_queue if abs(f["days_since_last_visit"] - followup["days_since_last_visit"]) < 7][:3]
                self.scheduled_followups.append({**followup, "status": "batch_scheduled"})
                for f in similar:
                    self.scheduled_followups.append({**f, "status": "batch_scheduled"})
                    if f in self.followup_queue:
                        self.followup_queue.remove(f)
                self.followup_compliance = min(1.0, self.followup_compliance + 0.15)
            elif action_name == "reschedule":
                followup["days_since_last_visit"] += 7.0
                self.followup_queue.append(followup)
            elif action_name == "cancel":
                self.scheduled_followups.append({**followup, "status": "cancelled"})
            elif action_name == "defer":
                followup["days_since_last_visit"] += 7.0
                followup["compliance_risk"] = min(1.0, followup["compliance_risk"] + 0.05)
                self.followup_queue.append(followup)
        for followup in self.followup_queue:
            followup["days_since_last_visit"] += 1.0
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.followup_compliance
        efficiency_score = len(self.scheduled_followups) / 20.0
        financial_score = len(self.scheduled_followups) / 20.0
        risk_penalty = len([f for f in self.followup_queue if f["compliance_risk"] > 0.7 and f["days_since_last_visit"] > 60]) * 0.3
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.followup_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.followup_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"followup_compliance": self.followup_compliance, "high_risk_waiting": len([f for f in self.followup_queue if f["compliance_risk"] > 0.7])},
            operational_efficiency={"queue_length": len(self.followup_queue), "followups_scheduled": len(self.scheduled_followups)},
            financial_metrics={"scheduled_count": len(self.scheduled_followups)},
            patient_satisfaction=1.0 - len(self.followup_queue) / 20.0,
            risk_score=len([f for f in self.followup_queue if f["compliance_risk"] > 0.7 and f["days_since_last_visit"] > 60]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

