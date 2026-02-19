"""Trial Patient Matching Environment - Matches patients to clinical trials (Veeva, IQVIA)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator
from simulator.clinical_trial_simulator import ClinicalTrialSimulator, TrialPhase

class TrialPatientMatchingEnv(HealthcareRLEnvironment):
    ACTIONS = ["match", "reject", "screen", "defer", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(19,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.trial_simulator = ClinicalTrialSimulator("TRIAL_001", TrialPhase.PHASE_3, 200, seed=self.np_random.integers(0, 10000))
        self.simulator = self.trial_simulator
        self.patient_pool = []
        self.matched_patients = []
    def _initialize_state(self) -> np.ndarray:
        self.patient_pool = self.patient_generator.generate_batch(15)
        self.matched_patients = []
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(19, dtype=np.float32)
        state[0] = len(self.patient_pool) / 20.0
        state[1] = len(self.matched_patients) / 15.0
        trial_state = self.trial_simulator.get_state()
        state[2] = trial_state.current_enrollment / trial_state.target_enrollment
        state[3] = trial_state.enrollment_rate / 5.0
        if self.patient_pool:
            p = self.patient_pool[0]
            state[4] = p.age / 100.0
            state[5] = p.risk_score
            state[6] = len(p.conditions) / 5.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.patient_pool and action_name == "match":
            patient = self.patient_pool.pop(0)
            self.trial_simulator.add_to_screening_pool(patient.patient_id)
            if self.trial_simulator.screen_patient(patient.patient_id):
                self.trial_simulator.enroll_patient(patient.patient_id)
                self.matched_patients.append(patient)
        self.trial_simulator.update(1.0)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        trial_state = self.trial_simulator.get_state()
        clinical_score = trial_state.current_enrollment / trial_state.target_enrollment
        efficiency_score = trial_state.enrollment_rate / 5.0
        financial_score = trial_state.current_enrollment / trial_state.target_enrollment
        risk_penalty = 0.0 if trial_state.enrollment_on_track else 0.2
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: trial_state.current_enrollment / trial_state.target_enrollment,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        trial_state = self.trial_simulator.get_state()
        return self.time_step >= 40 or trial_state.current_enrollment >= trial_state.target_enrollment
    def _get_kpis(self) -> KPIMetrics:
        trial_state = self.trial_simulator.get_state()
        return KPIMetrics(
            clinical_outcomes={"enrollment": trial_state.current_enrollment, "enrollment_rate": trial_state.enrollment_rate},
            operational_efficiency={"enrollment_progress": trial_state.current_enrollment / trial_state.target_enrollment},
            financial_metrics={"trial_value": trial_state.current_enrollment * 5000},
            patient_satisfaction=trial_state.current_enrollment / trial_state.target_enrollment,
            risk_score=0.0 if trial_state.enrollment_on_track else 0.2,
            compliance_score=1.0,
            timestamp=self.time_step
        )

