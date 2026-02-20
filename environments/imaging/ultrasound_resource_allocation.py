"""Ultrasound Resource Allocation Environment - Allocates ultrasound resources (Philips, GE)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class UltrasoundResourceAllocationEnv(HealthcareRLEnvironment):
    ACTIONS = ["allocate_portable", "allocate_fixed", "schedule_routine", "defer", "cancel", "batch_scan"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.ultrasound_queue = []
        self.allocated_scans = []
        self.resource_utilization = {"portable": 0.0, "fixed": 0.0}
    def _initialize_state(self) -> np.ndarray:
        self.ultrasound_queue = [{"patient": self.patient_generator.generate_patient(), "urgency": self.np_random.uniform(0, 1), "scan_type": self.np_random.choice(["abdomen", "pelvis", "cardiac", "vascular"]), "wait_time": 0.0} for _ in range(15)]
        self.allocated_scans = []
        self.resource_utilization = {"portable": 0.0, "fixed": 0.0}
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.ultrasound_queue) / 20.0
        state[1] = len(self.allocated_scans) / 20.0
        if self.ultrasound_queue:
            state[2] = self.ultrasound_queue[0]["urgency"]
            state[3] = self.ultrasound_queue[0]["wait_time"] / 7.0
            state[4] = self.ultrasound_queue[0]["patient"].risk_score
        state[5] = self.resource_utilization["portable"]
        state[6] = self.resource_utilization["fixed"]
        state[7] = np.mean([s["urgency"] for s in self.ultrasound_queue[:5]]) if self.ultrasound_queue else 0.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.ultrasound_queue:
            scan = self.ultrasound_queue.pop(0)
            if action_name == "allocate_portable":
                self.allocated_scans.append({**scan, "resource": "portable"})
                self.resource_utilization["portable"] = min(1.0, self.resource_utilization["portable"] + 0.1)
            elif action_name == "allocate_fixed":
                self.allocated_scans.append({**scan, "resource": "fixed"})
                self.resource_utilization["fixed"] = min(1.0, self.resource_utilization["fixed"] + 0.1)
            elif action_name == "schedule_routine":
                self.allocated_scans.append({**scan, "resource": "fixed"})
                self.resource_utilization["fixed"] = min(1.0, self.resource_utilization["fixed"] + 0.1)
            elif action_name == "defer":
                self.ultrasound_queue.append(scan)
                scan["wait_time"] += 1.0
            elif action_name == "batch_scan":
                similar_scans = [s for s in self.ultrasound_queue if s["scan_type"] == scan["scan_type"]][:2]
                for s in similar_scans:
                    self.allocated_scans.append({**s, "resource": "fixed"})
                    if s in self.ultrasound_queue:
                        self.ultrasound_queue.remove(s)
                    self.resource_utilization["fixed"] = min(1.0, self.resource_utilization["fixed"] + 0.1)
        for scan in self.ultrasound_queue:
            scan["wait_time"] += 0.5
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = 1.0 - len([s for s in self.ultrasound_queue if s["urgency"] > 0.8]) / 15.0
        efficiency_score = np.mean(list(self.resource_utilization.values()))
        financial_score = len(self.allocated_scans) / 20.0
        risk_penalty = len([s for s in self.ultrasound_queue if s["urgency"] > 0.9 and s["wait_time"] > 2.0]) * 0.2
        compliance_penalty = 0.2 if self.ultrasound_queue and self.ultrasound_queue[0]["urgency"] > 0.8 and self.ACTIONS[action] == "defer" else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.ultrasound_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 40 or len(self.ultrasound_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"urgent_scans_waiting": len([s for s in self.ultrasound_queue if s["urgency"] > 0.8])},
            operational_efficiency={"queue_length": len(self.ultrasound_queue), "resource_utilization": np.mean(list(self.resource_utilization.values()))},
            financial_metrics={"scans_allocated": len(self.allocated_scans)},
            patient_satisfaction=1.0 - len(self.ultrasound_queue) / 20.0,
            risk_score=len([s for s in self.ultrasound_queue if s["urgency"] > 0.9 and s["wait_time"] > 2.0]) / 15.0,
            compliance_score=1.0 - (0.2 if self.ultrasound_queue and self.ultrasound_queue[0]["urgency"] > 0.8 else 0.0),
            timestamp=self.time_step
        )

