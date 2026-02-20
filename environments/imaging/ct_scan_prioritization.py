"""CT Scan Prioritization Environment - Prioritizes CT scans (Philips, GE)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class CTScanPrioritizationEnv(HealthcareRLEnvironment):
    PRIORITIES = ["stat", "urgent", "routine", "defer", "cancel", "batch"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(18,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.PRIORITIES))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.ct_queue = []
        self.processed_scans = []
        self.scanner_utilization = 0.0
        self.total_wait_time = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.ct_queue = [{"patient": self.patient_generator.generate_patient(), "urgency": self.np_random.uniform(0, 1), "scan_type": self.np_random.choice(["head", "chest", "abdomen", "pelvis"]), "wait_time": 0.0} for _ in range(15)]
        self.processed_scans = []
        self.scanner_utilization = 0.0
        self.total_wait_time = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(18, dtype=np.float32)
        state[0] = len(self.ct_queue) / 20.0
        state[1] = len(self.processed_scans) / 20.0
        if self.ct_queue:
            state[2] = self.ct_queue[0]["urgency"]
            state[3] = self.ct_queue[0]["wait_time"] / 7.0
            state[4] = self.ct_queue[0]["patient"].risk_score
        state[5] = self.scanner_utilization
        state[6] = np.mean([s["urgency"] for s in self.ct_queue[:5]]) if self.ct_queue else 0.0
        state[7] = np.mean([s["wait_time"] for s in self.ct_queue]) / 7.0 if self.ct_queue else 0.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        priority = self.PRIORITIES[action]
        if self.ct_queue:
            scan = self.ct_queue.pop(0)
            if priority not in ["cancel", "defer"]:
                self.processed_scans.append({**scan, "priority": priority})
                self.scanner_utilization = min(1.0, self.scanner_utilization + 0.1)
            elif priority == "defer":
                self.ct_queue.append(scan)
                scan["wait_time"] += 1.0
                self.total_wait_time += 1.0
        for scan in self.ct_queue:
            scan["wait_time"] += 0.5
            self.total_wait_time += 0.5
        return {"priority": priority}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = 1.0 - len([s for s in self.ct_queue if s["urgency"] > 0.8]) / 15.0
        efficiency_score = self.scanner_utilization
        financial_score = len(self.processed_scans) / 20.0
        risk_penalty = len([s for s in self.ct_queue if s["urgency"] > 0.9 and s["wait_time"] > 2.0]) * 0.2
        compliance_penalty = 0.2 if self.ct_queue and self.PRIORITIES[action] not in ["stat", "urgent"] and self.ct_queue[0]["urgency"] > 0.8 else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.ct_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 40 or len(self.ct_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"urgent_scans_waiting": len([s for s in self.ct_queue if s["urgency"] > 0.8])},
            operational_efficiency={"queue_length": len(self.ct_queue), "scanner_utilization": self.scanner_utilization},
            financial_metrics={"scans_processed": len(self.processed_scans)},
            patient_satisfaction=1.0 - len(self.ct_queue) / 20.0,
            risk_score=len([s for s in self.ct_queue if s["urgency"] > 0.9 and s["wait_time"] > 2.0]) / 15.0,
            compliance_score=1.0 - (0.2 if self.ct_queue and self.ct_queue[0]["urgency"] > 0.8 else 0.0),
            timestamp=self.time_step
        )

