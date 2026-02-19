"""Equipment Maintenance Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class EquipmentMaintenanceEnv(HealthcareRLEnvironment):
    ACTIONS = ["schedule_maintenance", "emergency_repair", "preventive_maintenance", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.equipment = {"mri": {"status": 0.9, "maintenance_due": 0.2}, "ct": {"status": 0.85, "maintenance_due": 0.3}, "xray": {"status": 0.95, "maintenance_due": 0.1}}
        self.downtime = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.equipment = {k: {"status": self.np_random.uniform(0.8, 1.0), "maintenance_due": self.np_random.uniform(0, 0.3)} for k in ["mri", "ct", "xray"]}
        self.downtime = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            np.mean([e["status"] for e in self.equipment.values()]),
            np.mean([e["maintenance_due"] for e in self.equipment.values()]),
            self.downtime / 10.0,
            *[0.0] * 12
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if action_name in ["schedule_maintenance", "preventive_maintenance"]:
            for e in self.equipment.values():
                e["maintenance_due"] = max(0, e["maintenance_due"] - 0.3)
                e["status"] = min(1.0, e["status"] + 0.1)
        elif action_name == "emergency_repair":
            for e in self.equipment.values():
                if e["status"] < 0.5:
                    e["status"] = 0.8
                    self.downtime += 1.0
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        avg_status = np.mean([e["status"] for e in self.equipment.values()])
        clinical_score = avg_status
        efficiency_score = 1.0 - self.downtime / 10.0
        financial_score = avg_status * 0.9
        risk_penalty = 1.0 - avg_status if avg_status < 0.7 else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: avg_status,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 30
    def _get_kpis(self) -> KPIMetrics:
        avg_status = np.mean([e["status"] for e in self.equipment.values()])
        return KPIMetrics(
            clinical_outcomes={"equipment_status": avg_status},
            operational_efficiency={"downtime": self.downtime},
            financial_metrics={"maintenance_cost": (1.0 - avg_status) * 20000},
            patient_satisfaction=avg_status,
            risk_score=1.0 - avg_status,
            compliance_score=1.0,
            timestamp=self.time_step
        )

