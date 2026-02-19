"""Radiology Scheduling Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class RadiologySchedulingEnv(HealthcareRLEnvironment):
    ACTIONS = ["schedule_morning", "schedule_afternoon", "schedule_evening", "reschedule", "cancel"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.appointments = []
        self.schedule = {"morning": [], "afternoon": [], "evening": []}
        self.utilization = {"morning": 0.0, "afternoon": 0.0, "evening": 0.0}
    def _initialize_state(self) -> np.ndarray:
        self.appointments = []
        self.schedule = {"morning": [], "afternoon": [], "evening": []}
        self.utilization = {"morning": 0.0, "afternoon": 0.0, "evening": 0.0}
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            len(self.appointments) / 20.0,
            len(self.schedule["morning"]) / 10.0,
            len(self.schedule["afternoon"]) / 10.0,
            len(self.schedule["evening"]) / 10.0,
            self.utilization["morning"],
            self.utilization["afternoon"],
            self.utilization["evening"],
            np.mean(list(self.utilization.values())),
            len(self.appointments) / 30.0,
            *[0.0] * 7
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if action_name.startswith("schedule_"):
            slot = action_name.split("_")[1]
            if self.appointments:
                appt = self.appointments.pop(0)
                self.schedule[slot].append(appt)
                self.utilization[slot] = min(1.0, self.utilization[slot] + 0.1)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        efficiency_score = np.mean(list(self.utilization.values()))
        financial_score = sum(len(v) for v in self.schedule.values()) / 30.0
        return {
            RewardComponent.CLINICAL: 1.0 - len(self.appointments) / 20.0,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.appointments) / 20.0,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 30 or len(self.appointments) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={},
            operational_efficiency={"utilization": np.mean(list(self.utilization.values())), "appointments_scheduled": sum(len(v) for v in self.schedule.values())},
            financial_metrics={"revenue": sum(len(v) for v in self.schedule.values()) * 500},
            patient_satisfaction=1.0 - len(self.appointments) / 20.0,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

