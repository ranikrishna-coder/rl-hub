"""Population Health Cost Allocation Environment - Allocates population health costs (Health Catalyst, Innovaccer)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class PopulationHealthCostAllocationEnv(HealthcareRLEnvironment):
    ACTIONS = ["allocate_preventive", "allocate_chronic", "allocate_acute", "optimize_allocation", "defer", "reallocate"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(18,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.allocation_queue = []
        self.allocated_resources = []
        self.cost_efficiency = 0.0
        self.total_budget = 100000.0
        self.allocated_budget = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.allocation_queue = [{"patient": self.patient_generator.generate_patient(), "cost_category": self.np_random.choice(["preventive", "chronic", "acute"]), "cost_estimate": self.np_random.uniform(100, 5000), "priority": self.np_random.uniform(0, 1)} for _ in range(15)]
        self.allocated_resources = []
        self.cost_efficiency = 0.0
        self.total_budget = 100000.0
        self.allocated_budget = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(18, dtype=np.float32)
        state[0] = len(self.allocation_queue) / 20.0
        state[1] = len(self.allocated_resources) / 20.0
        if self.allocation_queue:
            state[2] = self.allocation_queue[0]["cost_estimate"] / 5000.0
            state[3] = self.allocation_queue[0]["priority"]
        state[4] = self.cost_efficiency
        state[5] = self.allocated_budget / self.total_budget
        state[6] = (self.total_budget - self.allocated_budget) / self.total_budget
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.allocation_queue:
            allocation = self.allocation_queue.pop(0)
            if action_name in ["allocate_preventive", "allocate_chronic", "allocate_acute"]:
                if self.allocated_budget + allocation["cost_estimate"] <= self.total_budget:
                    self.allocated_resources.append({**allocation, "allocated": True})
                    self.allocated_budget += allocation["cost_estimate"]
                    self.cost_efficiency = min(1.0, self.cost_efficiency + 0.1)
            elif action_name == "optimize_allocation":
                # Reallocate to optimize
                if self.allocated_budget + allocation["cost_estimate"] * 0.8 <= self.total_budget:
                    allocation["cost_estimate"] *= 0.8
                    self.allocated_resources.append({**allocation, "allocated": True, "optimized": True})
                    self.allocated_budget += allocation["cost_estimate"]
                    self.cost_efficiency = min(1.0, self.cost_efficiency + 0.15)
            elif action_name == "reallocate":
                # Move budget from lower priority
                self.allocation_queue.append(allocation)
            elif action_name == "defer":
                self.allocation_queue.append(allocation)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = len([a for a in self.allocated_resources if a["priority"] > 0.7]) / max(1, len(self.allocated_resources))
        efficiency_score = self.cost_efficiency
        financial_score = 1.0 - (self.allocated_budget / self.total_budget) if self.allocated_budget < self.total_budget else 0.0
        risk_penalty = len([a for a in self.allocation_queue if a["priority"] > 0.9]) * 0.2
        compliance_penalty = 0.2 if self.allocated_budget > self.total_budget else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.allocation_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or (len(self.allocation_queue) == 0 or self.allocated_budget >= self.total_budget)
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"high_priority_allocated": len([a for a in self.allocated_resources if a["priority"] > 0.7])},
            operational_efficiency={"queue_length": len(self.allocation_queue), "cost_efficiency": self.cost_efficiency, "budget_utilization": self.allocated_budget / self.total_budget},
            financial_metrics={"allocated_budget": self.allocated_budget, "remaining_budget": self.total_budget - self.allocated_budget},
            patient_satisfaction=1.0 - len(self.allocation_queue) / 20.0,
            risk_score=len([a for a in self.allocation_queue if a["priority"] > 0.9]) / 15.0,
            compliance_score=1.0 - (0.2 if self.allocated_budget > self.total_budget else 0.0),
            timestamp=self.time_step
        )

