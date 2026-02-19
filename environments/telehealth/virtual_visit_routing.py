"""Virtual Visit Routing Environment - Routes virtual visits to appropriate providers (Teladoc, Amwell)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class VirtualVisitRoutingEnv(HealthcareRLEnvironment):
    ROUTES = ["primary_care", "specialist", "urgent_care", "behavioral_health", "no_route"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ROUTES))
        self.visit_queue = []
        self.routed_visits = []
        self.provider_availability = {"primary_care": 0.8, "specialist": 0.6, "urgent_care": 0.9, "behavioral_health": 0.7}
    def _initialize_state(self) -> np.ndarray:
        self.visit_queue = [{"urgency": self.np_random.uniform(0, 1), "type": self.np_random.choice(["routine", "urgent", "followup"])} for _ in range(12)]
        self.routed_visits = []
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            len(self.visit_queue) / 20.0,
            len(self.routed_visits) / 15.0,
            np.mean([v["urgency"] for v in self.visit_queue[:5]]) if self.visit_queue else 0.0,
            np.mean(list(self.provider_availability.values())),
            *[0.0] * 12
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        route = self.ROUTES[action]
        if self.visit_queue and route != "no_route":
            visit = self.visit_queue.pop(0)
            self.routed_visits.append({**visit, "route": route})
            self.provider_availability[route] = max(0, self.provider_availability[route] - 0.1)
        return {"route": route}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = 1.0 - len(self.visit_queue) / 20.0
        efficiency_score = np.mean(list(self.provider_availability.values()))
        financial_score = len(self.routed_visits) / 15.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.visit_queue) / 20.0,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 30 or len(self.visit_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"visits_routed": len(self.routed_visits)},
            operational_efficiency={"queue_length": len(self.visit_queue), "provider_utilization": np.mean(list(self.provider_availability.values()))},
            financial_metrics={"visit_revenue": len(self.routed_visits) * 150},
            patient_satisfaction=1.0 - len(self.visit_queue) / 20.0,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

