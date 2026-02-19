"""HIE Routing Environment - Routes data through Health Information Exchange"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class HIERoutingEnv(HealthcareRLEnvironment):
    ROUTES = ["direct_push", "query_response", "subscription", "batch_upload", "no_route"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ROUTES))
        self.data_packets = []
        self.routed_packets = []
        self.routing_efficiency = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.data_packets = [{"size": self.np_random.uniform(1, 10), "priority": self.np_random.uniform(0, 1), "destination": self.np_random.choice(["facility_a", "facility_b", "facility_c"])} for _ in range(12)]
        self.routed_packets = []
        self.routing_efficiency = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            len(self.data_packets) / 20.0,
            len(self.routed_packets) / 15.0,
            self.routing_efficiency,
            np.mean([p["priority"] for p in self.data_packets[:5]]) if self.data_packets else 0.0,
            *[0.0] * 12
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        route = self.ROUTES[action]
        if self.data_packets and route != "no_route":
            packet = self.data_packets.pop(0)
            self.routed_packets.append({**packet, "route": route})
            self.routing_efficiency = min(1.0, self.routing_efficiency + 0.05)
        return {"route": route}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.routing_efficiency
        efficiency_score = 1.0 - len(self.data_packets) / 20.0
        financial_score = self.routing_efficiency * 0.9
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.routing_efficiency,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 30 or len(self.data_packets) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"routing_efficiency": self.routing_efficiency},
            operational_efficiency={"packets_routed": len(self.routed_packets)},
            financial_metrics={"routing_cost": len(self.routed_packets) * 20},
            patient_satisfaction=self.routing_efficiency,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

