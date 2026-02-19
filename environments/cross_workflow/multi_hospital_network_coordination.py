"""Multi-Hospital Network Coordination Environment - Coordinates across hospital network"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class MultiHospitalNetworkCoordinationEnv(HealthcareRLEnvironment):
    ACTIONS = ["coordinate_transfer", "share_resources", "optimize_network", "balance_load", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(18,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.hospitals = {"hospital_a": {"occupancy": 0.7, "capacity": 100}, "hospital_b": {"occupancy": 0.8, "capacity": 100}, "hospital_c": {"occupancy": 0.6, "capacity": 100}}
        self.coordination_score = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.coordination_score = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            np.mean([h["occupancy"] for h in self.hospitals.values()]),
            np.std([h["occupancy"] for h in self.hospitals.values()]),
            self.coordination_score,
            len([h for h in self.hospitals.values() if h["occupancy"] > 0.9]) / 3.0,
            *[0.0] * 14
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if action_name == "balance_load":
            avg_occupancy = np.mean([h["occupancy"] for h in self.hospitals.values()])
            for h in self.hospitals.values():
                if h["occupancy"] > avg_occupancy + 0.1:
                    h["occupancy"] = max(avg_occupancy, h["occupancy"] - 0.1)
                elif h["occupancy"] < avg_occupancy - 0.1:
                    h["occupancy"] = min(1.0, h["occupancy"] + 0.1)
            self.coordination_score = min(1.0, self.coordination_score + 0.1)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        load_balance = 1.0 - np.std([h["occupancy"] for h in self.hospitals.values()])
        clinical_score = 1.0 - len([h for h in self.hospitals.values() if h["occupancy"] > 0.95]) / 3.0
        efficiency_score = self.coordination_score
        financial_score = np.mean([h["occupancy"] for h in self.hospitals.values()]) * 0.9
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: load_balance,
            RewardComponent.RISK_PENALTY: len([h for h in self.hospitals.values() if h["occupancy"] > 0.95]) / 3.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 40
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"network_occupancy": np.mean([h["occupancy"] for h in self.hospitals.values()])},
            operational_efficiency={"coordination_score": self.coordination_score, "load_balance": 1.0 - np.std([h["occupancy"] for h in self.hospitals.values()])},
            financial_metrics={"network_revenue": np.mean([h["occupancy"] for h in self.hospitals.values()]) * 300000},
            patient_satisfaction=1.0 - np.std([h["occupancy"] for h in self.hospitals.values()]),
            risk_score=len([h for h in self.hospitals.values() if h["occupancy"] > 0.95]) / 3.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

