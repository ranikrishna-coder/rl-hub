"""Multi-Trial Resource Coordination Environment - Coordinates multi-trial resources (Veeva, IQVIA)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class MultiTrialResourceCoordinationEnv(HealthcareRLEnvironment):
    ACTIONS = ["allocate_trial_a", "allocate_trial_b", "allocate_trial_c", "optimize_allocation", "defer", "reallocate"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(18,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.coordination_queue = []
        self.coordinated_allocations = []
        self.coordination_efficiency = 0.0
        self.trial_utilization = {"trial_a": 0.0, "trial_b": 0.0, "trial_c": 0.0}
    def _initialize_state(self) -> np.ndarray:
        self.coordination_queue = [{"patient": self.patient_generator.generate_patient(), "trial_match_scores": {"trial_a": self.np_random.uniform(0, 1), "trial_b": self.np_random.uniform(0, 1), "trial_c": self.np_random.uniform(0, 1)}, "resource_need": self.np_random.uniform(0, 1)} for _ in range(15)]
        self.coordinated_allocations = []
        self.coordination_efficiency = 0.0
        self.trial_utilization = {"trial_a": 0.0, "trial_b": 0.0, "trial_c": 0.0}
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(18, dtype=np.float32)
        state[0] = len(self.coordination_queue) / 20.0
        state[1] = len(self.coordinated_allocations) / 20.0
        if self.coordination_queue:
            scores = self.coordination_queue[0]["trial_match_scores"]
            state[2] = scores["trial_a"]
            state[3] = scores["trial_b"]
            state[4] = scores["trial_c"]
            state[5] = self.coordination_queue[0]["resource_need"]
        state[6] = self.coordination_efficiency
        state[7] = self.trial_utilization["trial_a"]
        state[8] = self.trial_utilization["trial_b"]
        state[9] = self.trial_utilization["trial_c"]
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.coordination_queue:
            allocation = self.coordination_queue.pop(0)
            if action_name == "allocate_trial_a":
                self.coordinated_allocations.append({**allocation, "trial": "A"})
                self.trial_utilization["trial_a"] = min(1.0, self.trial_utilization["trial_a"] + 0.1)
                self.coordination_efficiency = min(1.0, self.coordination_efficiency + 0.1)
            elif action_name == "allocate_trial_b":
                self.coordinated_allocations.append({**allocation, "trial": "B"})
                self.trial_utilization["trial_b"] = min(1.0, self.trial_utilization["trial_b"] + 0.1)
                self.coordination_efficiency = min(1.0, self.coordination_efficiency + 0.1)
            elif action_name == "allocate_trial_c":
                self.coordinated_allocations.append({**allocation, "trial": "C"})
                self.trial_utilization["trial_c"] = min(1.0, self.trial_utilization["trial_c"] + 0.1)
                self.coordination_efficiency = min(1.0, self.coordination_efficiency + 0.1)
            elif action_name == "optimize_allocation":
                best_trial = max(allocation["trial_match_scores"], key=allocation["trial_match_scores"].get)
                self.coordinated_allocations.append({**allocation, "trial": best_trial, "optimized": True})
                self.trial_utilization[best_trial] = min(1.0, self.trial_utilization[best_trial] + 0.1)
                self.coordination_efficiency = min(1.0, self.coordination_efficiency + 0.15)
            elif action_name == "reallocate":
                # Move from underutilized to better match
                self.coordination_queue.insert(0, allocation)
            elif action_name == "defer":
                self.coordination_queue.append(allocation)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        utilization_balance = 1.0 - np.std(list(self.trial_utilization.values()))
        clinical_score = self.coordination_efficiency * utilization_balance
        efficiency_score = len(self.coordinated_allocations) / 20.0
        financial_score = len(self.coordinated_allocations) / 20.0
        risk_penalty = len([a for a in self.coordination_queue if a["resource_need"] > 0.8]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.coordination_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.coordination_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        utilization_balance = 1.0 - np.std(list(self.trial_utilization.values()))
        return KPIMetrics(
            clinical_outcomes={"coordination_efficiency": self.coordination_efficiency, "utilization_balance": utilization_balance, "high_need_waiting": len([a for a in self.coordination_queue if a["resource_need"] > 0.8])},
            operational_efficiency={"queue_length": len(self.coordination_queue), "allocations_coordinated": len(self.coordinated_allocations), "trial_utilization": np.mean(list(self.trial_utilization.values()))},
            financial_metrics={"coordinated_count": len(self.coordinated_allocations)},
            patient_satisfaction=1.0 - len(self.coordination_queue) / 20.0,
            risk_score=len([a for a in self.coordination_queue if a["resource_need"] > 0.8]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

