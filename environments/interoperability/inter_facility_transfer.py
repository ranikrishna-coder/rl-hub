"""Inter-Facility Transfer Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class InterFacilityTransferEnv(HealthcareRLEnvironment):
    ACTIONS = ["transfer_approved", "transfer_denied", "request_info", "expedite", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.transfer_requests = []
        self.completed_transfers = 0
        self.transfer_efficiency = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.transfer_requests = [{"urgency": self.np_random.uniform(0, 1), "facility_match": self.np_random.uniform(0.5, 1.0)} for _ in range(8)]
        self.completed_transfers = 0
        self.transfer_efficiency = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            len(self.transfer_requests) / 15.0,
            self.completed_transfers / 10.0,
            self.transfer_efficiency,
            np.mean([t["urgency"] for t in self.transfer_requests[:5]]) if self.transfer_requests else 0.0,
            *[0.0] * 12
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.transfer_requests and action_name == "transfer_approved":
            transfer = self.transfer_requests.pop(0)
            self.completed_transfers += 1
            self.transfer_efficiency = min(1.0, self.transfer_efficiency + 0.1)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.transfer_efficiency
        efficiency_score = 1.0 - len(self.transfer_requests) / 15.0
        financial_score = self.completed_transfers / 10.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.transfer_efficiency,
            RewardComponent.RISK_PENALTY: len([t for t in self.transfer_requests if t["urgency"] > 0.8]) / 10.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 25 or len(self.transfer_requests) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"transfer_efficiency": self.transfer_efficiency},
            operational_efficiency={"transfers_completed": self.completed_transfers},
            financial_metrics={"transfer_cost": self.completed_transfers * 500},
            patient_satisfaction=self.transfer_efficiency,
            risk_score=len([t for t in self.transfer_requests if t["urgency"] > 0.8]) / 10.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

