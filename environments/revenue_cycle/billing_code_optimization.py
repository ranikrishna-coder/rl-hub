"""Billing Code Optimization Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class BillingCodeOptimizationEnv(HealthcareRLEnvironment):
    OPTIMIZATIONS = ["add_codes", "remove_codes", "update_codes", "verify_codes", "no_change"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.OPTIMIZATIONS))
        self.claims = []
        self.optimization_score = 0.5
        self.revenue_impact = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.claims = [{"cpt_codes": self.np_random.integers(1, 4), "amount": self.np_random.uniform(500, 3000), "accuracy": self.np_random.uniform(0.6, 0.9)} for _ in range(10)]
        self.optimization_score = 0.5
        self.revenue_impact = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            len(self.claims) / 15.0,
            self.optimization_score,
            self.revenue_impact / 20000.0,
            np.mean([c["accuracy"] for c in self.claims[:5]]) if self.claims else 0.0,
            *[0.0] * 11
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        optimization = self.OPTIMIZATIONS[action]
        if self.claims:
            claim = self.claims[0]
            if optimization == "add_codes":
                claim["cpt_codes"] = min(5, claim["cpt_codes"] + 1)
                claim["amount"] *= 1.1
                claim["accuracy"] = min(1.0, claim["accuracy"] + 0.1)
            elif optimization == "update_codes":
                claim["accuracy"] = min(1.0, claim["accuracy"] + 0.15)
            self.optimization_score = min(1.0, self.optimization_score + 0.1)
            self.revenue_impact += claim["amount"] * 0.05
        return {"optimization": optimization}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.optimization_score
        efficiency_score = 1.0 - len(self.claims) / 15.0
        financial_score = self.revenue_impact / 20000.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.optimization_score,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 15 or len(self.claims) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"optimization_score": self.optimization_score},
            operational_efficiency={"claims_optimized": len(self.claims)},
            financial_metrics={"revenue_impact": self.revenue_impact},
            patient_satisfaction=self.optimization_score,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

