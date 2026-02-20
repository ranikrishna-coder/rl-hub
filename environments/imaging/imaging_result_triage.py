"""Imaging Result Triage Environment - Triages imaging results (Philips, GE)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class ImagingResultTriageEnv(HealthcareRLEnvironment):
    ACTIONS = ["flag_critical", "flag_urgent", "flag_routine", "auto_triage", "defer", "escalate"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.result_queue = []
        self.triaged_results = []
        self.critical_found = 0
    def _initialize_state(self) -> np.ndarray:
        self.result_queue = [{"patient": self.patient_generator.generate_patient(), "abnormality_score": self.np_random.uniform(0, 1), "urgency": self.np_random.uniform(0, 1), "wait_time": 0.0} for _ in range(15)]
        self.triaged_results = []
        self.critical_found = 0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.result_queue) / 20.0
        state[1] = len(self.triaged_results) / 20.0
        if self.result_queue:
            state[2] = self.result_queue[0]["abnormality_score"]
            state[3] = self.result_queue[0]["urgency"]
            state[4] = self.result_queue[0]["wait_time"] / 7.0
        state[5] = self.critical_found / 10.0
        state[6] = np.mean([r["abnormality_score"] for r in self.result_queue[:5]]) if self.result_queue else 0.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.result_queue:
            result = self.result_queue.pop(0)
            if action_name == "flag_critical":
                self.triaged_results.append({**result, "priority": "critical"})
                if result["abnormality_score"] > 0.8:
                    self.critical_found += 1
            elif action_name == "flag_urgent":
                self.triaged_results.append({**result, "priority": "urgent"})
            elif action_name == "flag_routine":
                self.triaged_results.append({**result, "priority": "routine"})
            elif action_name == "auto_triage":
                priority = "critical" if result["abnormality_score"] > 0.7 else ("urgent" if result["abnormality_score"] > 0.4 else "routine")
                self.triaged_results.append({**result, "priority": priority})
                if result["abnormality_score"] > 0.8:
                    self.critical_found += 1
            elif action_name == "defer":
                self.result_queue.append(result)
                result["wait_time"] += 1.0
            elif action_name == "escalate":
                self.triaged_results.append({**result, "priority": "critical"})
                self.critical_found += 1
        for result in self.result_queue:
            result["wait_time"] += 0.5
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.critical_found / max(1, len([r for r in self.result_queue + self.triaged_results if r.get("abnormality_score", 0) > 0.8]))
        efficiency_score = len(self.triaged_results) / 20.0
        financial_score = len(self.triaged_results) / 20.0
        risk_penalty = len([r for r in self.result_queue if r["abnormality_score"] > 0.8 and r["wait_time"] > 2.0]) * 0.3
        compliance_penalty = 0.2 if self.result_queue and self.result_queue[0]["abnormality_score"] > 0.8 and self.ACTIONS[action] != "flag_critical" else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.result_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 40 or len(self.result_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"critical_found": self.critical_found, "abnormal_results_waiting": len([r for r in self.result_queue if r["abnormality_score"] > 0.8])},
            operational_efficiency={"queue_length": len(self.result_queue), "results_triaged": len(self.triaged_results)},
            financial_metrics={"triaged_count": len(self.triaged_results)},
            patient_satisfaction=1.0 - len(self.result_queue) / 20.0,
            risk_score=len([r for r in self.result_queue if r["abnormality_score"] > 0.8 and r["wait_time"] > 2.0]) / 15.0,
            compliance_score=1.0 - (0.2 if self.result_queue and self.result_queue[0]["abnormality_score"] > 0.8 else 0.0),
            timestamp=self.time_step
        )

