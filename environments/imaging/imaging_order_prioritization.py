"""Imaging Order Prioritization Environment - Prioritizes imaging orders (Philips, GE)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class ImagingOrderPrioritizationEnv(HealthcareRLEnvironment):
    PRIORITIES = ["stat", "urgent", "routine", "defer", "cancel"]
    IMAGING_TYPES = ["ct", "mri", "xray", "ultrasound", "pet"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(20,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.PRIORITIES))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.orders_queue = []
        self.processed_orders = []
        self.equipment_utilization = {"ct": 0.0, "mri": 0.0, "xray": 0.0, "ultrasound": 0.0, "pet": 0.0}
    def _initialize_state(self) -> np.ndarray:
        self.orders_queue = [{"patient": self.patient_generator.generate_patient(), "type": self.np_random.choice(self.IMAGING_TYPES), "urgency": self.np_random.uniform(0, 1), "clinical_indication": self.np_random.uniform(0, 1)} for _ in range(15)]
        self.processed_orders = []
        self.equipment_utilization = {k: 0.0 for k in self.IMAGING_TYPES}
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(20, dtype=np.float32)
        state[0] = len(self.orders_queue) / 30.0
        state[1] = len(self.processed_orders) / 20.0
        if self.orders_queue:
            order = self.orders_queue[0]
            state[2] = order["urgency"]
            state[3] = order["clinical_indication"]
            state[4] = order["patient"].risk_score
            state[5] = 1.0 if order["type"] == "ct" else 0.0
            state[6] = 1.0 if order["type"] == "mri" else 0.0
            state[7] = 1.0 if order["type"] == "xray" else 0.0
        state[8] = self.equipment_utilization["ct"]
        state[9] = self.equipment_utilization["mri"]
        state[10] = self.equipment_utilization["xray"]
        state[11] = self.equipment_utilization["ultrasound"]
        state[12] = self.equipment_utilization["pet"]
        state[13] = np.mean([o["urgency"] for o in self.orders_queue[:5]]) if self.orders_queue else 0.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        priority = self.PRIORITIES[action]
        if self.orders_queue:
            order = self.orders_queue.pop(0)
            if priority != "cancel" and priority != "defer":
                self.processed_orders.append({**order, "priority": priority})
                self.equipment_utilization[order["type"]] = min(1.0, self.equipment_utilization[order["type"]] + 0.1)
        return {"priority": priority}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = 1.0 - len([o for o in self.orders_queue if o["urgency"] > 0.8]) / 15.0
        efficiency_score = np.mean(list(self.equipment_utilization.values()))
        financial_score = len(self.processed_orders) / 20.0
        risk_penalty = len([o for o in self.orders_queue if o["urgency"] > 0.9]) * 0.15
        compliance_penalty = 0.0
        if self.orders_queue and self.PRIORITIES[action] not in ["stat", "urgent"] and self.orders_queue[0]["urgency"] > 0.8:
            compliance_penalty = 0.2
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.orders_queue) / 30.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 40 or len(self.orders_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"urgent_orders_waiting": len([o for o in self.orders_queue if o["urgency"] > 0.8])},
            operational_efficiency={"queue_length": len(self.orders_queue), "equipment_utilization": np.mean(list(self.equipment_utilization.values()))},
            financial_metrics={"orders_processed": len(self.processed_orders)},
            patient_satisfaction=1.0 - len(self.orders_queue) / 30.0,
            risk_score=len([o for o in self.orders_queue if o["urgency"] > 0.9]) / 15.0,
            compliance_score=1.0 - (0.2 if self.orders_queue and self.orders_queue[0]["urgency"] > 0.8 else 0.0),
            timestamp=self.time_step
        )

