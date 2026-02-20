"""Preventive Screening Policy Environment - Manages preventive screening (Health Catalyst, Innovaccer)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class PreventiveScreeningPolicyEnv(HealthcareRLEnvironment):
    ACTIONS = ["schedule_screening", "defer_screening", "prioritize_high_risk", "batch_schedule", "cancel", "remind"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.screening_queue = []
        self.scheduled_screenings = []
        self.screening_coverage = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.screening_queue = [{"patient": self.patient_generator.generate_patient(), "risk_level": self.np_random.uniform(0, 1), "screening_type": self.np_random.choice(["mammogram", "colonoscopy", "diabetes", "cholesterol"]), "days_overdue": 0.0} for _ in range(15)]
        self.scheduled_screenings = []
        self.screening_coverage = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.screening_queue) / 20.0
        state[1] = len(self.scheduled_screenings) / 20.0
        if self.screening_queue:
            state[2] = self.screening_queue[0]["risk_level"]
            state[3] = self.screening_queue[0]["days_overdue"] / 365.0
        state[4] = self.screening_coverage
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.screening_queue:
            screening = self.screening_queue.pop(0)
            if action_name == "schedule_screening":
                self.scheduled_screenings.append({**screening, "scheduled": True})
                self.screening_coverage = min(1.0, self.screening_coverage + 0.1)
            elif action_name == "prioritize_high_risk":
                if screening["risk_level"] > 0.7:
                    self.scheduled_screenings.append({**screening, "scheduled": True, "priority": "high"})
                    self.screening_coverage = min(1.0, self.screening_coverage + 0.15)
                else:
                    self.screening_queue.append(screening)
            elif action_name == "batch_schedule":
                similar = [s for s in self.screening_queue if s["screening_type"] == screening["screening_type"]][:3]
                self.scheduled_screenings.append({**screening, "scheduled": True})
                for s in similar:
                    self.scheduled_screenings.append({**s, "scheduled": True})
                    if s in self.screening_queue:
                        self.screening_queue.remove(s)
                self.screening_coverage = min(1.0, self.screening_coverage + 0.2)
            elif action_name == "remind":
                self.screening_queue.append(screening)
                screening["days_overdue"] += 7.0
            elif action_name == "defer_screening":
                self.screening_queue.append(screening)
                screening["days_overdue"] += 30.0
        for screening in self.screening_queue:
            screening["days_overdue"] += 1.0
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.screening_coverage
        efficiency_score = len(self.scheduled_screenings) / 20.0
        financial_score = len(self.scheduled_screenings) / 20.0
        risk_penalty = len([s for s in self.screening_queue if s["risk_level"] > 0.8 and s["days_overdue"] > 180.0]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.screening_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.screening_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"screening_coverage": self.screening_coverage, "high_risk_waiting": len([s for s in self.screening_queue if s["risk_level"] > 0.8])},
            operational_efficiency={"queue_length": len(self.screening_queue), "screenings_scheduled": len(self.scheduled_screenings)},
            financial_metrics={"scheduled_count": len(self.scheduled_screenings)},
            patient_satisfaction=1.0 - len(self.screening_queue) / 20.0,
            risk_score=len([s for s in self.screening_queue if s["risk_level"] > 0.8 and s["days_overdue"] > 180.0]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

