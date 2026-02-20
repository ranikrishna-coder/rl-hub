"""Patient Billing Prioritization Environment - Prioritizes patient billing (Change Healthcare)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class PatientBillingPrioritizationEnv(HealthcareRLEnvironment):
    ACTIONS = ["bill_immediate", "bill_routine", "defer_billing", "payment_plan", "write_off", "escalate"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.billing_queue = []
        self.processed_bills = []
        self.revenue_collected = 0.0
        self.total_billable = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.billing_queue = [{"patient": self.patient_generator.generate_patient(), "bill_amount": self.np_random.uniform(100, 10000), "days_outstanding": self.np_random.uniform(0, 90), "collection_probability": self.np_random.uniform(0.3, 1.0)} for _ in range(15)]
        self.processed_bills = []
        self.revenue_collected = 0.0
        self.total_billable = sum(b["bill_amount"] for b in self.billing_queue)
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.billing_queue) / 20.0
        state[1] = len(self.processed_bills) / 20.0
        if self.billing_queue:
            state[2] = self.billing_queue[0]["bill_amount"] / 10000.0
            state[3] = self.billing_queue[0]["days_outstanding"] / 90.0
            state[4] = self.billing_queue[0]["collection_probability"]
        state[5] = self.revenue_collected / self.total_billable if self.total_billable > 0 else 0.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.billing_queue:
            bill = self.billing_queue.pop(0)
            if action_name == "bill_immediate":
                collected = bill["bill_amount"] * bill["collection_probability"]
                self.revenue_collected += collected
                self.processed_bills.append({**bill, "status": "billed", "collected": collected})
            elif action_name == "bill_routine":
                collected = bill["bill_amount"] * bill["collection_probability"] * 0.9
                self.revenue_collected += collected
                self.processed_bills.append({**bill, "status": "billed", "collected": collected})
            elif action_name == "payment_plan":
                collected = bill["bill_amount"] * bill["collection_probability"] * 0.7
                self.revenue_collected += collected
                self.processed_bills.append({**bill, "status": "payment_plan", "collected": collected})
            elif action_name == "write_off":
                self.processed_bills.append({**bill, "status": "written_off", "collected": 0.0})
            elif action_name == "escalate":
                collected = bill["bill_amount"] * min(1.0, bill["collection_probability"] + 0.2)
                self.revenue_collected += collected
                self.processed_bills.append({**bill, "status": "escalated", "collected": collected})
            elif action_name == "defer_billing":
                bill["days_outstanding"] += 7.0
                self.billing_queue.append(bill)
        for bill in self.billing_queue:
            bill["days_outstanding"] += 1.0
            bill["collection_probability"] = max(0.1, bill["collection_probability"] - 0.01)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        collection_rate = self.revenue_collected / self.total_billable if self.total_billable > 0 else 0.0
        clinical_score = collection_rate
        efficiency_score = len(self.processed_bills) / 20.0
        financial_score = collection_rate
        risk_penalty = len([b for b in self.billing_queue if b["days_outstanding"] > 60 and b["collection_probability"] < 0.5]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.billing_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.billing_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        collection_rate = self.revenue_collected / self.total_billable if self.total_billable > 0 else 0.0
        return KPIMetrics(
            clinical_outcomes={"collection_rate": collection_rate, "old_bills_waiting": len([b for b in self.billing_queue if b["days_outstanding"] > 60])},
            operational_efficiency={"queue_length": len(self.billing_queue), "bills_processed": len(self.processed_bills)},
            financial_metrics={"revenue_collected": self.revenue_collected, "collection_rate": collection_rate},
            patient_satisfaction=1.0 - len(self.billing_queue) / 20.0,
            risk_score=len([b for b in self.billing_queue if b["days_outstanding"] > 60 and b["collection_probability"] < 0.5]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

