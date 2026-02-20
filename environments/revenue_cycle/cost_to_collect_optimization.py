"""Cost-to-Collect Optimization Environment - Optimizes cost to collect (Change Healthcare)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class CostToCollectOptimizationEnv(HealthcareRLEnvironment):
    ACTIONS = ["automated_collection", "manual_collection", "outsource_collection", "payment_plan", "defer", "write_off"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(18,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.collection_queue = []
        self.collected_accounts = []
        self.cost_to_collect = 0.0
        self.total_collected = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.collection_queue = [{"patient": self.patient_generator.generate_patient(), "amount_due": self.np_random.uniform(100, 5000), "collection_cost": self.np_random.uniform(10, 200), "collection_probability": self.np_random.uniform(0.3, 0.9), "days_outstanding": 0.0} for _ in range(15)]
        self.collected_accounts = []
        self.cost_to_collect = 0.0
        self.total_collected = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(18, dtype=np.float32)
        state[0] = len(self.collection_queue) / 20.0
        state[1] = len(self.collected_accounts) / 20.0
        if self.collection_queue:
            state[2] = self.collection_queue[0]["amount_due"] / 5000.0
            state[3] = self.collection_queue[0]["collection_cost"] / 200.0
            state[4] = self.collection_queue[0]["collection_probability"]
            state[5] = self.collection_queue[0]["days_outstanding"] / 90.0
        state[6] = self.cost_to_collect / 1000.0
        state[7] = self.total_collected / 50000.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.collection_queue:
            account = self.collection_queue.pop(0)
            if action_name == "automated_collection":
                cost = account["collection_cost"] * 0.3
                collected = account["amount_due"] * account["collection_probability"] * 0.8
                self.cost_to_collect += cost
                self.total_collected += collected
                self.collected_accounts.append({**account, "method": "automated", "collected": collected, "cost": cost})
            elif action_name == "manual_collection":
                cost = account["collection_cost"]
                collected = account["amount_due"] * account["collection_probability"]
                self.cost_to_collect += cost
                self.total_collected += collected
                self.collected_accounts.append({**account, "method": "manual", "collected": collected, "cost": cost})
            elif action_name == "outsource_collection":
                cost = account["collection_cost"] * 0.5
                collected = account["amount_due"] * account["collection_probability"] * 0.7
                self.cost_to_collect += cost
                self.total_collected += collected
                self.collected_accounts.append({**account, "method": "outsourced", "collected": collected, "cost": cost})
            elif action_name == "payment_plan":
                cost = account["collection_cost"] * 0.2
                collected = account["amount_due"] * account["collection_probability"] * 0.6
                self.cost_to_collect += cost
                self.total_collected += collected
                self.collected_accounts.append({**account, "method": "payment_plan", "collected": collected, "cost": cost})
            elif action_name == "write_off":
                self.collected_accounts.append({**account, "method": "written_off", "collected": 0.0, "cost": 0.0})
            elif action_name == "defer":
                account["days_outstanding"] += 7.0
                account["collection_probability"] = max(0.1, account["collection_probability"] - 0.05)
                self.collection_queue.append(account)
        for account in self.collection_queue:
            account["days_outstanding"] += 1.0
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        cost_efficiency = 1.0 - (self.cost_to_collect / max(1.0, self.total_collected)) if self.total_collected > 0 else 0.0
        clinical_score = cost_efficiency
        efficiency_score = len(self.collected_accounts) / 20.0
        financial_score = self.total_collected / 50000.0
        risk_penalty = len([a for a in self.collection_queue if a["days_outstanding"] > 60 and a["collection_probability"] < 0.3]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.collection_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.collection_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        cost_efficiency = 1.0 - (self.cost_to_collect / max(1.0, self.total_collected)) if self.total_collected > 0 else 0.0
        return KPIMetrics(
            clinical_outcomes={"cost_efficiency": cost_efficiency, "old_accounts_waiting": len([a for a in self.collection_queue if a["days_outstanding"] > 60])},
            operational_efficiency={"queue_length": len(self.collection_queue), "accounts_collected": len(self.collected_accounts), "cost_to_collect": self.cost_to_collect},
            financial_metrics={"total_collected": self.total_collected, "cost_efficiency": cost_efficiency},
            patient_satisfaction=1.0 - len(self.collection_queue) / 20.0,
            risk_score=len([a for a in self.collection_queue if a["days_outstanding"] > 60 and a["collection_probability"] < 0.3]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

