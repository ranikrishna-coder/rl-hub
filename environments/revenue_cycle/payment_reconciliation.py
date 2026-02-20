"""Payment Reconciliation Environment - Reconciles payments (Change Healthcare)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class PaymentReconciliationEnv(HealthcareRLEnvironment):
    ACTIONS = ["match_payment", "investigate_discrepancy", "apply_adjustment", "escalate", "defer", "write_off"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.reconciliation_queue = []
        self.reconciled_payments = []
        self.reconciliation_rate = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.reconciliation_queue = [{"patient": self.patient_generator.generate_patient(), "expected_amount": self.np_random.uniform(500, 5000), "received_amount": self.np_random.uniform(0, 5000), "discrepancy": 0.0, "days_unreconciled": 0.0} for _ in range(15)]
        for payment in self.reconciliation_queue:
            payment["discrepancy"] = abs(payment["expected_amount"] - payment["received_amount"])
        self.reconciled_payments = []
        self.reconciliation_rate = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.reconciliation_queue) / 20.0
        state[1] = len(self.reconciled_payments) / 20.0
        if self.reconciliation_queue:
            state[2] = self.reconciliation_queue[0]["discrepancy"] / 5000.0
            state[3] = self.reconciliation_queue[0]["days_unreconciled"] / 30.0
        state[4] = self.reconciliation_rate
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.reconciliation_queue:
            payment = self.reconciliation_queue.pop(0)
            if action_name == "match_payment":
                if payment["discrepancy"] < 10.0:
                    self.reconciled_payments.append({**payment, "status": "matched"})
                    self.reconciliation_rate = min(1.0, self.reconciliation_rate + 0.1)
                else:
                    payment["days_unreconciled"] += 1.0
                    self.reconciliation_queue.append(payment)
            elif action_name == "investigate_discrepancy":
                payment["discrepancy"] = max(0, payment["discrepancy"] - payment["discrepancy"] * 0.3)
                self.reconciliation_queue.insert(0, payment)
            elif action_name == "apply_adjustment":
                self.reconciled_payments.append({**payment, "status": "adjusted"})
                self.reconciliation_rate = min(1.0, self.reconciliation_rate + 0.08)
            elif action_name == "escalate":
                self.reconciled_payments.append({**payment, "status": "escalated"})
                self.reconciliation_rate = min(1.0, self.reconciliation_rate + 0.05)
            elif action_name == "write_off":
                self.reconciled_payments.append({**payment, "status": "written_off"})
            elif action_name == "defer":
                payment["days_unreconciled"] += 7.0
                self.reconciliation_queue.append(payment)
        for payment in self.reconciliation_queue:
            payment["days_unreconciled"] += 1.0
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.reconciliation_rate
        efficiency_score = len(self.reconciled_payments) / 20.0
        financial_score = self.reconciliation_rate
        risk_penalty = len([p for p in self.reconciliation_queue if p["days_unreconciled"] > 30]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.reconciliation_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.reconciliation_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"reconciliation_rate": self.reconciliation_rate, "old_payments_waiting": len([p for p in self.reconciliation_queue if p["days_unreconciled"] > 30])},
            operational_efficiency={"queue_length": len(self.reconciliation_queue), "payments_reconciled": len(self.reconciled_payments)},
            financial_metrics={"reconciliation_rate": self.reconciliation_rate},
            patient_satisfaction=1.0 - len(self.reconciliation_queue) / 20.0,
            risk_score=len([p for p in self.reconciliation_queue if p["days_unreconciled"] > 30]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

