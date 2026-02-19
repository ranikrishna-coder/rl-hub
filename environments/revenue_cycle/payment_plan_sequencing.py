"""Payment Plan Sequencing Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class PaymentPlanSequencingEnv(HealthcareRLEnvironment):
    PLANS = ["immediate_payment", "installment_3mo", "installment_6mo", "installment_12mo", "financial_assistance", "no_plan"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.PLANS))
        self.patient_accounts = []
        self.collected_revenue = 0.0
        self.total_due = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.patient_accounts = [{"balance": self.np_random.uniform(500, 5000), "risk": self.np_random.uniform(0, 1)} for _ in range(12)]
        self.collected_revenue = 0.0
        self.total_due = sum(a["balance"] for a in self.patient_accounts)
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            len(self.patient_accounts) / 15.0,
            self.collected_revenue / 50000.0,
            self.total_due / 50000.0,
            np.mean([a["risk"] for a in self.patient_accounts[:5]]) if self.patient_accounts else 0.0,
            *[0.0] * 12
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        plan = self.PLANS[action]
        if self.patient_accounts:
            account = self.patient_accounts.pop(0)
            collection_rates = {"immediate_payment": 1.0, "installment_3mo": 0.9, "installment_6mo": 0.8, "installment_12mo": 0.7, "financial_assistance": 0.5}
            collected = account["balance"] * collection_rates.get(plan, 0.5)
            self.collected_revenue += collected
        return {"plan": plan}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        collection_rate = self.collected_revenue / self.total_due if self.total_due > 0 else 0.0
        clinical_score = collection_rate
        efficiency_score = 1.0 - len(self.patient_accounts) / 15.0
        financial_score = collection_rate
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: collection_rate,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 20 or len(self.patient_accounts) == 0
    def _get_kpis(self) -> KPIMetrics:
        collection_rate = self.collected_revenue / self.total_due if self.total_due > 0 else 0.0
        return KPIMetrics(
            clinical_outcomes={"collection_rate": collection_rate},
            operational_efficiency={"accounts_processed": len(self.patient_accounts)},
            financial_metrics={"collected_revenue": self.collected_revenue, "collection_rate": collection_rate},
            patient_satisfaction=collection_rate,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

