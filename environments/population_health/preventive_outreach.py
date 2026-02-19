"""Preventive Outreach Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class PreventiveOutreachEnv(HealthcareRLEnvironment):
    OUTREACH_TYPES = ["screening", "vaccination", "wellness_visit", "education", "no_outreach"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.OUTREACH_TYPES))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.target_population = []
        self.outreach_completed = []
        self.prevention_score = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.target_population = self.patient_generator.generate_batch(15)
        self.outreach_completed = []
        self.prevention_score = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(16, dtype=np.float32)
        state[0] = len(self.target_population) / 20.0
        state[1] = len(self.outreach_completed) / 15.0
        state[2] = self.prevention_score
        if self.target_population:
            p = self.target_population[0]
            state[3] = p.age / 100.0
            state[4] = p.risk_score
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        outreach = self.OUTREACH_TYPES[action]
        if self.target_population and outreach != "no_outreach":
            patient = self.target_population.pop(0)
            self.outreach_completed.append({"patient": patient, "type": outreach})
            self.prevention_score = min(1.0, self.prevention_score + 0.1)
        return {"outreach": outreach}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.prevention_score
        efficiency_score = len(self.outreach_completed) / 15.0
        financial_score = 1.0 / (1.0 + len(self.outreach_completed) * 150 / 5000.0)
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.prevention_score,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 20 or len(self.target_population) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"prevention_score": self.prevention_score},
            operational_efficiency={"outreach_completed": len(self.outreach_completed)},
            financial_metrics={"outreach_cost": len(self.outreach_completed) * 150},
            patient_satisfaction=self.prevention_score,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

