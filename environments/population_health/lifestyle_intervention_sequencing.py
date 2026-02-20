"""Lifestyle Intervention Sequencing Environment - Sequences lifestyle interventions (Health Catalyst, Innovaccer)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class LifestyleInterventionSequencingEnv(HealthcareRLEnvironment):
    ACTIONS = ["diet_intervention", "exercise_intervention", "smoking_cessation", "stress_management", "defer", "comprehensive"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.intervention_queue = []
        self.completed_interventions = []
        self.lifestyle_improvement = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.intervention_queue = [{"patient": self.patient_generator.generate_patient(), "risk_factors": self.np_random.uniform(0, 1), "readiness_score": self.np_random.uniform(0.3, 1.0), "interventions_received": 0} for _ in range(15)]
        self.completed_interventions = []
        self.lifestyle_improvement = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.intervention_queue) / 20.0
        state[1] = len(self.completed_interventions) / 20.0
        if self.intervention_queue:
            state[2] = self.intervention_queue[0]["risk_factors"]
            state[3] = self.intervention_queue[0]["readiness_score"]
        state[4] = self.lifestyle_improvement
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.intervention_queue:
            patient = self.intervention_queue.pop(0)
            if action_name == "diet_intervention":
                patient["risk_factors"] = max(0, patient["risk_factors"] - 0.15)
                patient["interventions_received"] += 1
                self.completed_interventions.append({**patient, "intervention": "diet"})
                self.lifestyle_improvement = min(1.0, self.lifestyle_improvement + 0.1)
            elif action_name == "exercise_intervention":
                patient["risk_factors"] = max(0, patient["risk_factors"] - 0.18)
                patient["interventions_received"] += 1
                self.completed_interventions.append({**patient, "intervention": "exercise"})
                self.lifestyle_improvement = min(1.0, self.lifestyle_improvement + 0.12)
            elif action_name == "smoking_cessation":
                patient["risk_factors"] = max(0, patient["risk_factors"] - 0.25)
                patient["interventions_received"] += 1
                self.completed_interventions.append({**patient, "intervention": "smoking"})
                self.lifestyle_improvement = min(1.0, self.lifestyle_improvement + 0.2)
            elif action_name == "stress_management":
                patient["risk_factors"] = max(0, patient["risk_factors"] - 0.12)
                patient["interventions_received"] += 1
                self.completed_interventions.append({**patient, "intervention": "stress"})
                self.lifestyle_improvement = min(1.0, self.lifestyle_improvement + 0.08)
            elif action_name == "comprehensive":
                patient["risk_factors"] = max(0, patient["risk_factors"] - 0.35)
                patient["interventions_received"] += 2
                self.completed_interventions.append({**patient, "intervention": "comprehensive"})
                self.lifestyle_improvement = min(1.0, self.lifestyle_improvement + 0.25)
            elif action_name == "defer":
                self.intervention_queue.append(patient)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.lifestyle_improvement
        efficiency_score = len(self.completed_interventions) / 20.0
        financial_score = len(self.completed_interventions) / 20.0
        risk_penalty = len([p for p in self.intervention_queue if p["risk_factors"] > 0.8]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.lifestyle_improvement,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.intervention_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"lifestyle_improvement": self.lifestyle_improvement, "high_risk_waiting": len([p for p in self.intervention_queue if p["risk_factors"] > 0.8])},
            operational_efficiency={"queue_length": len(self.intervention_queue), "interventions_completed": len(self.completed_interventions)},
            financial_metrics={"completed_count": len(self.completed_interventions)},
            patient_satisfaction=self.lifestyle_improvement,
            risk_score=len([p for p in self.intervention_queue if p["risk_factors"] > 0.8]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

