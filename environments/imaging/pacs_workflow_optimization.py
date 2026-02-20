"""PACS Workflow Optimization Environment - Optimizes PACS workflow (Philips, GE)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class PACSWorkflowOptimizationEnv(HealthcareRLEnvironment):
    ACTIONS = ["route_urgent", "route_routine", "batch_process", "prioritize", "defer", "auto_route"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.pacs_queue = []
        self.processed_studies = []
        self.workflow_efficiency = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.pacs_queue = [{"patient": self.patient_generator.generate_patient(), "urgency": self.np_random.uniform(0, 1), "study_type": self.np_random.choice(["ct", "mri", "xray", "ultrasound"]), "wait_time": 0.0} for _ in range(15)]
        self.processed_studies = []
        self.workflow_efficiency = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(16, dtype=np.float32)
        state[0] = len(self.pacs_queue) / 20.0
        state[1] = len(self.processed_studies) / 20.0
        if self.pacs_queue:
            state[2] = self.pacs_queue[0]["urgency"]
            state[3] = self.pacs_queue[0]["wait_time"] / 7.0
        state[4] = self.workflow_efficiency
        state[5] = np.mean([s["urgency"] for s in self.pacs_queue[:5]]) if self.pacs_queue else 0.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.pacs_queue:
            study = self.pacs_queue.pop(0)
            if action_name not in ["defer"]:
                self.processed_studies.append({**study, "action": action_name})
                self.workflow_efficiency = min(1.0, self.workflow_efficiency + 0.1)
            elif action_name == "defer":
                self.pacs_queue.append(study)
                study["wait_time"] += 1.0
        for study in self.pacs_queue:
            study["wait_time"] += 0.5
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = 1.0 - len([s for s in self.pacs_queue if s["urgency"] > 0.8]) / 15.0
        efficiency_score = self.workflow_efficiency
        financial_score = len(self.processed_studies) / 20.0
        risk_penalty = len([s for s in self.pacs_queue if s["urgency"] > 0.9 and s["wait_time"] > 2.0]) * 0.2
        compliance_penalty = 0.2 if self.pacs_queue and self.pacs_queue[0]["urgency"] > 0.8 and self.ACTIONS[action] == "defer" else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.pacs_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 40 or len(self.pacs_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"urgent_studies_waiting": len([s for s in self.pacs_queue if s["urgency"] > 0.8])},
            operational_efficiency={"queue_length": len(self.pacs_queue), "workflow_efficiency": self.workflow_efficiency},
            financial_metrics={"studies_processed": len(self.processed_studies)},
            patient_satisfaction=1.0 - len(self.pacs_queue) / 20.0,
            risk_score=len([s for s in self.pacs_queue if s["urgency"] > 0.9 and s["wait_time"] > 2.0]) / 15.0,
            compliance_score=1.0 - (0.2 if self.pacs_queue and self.pacs_queue[0]["urgency"] > 0.8 else 0.0),
            timestamp=self.time_step
        )

