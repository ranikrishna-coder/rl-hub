"""Equipment Utilization Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class EquipmentUtilizationEnv(HealthcareRLEnvironment):
    ACTIONS = ["schedule_ct", "schedule_mri", "schedule_xray", "maintenance", "idle"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.equipment = {"ct": {"utilization": 0.0, "maintenance_due": 0.0}, "mri": {"utilization": 0.0, "maintenance_due": 0.0}, "xray": {"utilization": 0.0, "maintenance_due": 0.0}}
        self.scheduled_scans = []
    def _initialize_state(self) -> np.ndarray:
        self.equipment = {k: {"utilization": 0.0, "maintenance_due": self.np_random.uniform(0, 0.3)} for k in ["ct", "mri", "xray"]}
        self.scheduled_scans = []
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            self.equipment["ct"]["utilization"],
            self.equipment["mri"]["utilization"],
            self.equipment["xray"]["utilization"],
            self.equipment["ct"]["maintenance_due"],
            self.equipment["mri"]["maintenance_due"],
            self.equipment["xray"]["maintenance_due"],
            len(self.scheduled_scans) / 20.0,
            np.mean([e["utilization"] for e in self.equipment.values()]),
            *[0.0] * 8
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if action_name.startswith("schedule_"):
            eq_type = action_name.split("_")[1]
            if self.equipment[eq_type]["maintenance_due"] < 0.2:
                self.equipment[eq_type]["utilization"] = min(1.0, self.equipment[eq_type]["utilization"] + 0.1)
                self.scheduled_scans.append(eq_type)
        elif action_name == "maintenance":
            for eq in self.equipment.values():
                eq["maintenance_due"] = max(0, eq["maintenance_due"] - 0.3)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        avg_utilization = np.mean([e["utilization"] for e in self.equipment.values()])
        maintenance_penalty = sum([e["maintenance_due"] for e in self.equipment.values()]) / 3.0
        efficiency_score = avg_utilization if avg_utilization < 0.9 else 1.0 - (avg_utilization - 0.9) * 10
        financial_score = avg_utilization * 0.9
        return {
            RewardComponent.CLINICAL: 1.0 - maintenance_penalty,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: avg_utilization,
            RewardComponent.RISK_PENALTY: maintenance_penalty,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 40
    def _get_kpis(self) -> KPIMetrics:
        avg_util = np.mean([e["utilization"] for e in self.equipment.values()])
        return KPIMetrics(
            clinical_outcomes={},
            operational_efficiency={"avg_utilization": avg_util, "scans_scheduled": len(self.scheduled_scans)},
            financial_metrics={"equipment_revenue": avg_util * 50000},
            patient_satisfaction=avg_util,
            risk_score=sum([e["maintenance_due"] for e in self.equipment.values()]) / 3.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

