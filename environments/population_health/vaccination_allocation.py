"""Vaccination Allocation Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class VaccinationAllocationEnv(HealthcareRLEnvironment):
    ALLOCATIONS = ["priority_group_1", "priority_group_2", "priority_group_3", "general_population", "no_allocation"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ALLOCATIONS))
        self.vaccine_supply = 1000
        self.allocated = 0
        self.priority_groups = {"group_1": 200, "group_2": 300, "group_3": 500, "general": 1000}
    def _initialize_state(self) -> np.ndarray:
        self.vaccine_supply = 1000
        self.allocated = 0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            self.vaccine_supply / 2000.0,
            self.allocated / 1000.0,
            self.priority_groups["group_1"] / 500.0,
            self.priority_groups["group_2"] / 500.0,
            self.priority_groups["group_3"] / 500.0,
            *[0.0] * 10
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        allocation = self.ALLOCATIONS[action]
        if allocation != "no_allocation" and self.vaccine_supply > 0:
            doses = {"priority_group_1": 50, "priority_group_2": 30, "priority_group_3": 20, "general_population": 10}.get(allocation, 10)
            self.vaccine_supply = max(0, self.vaccine_supply - doses)
            self.allocated += doses
        return {"allocation": allocation}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.allocated / 1000.0
        efficiency_score = 1.0 - self.vaccine_supply / 2000.0 if self.vaccine_supply < 1000 else 0.5
        financial_score = self.allocated / 1000.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.allocated / 1000.0,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 30 or self.vaccine_supply == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"doses_allocated": self.allocated},
            operational_efficiency={"supply_utilization": 1.0 - self.vaccine_supply / 2000.0},
            financial_metrics={"allocation_cost": self.allocated * 50},
            patient_satisfaction=self.allocated / 1000.0,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

