"""Trial Site Resource Allocation Environment - Allocates trial site resources (Veeva, IQVIA)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class TrialSiteResourceAllocationEnv(HealthcareRLEnvironment):
    ACTIONS = ["allocate_site", "optimize_capacity", "add_resources", "reallocate", "defer", "close_site"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.site_queue = []
        self.allocated_sites = []
        self.resource_utilization = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.site_queue = [{"patient": self.patient_generator.generate_patient(), "site_capacity": self.np_random.uniform(0.3, 1.0), "resource_need": self.np_random.uniform(0, 1), "enrollment_potential": self.np_random.uniform(0.4, 1.0)} for _ in range(15)]
        self.allocated_sites = []
        self.resource_utilization = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.site_queue) / 20.0
        state[1] = len(self.allocated_sites) / 20.0
        if self.site_queue:
            state[2] = self.site_queue[0]["site_capacity"]
            state[3] = self.site_queue[0]["resource_need"]
            state[4] = self.site_queue[0]["enrollment_potential"]
        state[5] = self.resource_utilization
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.site_queue:
            site = self.site_queue.pop(0)
            if action_name == "allocate_site":
                self.allocated_sites.append({**site, "status": "allocated"})
                self.resource_utilization = min(1.0, self.resource_utilization + site["site_capacity"] / 10.0)
            elif action_name == "optimize_capacity":
                site["site_capacity"] = min(1.0, site["site_capacity"] + 0.15)
                self.allocated_sites.append({**site, "status": "optimized"})
                self.resource_utilization = min(1.0, self.resource_utilization + site["site_capacity"] / 8.0)
            elif action_name == "add_resources":
                site["site_capacity"] = min(1.0, site["site_capacity"] + 0.2)
                site["resource_need"] = max(0, site["resource_need"] - 0.2)
                self.allocated_sites.append({**site, "status": "resources_added"})
                self.resource_utilization = min(1.0, self.resource_utilization + site["site_capacity"] / 7.0)
            elif action_name == "reallocate":
                site["site_capacity"] = min(1.0, site["site_capacity"] + 0.1)
                self.allocated_sites.append({**site, "status": "reallocated"})
                self.resource_utilization = min(1.0, self.resource_utilization + site["site_capacity"] / 9.0)
            elif action_name == "close_site":
                self.allocated_sites.append({**site, "status": "closed"})
            elif action_name == "defer":
                self.site_queue.append(site)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.resource_utilization
        efficiency_score = len(self.allocated_sites) / 20.0
        financial_score = len(self.allocated_sites) / 20.0
        risk_penalty = len([s for s in self.site_queue if s["resource_need"] > 0.8]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.site_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.site_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"resource_utilization": self.resource_utilization, "high_need_waiting": len([s for s in self.site_queue if s["resource_need"] > 0.8])},
            operational_efficiency={"queue_length": len(self.site_queue), "sites_allocated": len(self.allocated_sites)},
            financial_metrics={"allocated_count": len(self.allocated_sites)},
            patient_satisfaction=1.0 - len(self.site_queue) / 20.0,
            risk_score=len([s for s in self.site_queue if s["resource_need"] > 0.8]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

