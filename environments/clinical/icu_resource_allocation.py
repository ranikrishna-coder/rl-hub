"""ICU Resource Allocation Environment - Allocates ICU beds and staff optimally"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator, ConditionSeverity
from simulator.hospital_simulator import HospitalSimulator, BedType

class ICUResourceAllocationEnv(HealthcareRLEnvironment):
    ACTIONS = ["admit_icu", "admit_stepdown", "discharge", "transfer", "monitor", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(22,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        self.current_patients = []
        self.waiting_queue = []
    def _initialize_state(self) -> np.ndarray:
        self.current_patients = self.patient_generator.generate_batch(5)
        self.waiting_queue = []
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(22, dtype=np.float32)
        hospital_state = self.hospital_simulator.get_state()
        state[0] = hospital_state.occupied_beds.get(BedType.ICU, 0) / 20.0
        state[1] = hospital_state.occupied_beds.get(BedType.STEP_DOWN, 0) / 30.0
        state[2] = hospital_state.occupancy_rate
        state[3] = len(self.waiting_queue) / 10.0
        for i, p in enumerate(self.current_patients[:5]):
            if i < 5:
                idx = 4 + i * 3
                state[idx] = p.risk_score
                state[idx+1] = 1.0 if p.severity == ConditionSeverity.CRITICAL else 0.0
                state[idx+2] = p.vitals.get("oxygen_saturation", 98) / 100.0
        state[19] = hospital_state.available_staff.get("nurse", 0) / 80.0
        state[20] = hospital_state.available_staff.get("physician", 0) / 20.0
        state[21] = len(self.current_patients) / 10.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        info = {"action": action_name}
        if action_name == "admit_icu" and self.current_patients:
            p = self.current_patients[0]
            self.hospital_simulator.admit_patient(p, BedType.ICU)
            self.current_patients.pop(0)
        elif action_name == "admit_stepdown" and self.current_patients:
            p = self.current_patients[0]
            self.hospital_simulator.admit_patient(p, BedType.STEP_DOWN)
            self.current_patients.pop(0)
        self.hospital_simulator.update(1.0)
        return info
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        hospital_state = self.hospital_simulator.get_state()
        occupancy = hospital_state.occupancy_rate
        clinical_score = 1.0 - len(self.waiting_queue) / 10.0
        efficiency_score = 1.0 - abs(occupancy - 0.85)  # Target 85% occupancy
        financial_score = occupancy * 0.8  # Higher occupancy = more revenue
        risk_penalty = len(self.waiting_queue) * 0.1 if len(self.waiting_queue) > 3 else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.waiting_queue) / 10.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 100 or (len(self.current_patients) == 0 and len(self.waiting_queue) == 0)
    def _get_kpis(self) -> KPIMetrics:
        hospital_state = self.hospital_simulator.get_state()
        return KPIMetrics(
            clinical_outcomes={"icu_occupancy": hospital_state.occupied_beds.get(BedType.ICU, 0) / 20.0},
            operational_efficiency={"bed_utilization": hospital_state.occupancy_rate, "queue_length": len(self.waiting_queue)},
            financial_metrics={"revenue": hospital_state.occupancy_rate * 10000},
            patient_satisfaction=1.0 - len(self.waiting_queue) / 10.0,
            risk_score=len(self.waiting_queue) / 10.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

