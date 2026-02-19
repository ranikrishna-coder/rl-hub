"""Surgical Scheduling Environment - Optimizes OR scheduling and resource allocation"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator
from simulator.hospital_simulator import HospitalSimulator, BedType

class SurgicalSchedulingEnv(HealthcareRLEnvironment):
    ACTIONS = ["schedule_urgent", "schedule_elective", "cancel", "reschedule", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(18,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        self.surgery_queue = []
        self.scheduled_surgeries = []
        self.or_utilization = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.surgery_queue = [{"patient": self.patient_generator.generate_patient(), "urgency": self.np_random.uniform(0, 1), "duration": self.np_random.uniform(1, 4)} for _ in range(10)]
        self.scheduled_surgeries = []
        self.or_utilization = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(18, dtype=np.float32)
        state[0] = len(self.surgery_queue) / 20.0
        state[1] = len(self.scheduled_surgeries) / 10.0
        state[2] = self.or_utilization
        if self.surgery_queue:
            state[3] = np.mean([s["urgency"] for s in self.surgery_queue[:5]])
            state[4] = np.mean([s["duration"] for s in self.surgery_queue[:5]]) / 4.0
        hospital_state = self.hospital_simulator.get_state()
        state[5] = hospital_state.occupied_beds.get(BedType.OR, 0) / 10.0
        state[6] = hospital_state.available_staff.get("physician", 0) / 20.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        info = {"action": action_name}
        if action_name == "schedule_urgent" and self.surgery_queue:
            surgery = max(self.surgery_queue, key=lambda x: x["urgency"])
            self.scheduled_surgeries.append(surgery)
            self.surgery_queue.remove(surgery)
            self.or_utilization = min(1.0, self.or_utilization + surgery["duration"] / 8.0)
        elif action_name == "schedule_elective" and self.surgery_queue:
            surgery = self.surgery_queue[0]
            self.scheduled_surgeries.append(surgery)
            self.surgery_queue.pop(0)
            self.or_utilization = min(1.0, self.or_utilization + surgery["duration"] / 8.0)
        return info
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = 1.0 - len([s for s in self.surgery_queue if s["urgency"] > 0.8]) / 10.0
        efficiency_score = self.or_utilization if self.or_utilization < 0.9 else 1.0 - (self.or_utilization - 0.9) * 10
        financial_score = self.or_utilization * 0.9
        risk_penalty = len([s for s in self.surgery_queue if s["urgency"] > 0.9]) * 0.2
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.surgery_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or (len(self.surgery_queue) == 0 and len(self.scheduled_surgeries) == 0)
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"urgent_surgeries_waiting": len([s for s in self.surgery_queue if s["urgency"] > 0.8])},
            operational_efficiency={"or_utilization": self.or_utilization, "queue_length": len(self.surgery_queue)},
            financial_metrics={"or_revenue": self.or_utilization * 50000},
            patient_satisfaction=1.0 - len(self.surgery_queue) / 20.0,
            risk_score=len([s for s in self.surgery_queue if s["urgency"] > 0.9]) / 10.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

