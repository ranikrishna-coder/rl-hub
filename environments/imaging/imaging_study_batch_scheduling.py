"""Imaging Study Batch Scheduling Environment - Batches imaging studies (Philips, GE)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class ImagingStudyBatchSchedulingEnv(HealthcareRLEnvironment):
    ACTIONS = ["batch_similar", "batch_urgent", "schedule_individual", "defer_batch", "cancel", "optimize_batch"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.study_queue = []
        self.scheduled_batches = []
        self.batch_efficiency = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.study_queue = [{"patient": self.patient_generator.generate_patient(), "study_type": self.np_random.choice(["ct", "mri", "xray"]), "urgency": self.np_random.uniform(0, 1), "wait_time": 0.0} for _ in range(15)]
        self.scheduled_batches = []
        self.batch_efficiency = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.study_queue) / 20.0
        state[1] = len(self.scheduled_batches) / 10.0
        if self.study_queue:
            state[2] = self.study_queue[0]["urgency"]
            state[3] = self.study_queue[0]["wait_time"] / 7.0
        state[4] = self.batch_efficiency
        state[5] = len([s for s in self.study_queue if s["study_type"] == self.study_queue[0]["study_type"]]) / 15.0 if self.study_queue else 0.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.study_queue:
            if action_name == "batch_similar":
                study_type = self.study_queue[0]["study_type"]
                batch = [s for s in self.study_queue if s["study_type"] == study_type][:3]
                self.scheduled_batches.append({"studies": batch, "type": "similar"})
                for s in batch:
                    if s in self.study_queue:
                        self.study_queue.remove(s)
                self.batch_efficiency = min(1.0, self.batch_efficiency + 0.15)
            elif action_name == "batch_urgent":
                urgent = [s for s in self.study_queue if s["urgency"] > 0.7][:3]
                self.scheduled_batches.append({"studies": urgent, "type": "urgent"})
                for s in urgent:
                    if s in self.study_queue:
                        self.study_queue.remove(s)
                self.batch_efficiency = min(1.0, self.batch_efficiency + 0.1)
            elif action_name == "schedule_individual":
                study = self.study_queue.pop(0)
                self.scheduled_batches.append({"studies": [study], "type": "individual"})
            elif action_name == "optimize_batch":
                # Optimize existing batches
                self.batch_efficiency = min(1.0, self.batch_efficiency + 0.1)
        for study in self.study_queue:
            study["wait_time"] += 0.5
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = 1.0 - len([s for s in self.study_queue if s["urgency"] > 0.8]) / 15.0
        efficiency_score = self.batch_efficiency
        financial_score = len(self.scheduled_batches) / 10.0
        risk_penalty = len([s for s in self.study_queue if s["urgency"] > 0.9 and s["wait_time"] > 2.0]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.study_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 40 or len(self.study_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"urgent_studies_waiting": len([s for s in self.study_queue if s["urgency"] > 0.8])},
            operational_efficiency={"queue_length": len(self.study_queue), "batch_efficiency": self.batch_efficiency, "batches_scheduled": len(self.scheduled_batches)},
            financial_metrics={"batches_count": len(self.scheduled_batches)},
            patient_satisfaction=1.0 - len(self.study_queue) / 20.0,
            risk_score=len([s for s in self.study_queue if s["urgency"] > 0.9 and s["wait_time"] > 2.0]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

