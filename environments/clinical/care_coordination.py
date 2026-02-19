"""Care Coordination Environment - Coordinates care across providers"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class CareCoordinationEnv(HealthcareRLEnvironment):
    ACTIONS = ["primary_care", "specialist", "lab_order", "imaging_order", "medication_sync", "care_plan_update"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(19,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.current_patient = None
        self.care_team = []
        self.care_plan = []
        self.coordination_score = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.current_patient = self.patient_generator.generate_patient()
        self.care_team = []
        self.care_plan = []
        self.coordination_score = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        if not self.current_patient:
            return np.zeros(19, dtype=np.float32)
        p = self.current_patient
        return np.array([
            p.age / 100.0, len(p.conditions) / 5.0, len(p.medications) / 10.0,
            len(self.care_team) / 5.0, len(self.care_plan) / 10.0,
            self.coordination_score, p.risk_score,
            1.0 if "primary_care" in self.care_team else 0.0,
            1.0 if "specialist" in self.care_team else 0.0,
            len(set([item.split("_")[0] for item in self.care_plan])) / 5.0,
            p.vitals.get("bp_systolic", 120) / 200.0,
            p.vitals.get("heart_rate", 72) / 150.0,
            p.lab_results.get("glucose", 100) / 200.0,
            p.readmission_risk, len(p.comorbidities) / 5.0,
            p.length_of_stay / 30.0, 1.0 if len(self.care_plan) > 3 else 0.0,
            self.current_patient.length_of_stay / 30.0,
            len([x for x in self.care_plan if "sync" in x]) / 5.0
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        self.care_plan.append(action_name)
        if "specialist" in action_name:
            self.care_team.append("specialist")
        elif "primary" in action_name:
            self.care_team.append("primary_care")
        if len(set(self.care_team)) > 1:
            self.coordination_score = min(1.0, self.coordination_score + 0.1)
        if "sync" in action_name and self.current_patient:
            self.current_patient.risk_score = max(0, self.current_patient.risk_score - 0.05)
        return {"action": action_name, "coordination": self.coordination_score}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        if not self.current_patient:
            return {k: 0.0 for k in RewardComponent}
        p = self.current_patient
        clinical_score = (1.0 - p.risk_score + self.coordination_score) / 2.0
        efficiency_score = self.coordination_score
        financial_score = 1.0 / (1.0 + len(self.care_plan) * 100 / 5000.0)
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.coordination_score,
            RewardComponent.RISK_PENALTY: p.risk_score if p.risk_score > 0.6 else 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 15 or (self.current_patient and self.coordination_score > 0.8 and self.current_patient.risk_score < 0.3)
    def _get_kpis(self) -> KPIMetrics:
        if not self.current_patient:
            return KPIMetrics({}, {}, {}, 0.0, 0.0, 0.0, self.time_step)
        p = self.current_patient
        return KPIMetrics(
            clinical_outcomes={"coordination_score": self.coordination_score, "risk_score": p.risk_score},
            operational_efficiency={"care_team_size": len(self.care_team), "care_plan_items": len(self.care_plan)},
            financial_metrics={"coordination_cost": len(self.care_plan) * 100},
            patient_satisfaction=self.coordination_score,
            risk_score=p.risk_score,
            compliance_score=1.0,
            timestamp=self.time_step
        )

