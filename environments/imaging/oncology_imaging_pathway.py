"""Oncology Imaging Pathway Environment - Optimizes oncology imaging pathways (Philips, GE)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class OncologyImagingPathwayEnv(HealthcareRLEnvironment):
    ACTIONS = ["schedule_baseline", "schedule_followup", "schedule_response", "prioritize", "defer", "coordinate_series"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(18,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.pathway_queue = []
        self.scheduled_pathways = []
        self.pathway_coordination = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.pathway_queue = [{"patient": self.patient_generator.generate_patient(), "pathway_stage": self.np_random.choice(["baseline", "followup", "response"]), "urgency": self.np_random.uniform(0, 1), "wait_time": 0.0} for _ in range(15)]
        self.scheduled_pathways = []
        self.pathway_coordination = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(18, dtype=np.float32)
        state[0] = len(self.pathway_queue) / 20.0
        state[1] = len(self.scheduled_pathways) / 20.0
        if self.pathway_queue:
            state[2] = self.pathway_queue[0]["urgency"]
            state[3] = self.pathway_queue[0]["wait_time"] / 7.0
            state[4] = 1.0 if self.pathway_queue[0]["pathway_stage"] == "baseline" else (0.5 if self.pathway_queue[0]["pathway_stage"] == "followup" else 0.0)
        state[5] = self.pathway_coordination
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.pathway_queue:
            pathway = self.pathway_queue.pop(0)
            if action_name in ["schedule_baseline", "schedule_followup", "schedule_response"]:
                self.scheduled_pathways.append({**pathway, "scheduled": True})
                self.pathway_coordination = min(1.0, self.pathway_coordination + 0.1)
            elif action_name == "coordinate_series":
                similar_pathways = [p for p in self.pathway_queue if p["pathway_stage"] == pathway["pathway_stage"]][:2]
                self.scheduled_pathways.append({**pathway, "scheduled": True, "coordinated": True})
                for p in similar_pathways:
                    self.scheduled_pathways.append({**p, "scheduled": True, "coordinated": True})
                    if p in self.pathway_queue:
                        self.pathway_queue.remove(p)
                self.pathway_coordination = min(1.0, self.pathway_coordination + 0.2)
            elif action_name == "defer":
                self.pathway_queue.append(pathway)
                pathway["wait_time"] += 1.0
        for pathway in self.pathway_queue:
            pathway["wait_time"] += 0.5
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = 1.0 - len([p for p in self.pathway_queue if p["urgency"] > 0.8]) / 15.0
        efficiency_score = self.pathway_coordination
        financial_score = len(self.scheduled_pathways) / 20.0
        risk_penalty = len([p for p in self.pathway_queue if p["urgency"] > 0.9 and p["wait_time"] > 2.0]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.pathway_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 40 or len(self.pathway_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"urgent_pathways_waiting": len([p for p in self.pathway_queue if p["urgency"] > 0.8])},
            operational_efficiency={"queue_length": len(self.pathway_queue), "pathway_coordination": self.pathway_coordination},
            financial_metrics={"pathways_scheduled": len(self.scheduled_pathways)},
            patient_satisfaction=1.0 - len(self.pathway_queue) / 20.0,
            risk_score=len([p for p in self.pathway_queue if p["urgency"] > 0.9 and p["wait_time"] > 2.0]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

