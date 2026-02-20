"""Drug Supply Sequencing Environment - Sequences drug supply (Veeva, IQVIA)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class DrugSupplySequencingEnv(HealthcareRLEnvironment):
    ACTIONS = ["order_supply", "expedite_order", "allocate_existing", "batch_order", "defer", "emergency_supply"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.supply_queue = []
        self.fulfilled_orders = []
        self.supply_efficiency = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.supply_queue = [{"patient": self.patient_generator.generate_patient(), "drug_type": self.np_random.choice(["investigational", "control", "rescue"]), "urgency": self.np_random.uniform(0, 1), "days_until_needed": self.np_random.uniform(0, 30), "quantity_needed": self.np_random.uniform(1, 10)} for _ in range(15)]
        self.fulfilled_orders = []
        self.supply_efficiency = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.supply_queue) / 20.0
        state[1] = len(self.fulfilled_orders) / 20.0
        if self.supply_queue:
            state[2] = self.supply_queue[0]["urgency"]
            state[3] = self.supply_queue[0]["days_until_needed"] / 30.0
            state[4] = self.supply_queue[0]["quantity_needed"] / 10.0
        state[5] = self.supply_efficiency
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.supply_queue:
            order = self.supply_queue.pop(0)
            if action_name == "order_supply":
                self.fulfilled_orders.append({**order, "status": "ordered"})
                self.supply_efficiency = min(1.0, self.supply_efficiency + 0.1)
            elif action_name == "expedite_order":
                self.fulfilled_orders.append({**order, "status": "expedited"})
                self.supply_efficiency = min(1.0, self.supply_efficiency + 0.12)
            elif action_name == "allocate_existing":
                self.fulfilled_orders.append({**order, "status": "allocated"})
                self.supply_efficiency = min(1.0, self.supply_efficiency + 0.15)
            elif action_name == "batch_order":
                similar = [o for o in self.supply_queue if o["drug_type"] == order["drug_type"]][:3]
                self.fulfilled_orders.append({**order, "status": "batch_ordered"})
                for o in similar:
                    self.fulfilled_orders.append({**o, "status": "batch_ordered"})
                    if o in self.supply_queue:
                        self.supply_queue.remove(o)
                self.supply_efficiency = min(1.0, self.supply_efficiency + 0.2)
            elif action_name == "emergency_supply":
                self.fulfilled_orders.append({**order, "status": "emergency"})
                self.supply_efficiency = min(1.0, self.supply_efficiency + 0.18)
            elif action_name == "defer":
                order["days_until_needed"] = max(0, order["days_until_needed"] - 1)
                self.supply_queue.append(order)
        for order in self.supply_queue:
            order["days_until_needed"] = max(0, order["days_until_needed"] - 1)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.supply_efficiency
        efficiency_score = len(self.fulfilled_orders) / 20.0
        financial_score = len(self.fulfilled_orders) / 20.0
        risk_penalty = len([o for o in self.supply_queue if o["urgency"] > 0.8 and o["days_until_needed"] < 3]) * 0.3
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.supply_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.supply_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"supply_efficiency": self.supply_efficiency, "urgent_orders_waiting": len([o for o in self.supply_queue if o["urgency"] > 0.8])},
            operational_efficiency={"queue_length": len(self.supply_queue), "orders_fulfilled": len(self.fulfilled_orders)},
            financial_metrics={"fulfilled_count": len(self.fulfilled_orders)},
            patient_satisfaction=1.0 - len(self.supply_queue) / 20.0,
            risk_score=len([o for o in self.supply_queue if o["urgency"] > 0.8 and o["days_until_needed"] < 3]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

