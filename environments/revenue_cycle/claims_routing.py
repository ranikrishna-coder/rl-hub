"""Claims Routing Environment - Routes claims to appropriate processors (Change Healthcare)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.financial_simulator import FinancialSimulator, ClaimStatus

class ClaimsRoutingEnv(HealthcareRLEnvironment):
    ROUTES = ["auto_adjudicate", "manual_review", "specialist_review", "escalate", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(18,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ROUTES))
        self.financial_simulator = FinancialSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.financial_simulator
        self.claims_queue = []
        self.routed_claims = []
    def _initialize_state(self) -> np.ndarray:
        self.claims_queue = [self.financial_simulator.create_claim(f"PAT_{i}", self.np_random.uniform(500, 5000)) for i in range(15)]
        self.routed_claims = []
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(18, dtype=np.float32)
        state[0] = len(self.claims_queue) / 20.0
        state[1] = len(self.routed_claims) / 15.0
        if self.claims_queue:
            claim = self.claims_queue[0]
            state[2] = claim.amount / 10000.0
            state[3] = len(claim.cpt_codes) / 5.0
        financial_state = self.financial_simulator.get_state()
        state[4] = financial_state.claims_pending / 20.0
        state[5] = financial_state.denial_rate
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        route = self.ROUTES[action]
        if self.claims_queue:
            claim = self.claims_queue.pop(0)
            if route == "auto_adjudicate":
                self.financial_simulator.submit_claim(claim.claim_id)
            self.routed_claims.append({**claim.__dict__, "route": route})
        self.financial_simulator.update(1.0)
        return {"route": route}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        financial_state = self.financial_simulator.get_state()
        clinical_score = 1.0 - financial_state.denial_rate
        efficiency_score = 1.0 - len(self.claims_queue) / 20.0
        financial_score = financial_state.collection_rate
        risk_penalty = financial_state.denial_rate if financial_state.denial_rate > 0.3 else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - financial_state.denial_rate,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 30 or len(self.claims_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        financial_state = self.financial_simulator.get_state()
        return KPIMetrics(
            clinical_outcomes={"denial_rate": financial_state.denial_rate},
            operational_efficiency={"claims_routed": len(self.routed_claims), "queue_length": len(self.claims_queue)},
            financial_metrics={"collection_rate": financial_state.collection_rate, "total_revenue": financial_state.total_revenue},
            patient_satisfaction=1.0 - financial_state.denial_rate,
            risk_score=financial_state.denial_rate,
            compliance_score=1.0,
            timestamp=self.time_step
        )

