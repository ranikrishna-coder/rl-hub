"""Provider Load Balancing Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class ProviderLoadBalancingEnv(HealthcareRLEnvironment):
    ACTIONS = ["assign_provider_1", "assign_provider_2", "assign_provider_3", "wait", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.providers = {"provider_1": {"load": 0.5, "capacity": 10}, "provider_2": {"load": 0.6, "capacity": 10}, "provider_3": {"load": 0.4, "capacity": 10}}
        self.patient_queue = []
    def _initialize_state(self) -> np.ndarray:
        self.patient_queue = [{"priority": self.np_random.uniform(0, 1)} for _ in range(8)]
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            len(self.patient_queue) / 15.0,
            np.mean([p["load"] for p in self.providers.values()]),
            self.providers["provider_1"]["load"],
            self.providers["provider_2"]["load"],
            self.providers["provider_3"]["load"],
            *[0.0] * 11
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.patient_queue and action_name.startswith("assign_"):
            provider_key = action_name.split("_")[1] + "_" + action_name.split("_")[2]
            if provider_key in self.providers:
                self.patient_queue.pop(0)
                self.providers[provider_key]["load"] = min(1.0, self.providers[provider_key]["load"] + 0.1)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        load_balance = 1.0 - np.std([p["load"] for p in self.providers.values()])
        clinical_score = 1.0 - len(self.patient_queue) / 15.0
        efficiency_score = load_balance
        financial_score = np.mean([p["load"] for p in self.providers.values()])
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.patient_queue) / 15.0,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 30 or len(self.patient_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"queue_length": len(self.patient_queue)},
            operational_efficiency={"load_balance": 1.0 - np.std([p["load"] for p in self.providers.values()]), "avg_load": np.mean([p["load"] for p in self.providers.values()])},
            financial_metrics={"provider_utilization": np.mean([p["load"] for p in self.providers.values()])},
            patient_satisfaction=1.0 - len(self.patient_queue) / 15.0,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

