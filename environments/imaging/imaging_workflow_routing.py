"""Imaging Workflow Routing Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class ImagingWorkflowRoutingEnv(HealthcareRLEnvironment):
    ROUTES = ["direct_reading", "preliminary", "ai_assist", "specialist_review", "batch_reading"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ROUTES))
        self.workflow_queue = []
        self.processed = []
        self.turnaround_times = []
    def _initialize_state(self) -> np.ndarray:
        self.workflow_queue = [{"priority": self.np_random.uniform(0, 1), "complexity": self.np_random.uniform(0, 1)} for _ in range(12)]
        self.processed = []
        self.turnaround_times = []
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            len(self.workflow_queue) / 20.0,
            len(self.processed) / 15.0,
            np.mean([w["priority"] for w in self.workflow_queue[:5]]) if self.workflow_queue else 0.0,
            np.mean(self.turnaround_times) / 24.0 if self.turnaround_times else 0.0,
            *[0.0] * 13
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        route = self.ROUTES[action]
        if self.workflow_queue:
            case = self.workflow_queue.pop(0)
            self.processed.append({**case, "route": route})
            turnaround = {"direct_reading": 1.0, "preliminary": 2.0, "ai_assist": 1.5, "specialist_review": 4.0, "batch_reading": 6.0}.get(route, 2.0)
            self.turnaround_times.append(turnaround)
        return {"route": route}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = 1.0 - len(self.workflow_queue) / 20.0
        efficiency_score = 1.0 - np.mean(self.turnaround_times) / 24.0 if self.turnaround_times else 0.5
        financial_score = len(self.processed) / 15.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - np.mean(self.turnaround_times) / 24.0 if self.turnaround_times else 0.5,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 35 or len(self.workflow_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={},
            operational_efficiency={"queue_length": len(self.workflow_queue), "avg_turnaround": np.mean(self.turnaround_times) if self.turnaround_times else 0.0},
            financial_metrics={"cases_processed": len(self.processed)},
            patient_satisfaction=1.0 - np.mean(self.turnaround_times) / 24.0 if self.turnaround_times else 0.5,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

