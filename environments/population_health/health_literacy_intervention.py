"""Health Literacy Intervention Environment - Manages health literacy interventions (Health Catalyst, Innovaccer)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class HealthLiteracyInterventionEnv(HealthcareRLEnvironment):
    ACTIONS = ["provide_education", "simplify_materials", "use_visual_aids", "cultural_adaptation", "defer", "escalate"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.intervention_queue = []
        self.completed_interventions = []
        self.literacy_improvement = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.intervention_queue = [{"patient": self.patient_generator.generate_patient(), "literacy_level": self.np_random.uniform(0, 1), "comprehension_score": self.np_random.uniform(0.3, 0.8), "interventions_received": 0} for _ in range(15)]
        self.completed_interventions = []
        self.literacy_improvement = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.intervention_queue) / 20.0
        state[1] = len(self.completed_interventions) / 20.0
        if self.intervention_queue:
            state[2] = self.intervention_queue[0]["literacy_level"]
            state[3] = self.intervention_queue[0]["comprehension_score"]
        state[4] = self.literacy_improvement
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.intervention_queue:
            patient = self.intervention_queue.pop(0)
            if action_name == "provide_education":
                patient["comprehension_score"] = min(1.0, patient["comprehension_score"] + 0.15)
                patient["interventions_received"] += 1
                self.completed_interventions.append({**patient, "intervention": "education"})
                self.literacy_improvement = min(1.0, self.literacy_improvement + 0.1)
            elif action_name == "simplify_materials":
                patient["comprehension_score"] = min(1.0, patient["comprehension_score"] + 0.2)
                patient["interventions_received"] += 1
                self.completed_interventions.append({**patient, "intervention": "simplified"})
                self.literacy_improvement = min(1.0, self.literacy_improvement + 0.12)
            elif action_name == "use_visual_aids":
                patient["comprehension_score"] = min(1.0, patient["comprehension_score"] + 0.18)
                patient["interventions_received"] += 1
                self.completed_interventions.append({**patient, "intervention": "visual"})
                self.literacy_improvement = min(1.0, self.literacy_improvement + 0.1)
            elif action_name == "cultural_adaptation":
                patient["comprehension_score"] = min(1.0, patient["comprehension_score"] + 0.25)
                patient["interventions_received"] += 1
                self.completed_interventions.append({**patient, "intervention": "cultural"})
                self.literacy_improvement = min(1.0, self.literacy_improvement + 0.15)
            elif action_name == "escalate":
                patient["comprehension_score"] = min(1.0, patient["comprehension_score"] + 0.3)
                patient["interventions_received"] += 1
                self.completed_interventions.append({**patient, "intervention": "escalated"})
                self.literacy_improvement = min(1.0, self.literacy_improvement + 0.2)
            elif action_name == "defer":
                self.intervention_queue.append(patient)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.literacy_improvement
        efficiency_score = len(self.completed_interventions) / 20.0
        financial_score = len(self.completed_interventions) / 20.0
        risk_penalty = len([p for p in self.intervention_queue if p["literacy_level"] < 0.3]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.literacy_improvement,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.intervention_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"literacy_improvement": self.literacy_improvement, "low_literacy_waiting": len([p for p in self.intervention_queue if p["literacy_level"] < 0.3])},
            operational_efficiency={"queue_length": len(self.intervention_queue), "interventions_completed": len(self.completed_interventions)},
            financial_metrics={"completed_count": len(self.completed_interventions)},
            patient_satisfaction=self.literacy_improvement,
            risk_score=len([p for p in self.intervention_queue if p["literacy_level"] < 0.3]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

