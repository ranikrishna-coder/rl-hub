"""Bed Turnover Optimization Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.hospital_simulator import HospitalSimulator

class BedTurnoverOptimizationEnv(HealthcareRLEnvironment):
    ACTIONS = ["discharge", "transfer", "extend_stay", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        self.turnover_rate = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.turnover_rate = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        hospital_state = self.hospital_simulator.get_state()
        return np.array([
            hospital_state.occupancy_rate,
            self.turnover_rate,
            len(hospital_state.patient_queue) / 20.0,
            *[0.0] * 13
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if action_name == "discharge" and self.hospital_simulator.patients:
            patient_id = list(self.hospital_simulator.patients.keys())[0]
            self.hospital_simulator.discharge_patient(patient_id)
            self.turnover_rate = min(1.0, self.turnover_rate + 0.1)
        self.hospital_simulator.update(1.0)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        hospital_state = self.hospital_simulator.get_state()
        clinical_score = 1.0 - len(hospital_state.patient_queue) / 20.0
        efficiency_score = self.turnover_rate
        financial_score = hospital_state.occupancy_rate * 0.9
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(hospital_state.patient_queue) / 20.0,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 40
    def _get_kpis(self) -> KPIMetrics:
        hospital_state = self.hospital_simulator.get_state()
        return KPIMetrics(
            clinical_outcomes={"queue_length": len(hospital_state.patient_queue)},
            operational_efficiency={"turnover_rate": self.turnover_rate, "occupancy_rate": hospital_state.occupancy_rate},
            financial_metrics={"revenue": hospital_state.occupancy_rate * 100000},
            patient_satisfaction=1.0 - len(hospital_state.patient_queue) / 20.0,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

