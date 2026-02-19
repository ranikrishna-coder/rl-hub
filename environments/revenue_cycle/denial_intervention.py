"""Denial Intervention Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.financial_simulator import FinancialSimulator, ClaimStatus

class DenialInterventionEnv(HealthcareRLEnvironment):
    INTERVENTIONS = ["appeal", "correct_and_resubmit", "write_off", "patient_billing", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.INTERVENTIONS))
        self.financial_simulator = FinancialSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.financial_simulator
        self.denied_claims = []
        self.recovered_revenue = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.denied_claims = [c for c in self.financial_simulator.claims.values() if c.status == ClaimStatus.DENIED]
        self.recovered_revenue = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.denied_claims) / 20.0
        state[1] = self.recovered_revenue / 50000.0
        if self.denied_claims:
            claim = self.denied_claims[0]
            state[2] = claim.amount / 10000.0
            state[3] = 1.0 if claim.denial_reason else 0.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        intervention = self.INTERVENTIONS[action]
        if self.denied_claims:
            claim = self.denied_claims.pop(0)
            if intervention == "appeal":
                self.financial_simulator.appeal_claim(claim.claim_id)
                if claim.status == ClaimStatus.APPROVED:
                    self.recovered_revenue += claim.amount * 0.8
            elif intervention == "correct_and_resubmit":
                self.recovered_revenue += claim.amount * 0.6
        self.financial_simulator.update(1.0)
        return {"intervention": intervention}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.recovered_revenue / 50000.0
        efficiency_score = 1.0 - len(self.denied_claims) / 20.0
        financial_score = self.recovered_revenue / 50000.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.recovered_revenue / 50000.0,
            RewardComponent.RISK_PENALTY: len(self.denied_claims) / 20.0 if len(self.denied_claims) > 10 else 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 25 or len(self.denied_claims) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"recovered_revenue": self.recovered_revenue},
            operational_efficiency={"denials_processed": len([c for c in self.financial_simulator.claims.values() if c.status != ClaimStatus.DENIED])},
            financial_metrics={"revenue_recovery_rate": self.recovered_revenue / 50000.0},
            patient_satisfaction=self.recovered_revenue / 50000.0,
            risk_score=len(self.denied_claims) / 20.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

