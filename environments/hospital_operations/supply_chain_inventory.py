"""Supply Chain Inventory Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class SupplyChainInventoryEnv(HealthcareRLEnvironment):
    ACTIONS = ["order_supplies", "adjust_inventory", "emergency_order", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.inventory_levels = {"medications": 0.7, "supplies": 0.6, "equipment": 0.8}
        self.stockouts = 0
        self.inventory_cost = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.inventory_levels = {"medications": 0.7, "supplies": 0.6, "equipment": 0.8}
        self.stockouts = 0
        self.inventory_cost = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            np.mean(list(self.inventory_levels.values())),
            self.stockouts / 10.0,
            self.inventory_cost / 50000.0,
            *[0.0] * 12
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if action_name == "order_supplies":
            for k in self.inventory_levels:
                self.inventory_levels[k] = min(1.0, self.inventory_levels[k] + 0.2)
            self.inventory_cost += 5000
        elif action_name == "emergency_order":
            for k in self.inventory_levels:
                self.inventory_levels[k] = min(1.0, self.inventory_levels[k] + 0.3)
            self.inventory_cost += 10000
        if any(v < 0.2 for v in self.inventory_levels.values()):
            self.stockouts += 1
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = 1.0 - self.stockouts / 10.0
        efficiency_score = np.mean(list(self.inventory_levels.values()))
        financial_score = 1.0 / (1.0 + self.inventory_cost / 50000.0)
        risk_penalty = self.stockouts / 10.0 if self.stockouts > 2 else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - self.stockouts / 10.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 30
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"stockouts": self.stockouts},
            operational_efficiency={"avg_inventory": np.mean(list(self.inventory_levels.values()))},
            financial_metrics={"inventory_cost": self.inventory_cost},
            patient_satisfaction=1.0 - self.stockouts / 10.0,
            risk_score=self.stockouts / 10.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

