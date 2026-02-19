"""Patient Journey Optimization Environment - Multi-agent optimization across care continuum"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator
from simulator.hospital_simulator import HospitalSimulator
from simulator.financial_simulator import FinancialSimulator

class PatientJourneyOptimizationEnv(HealthcareRLEnvironment):
    ACTIONS = ["admit", "discharge", "transfer", "coordinate_care", "optimize_pathway", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(22,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.financial_simulator = FinancialSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        self.current_patient = None
        self.journey_steps = []
        self.journey_score = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.current_patient = self.patient_generator.generate_patient()
        self.journey_steps = []
        self.journey_score = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        if not self.current_patient:
            return np.zeros(22, dtype=np.float32)
        p = self.current_patient
        hospital_state = self.hospital_simulator.get_state()
        financial_state = self.financial_simulator.get_state()
        return np.array([
            p.risk_score, p.length_of_stay / 30.0, len(self.journey_steps) / 10.0,
            self.journey_score, hospital_state.occupancy_rate,
            financial_state.collection_rate, *[0.0] * 16
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        self.journey_steps.append(action_name)
        if action_name == "admit" and self.current_patient:
            self.hospital_simulator.admit_patient(self.current_patient)
        elif action_name == "discharge" and self.current_patient:
            self.hospital_simulator.discharge_patient(self.current_patient.patient_id)
            self.journey_score = min(1.0, self.journey_score + 0.2)
        self.hospital_simulator.update(1.0)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        if not self.current_patient:
            return {k: 0.0 for k in RewardComponent}
        p = self.current_patient
        clinical_score = (1.0 - p.risk_score + self.journey_score) / 2.0
        efficiency_score = 1.0 - len(self.journey_steps) / 10.0 if self.journey_score > 0.7 else 0.5
        financial_score = self.journey_score * 0.9
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.journey_score,
            RewardComponent.RISK_PENALTY: p.risk_score if p.risk_score > 0.6 else 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 30 or (self.journey_score > 0.8 and self.current_patient and self.current_patient.risk_score < 0.3)
    def _get_kpis(self) -> KPIMetrics:
        if not self.current_patient:
            return KPIMetrics({}, {}, {}, 0.0, 0.0, 0.0, self.time_step)
        p = self.current_patient
        return KPIMetrics(
            clinical_outcomes={"journey_score": self.journey_score, "risk_score": p.risk_score},
            operational_efficiency={"journey_length": len(self.journey_steps)},
            financial_metrics={"journey_cost": len(self.journey_steps) * 500},
            patient_satisfaction=self.journey_score,
            risk_score=p.risk_score,
            compliance_score=1.0,
            timestamp=self.time_step
        )

