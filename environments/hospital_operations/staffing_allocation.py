"""Staffing Allocation Environment - Allocates staff across departments (Meditech)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.hospital_simulator import HospitalSimulator, StaffType

class StaffingAllocationEnv(HealthcareRLEnvironment):
    ALLOCATIONS = ["increase_icu", "increase_ed", "increase_or", "increase_floor", "maintain", "reduce"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(18,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ALLOCATIONS))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        self.staff_utilization = {}
    def _initialize_state(self) -> np.ndarray:
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        hospital_state = self.hospital_simulator.get_state()
        state = np.zeros(18, dtype=np.float32)
        state[0] = hospital_state.occupancy_rate
        state[1] = hospital_state.available_staff.get(StaffType.NURSE, 0) / 80.0
        state[2] = hospital_state.available_staff.get(StaffType.PHYSICIAN, 0) / 20.0
        state[3] = hospital_state.staff_utilization.get(StaffType.NURSE, 0.0)
        state[4] = hospital_state.staff_utilization.get(StaffType.PHYSICIAN, 0.0)
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        allocation = self.ALLOCATIONS[action]
        self.hospital_simulator.update(1.0)
        return {"allocation": allocation}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        hospital_state = self.hospital_simulator.get_state()
        clinical_score = 1.0 - len(hospital_state.patient_queue) / 20.0
        efficiency_score = np.mean(list(hospital_state.staff_utilization.values()))
        financial_score = hospital_state.occupancy_rate * 0.9
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(hospital_state.patient_queue) / 20.0,
            RewardComponent.RISK_PENALTY: len(hospital_state.patient_queue) / 20.0 if len(hospital_state.patient_queue) > 5 else 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 40
    def _get_kpis(self) -> KPIMetrics:
        hospital_state = self.hospital_simulator.get_state()
        return KPIMetrics(
            clinical_outcomes={"queue_length": len(hospital_state.patient_queue)},
            operational_efficiency={"staff_utilization": np.mean(list(hospital_state.staff_utilization.values())), "occupancy_rate": hospital_state.occupancy_rate},
            financial_metrics={"revenue": hospital_state.occupancy_rate * 100000},
            patient_satisfaction=1.0 - len(hospital_state.patient_queue) / 20.0,
            risk_score=len(hospital_state.patient_queue) / 20.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

