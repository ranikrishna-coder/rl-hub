"""Imaging Quality Control Environment - Controls imaging quality (Philips, GE)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class ImagingQualityControlEnv(HealthcareRLEnvironment):
    ACTIONS = ["approve_quality", "reject_retake", "flag_review", "auto_approve", "defer", "quality_improve"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.quality_queue = []
        self.approved_studies = []
        self.quality_score = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.quality_queue = [{"patient": self.patient_generator.generate_patient(), "quality_metric": self.np_random.uniform(0.5, 1.0), "urgency": self.np_random.uniform(0, 1), "wait_time": 0.0} for _ in range(15)]
        self.approved_studies = []
        self.quality_score = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.quality_queue) / 20.0
        state[1] = len(self.approved_studies) / 20.0
        if self.quality_queue:
            state[2] = self.quality_queue[0]["quality_metric"]
            state[3] = self.quality_queue[0]["urgency"]
            state[4] = self.quality_queue[0]["wait_time"] / 7.0
        state[5] = self.quality_score
        state[6] = np.mean([q["quality_metric"] for q in self.quality_queue[:5]]) if self.quality_queue else 0.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.quality_queue:
            study = self.quality_queue.pop(0)
            if action_name == "approve_quality":
                self.approved_studies.append({**study, "status": "approved"})
                self.quality_score = min(1.0, self.quality_score + 0.1)
            elif action_name == "reject_retake":
                # Retake improves quality
                study["quality_metric"] = min(1.0, study["quality_metric"] + 0.2)
                self.quality_queue.insert(0, study)
            elif action_name == "flag_review":
                self.approved_studies.append({**study, "status": "flagged"})
            elif action_name == "auto_approve":
                if study["quality_metric"] > 0.9:
                    self.approved_studies.append({**study, "status": "auto_approved"})
                    self.quality_score = min(1.0, self.quality_score + 0.05)
                else:
                    self.quality_queue.append(study)
            elif action_name == "quality_improve":
                study["quality_metric"] = min(1.0, study["quality_metric"] + 0.1)
                self.quality_queue.insert(0, study)
            elif action_name == "defer":
                self.quality_queue.append(study)
                study["wait_time"] += 1.0
        for study in self.quality_queue:
            study["wait_time"] += 0.5
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        avg_quality = np.mean([s.get("quality_metric", 0.8) for s in self.approved_studies]) if self.approved_studies else 0.8
        clinical_score = avg_quality
        efficiency_score = len(self.approved_studies) / 20.0
        financial_score = len(self.approved_studies) / 20.0
        risk_penalty = len([s for s in self.quality_queue if s["quality_metric"] < 0.7 and s["wait_time"] > 2.0]) * 0.2
        compliance_penalty = 0.2 if self.quality_queue and self.quality_queue[0]["quality_metric"] < 0.7 and self.ACTIONS[action] == "approve_quality" else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.quality_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 40 or len(self.quality_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        avg_quality = np.mean([s.get("quality_metric", 0.8) for s in self.approved_studies]) if self.approved_studies else 0.8
        return KPIMetrics(
            clinical_outcomes={"avg_quality_score": avg_quality, "low_quality_waiting": len([s for s in self.quality_queue if s["quality_metric"] < 0.7])},
            operational_efficiency={"queue_length": len(self.quality_queue), "studies_approved": len(self.approved_studies)},
            financial_metrics={"approved_count": len(self.approved_studies)},
            patient_satisfaction=1.0 - len(self.quality_queue) / 20.0,
            risk_score=len([s for s in self.quality_queue if s["quality_metric"] < 0.7 and s["wait_time"] > 2.0]) / 15.0,
            compliance_score=1.0 - (0.2 if self.quality_queue and self.quality_queue[0]["quality_metric"] < 0.7 else 0.0),
            timestamp=self.time_step
        )

