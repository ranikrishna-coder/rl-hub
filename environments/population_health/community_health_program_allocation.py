"""Community Health Program Allocation Environment - Allocates community health programs (Health Catalyst, Innovaccer)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class CommunityHealthProgramAllocationEnv(HealthcareRLEnvironment):
    ACTIONS = ["allocate_wellness", "allocate_chronic_disease", "allocate_mental_health", "allocate_preventive", "defer", "optimize"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.program_queue = []
        self.allocated_programs = []
        self.program_impact = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.program_queue = [{"patient": self.patient_generator.generate_patient(), "program_type": self.np_random.choice(["wellness", "chronic_disease", "mental_health", "preventive"]), "impact_score": self.np_random.uniform(0, 1), "cost": self.np_random.uniform(500, 5000)} for _ in range(15)]
        self.allocated_programs = []
        self.program_impact = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.program_queue) / 20.0
        state[1] = len(self.allocated_programs) / 20.0
        if self.program_queue:
            state[2] = self.program_queue[0]["impact_score"]
            state[3] = self.program_queue[0]["cost"] / 5000.0
        state[4] = self.program_impact
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.program_queue:
            program = self.program_queue.pop(0)
            if action_name in ["allocate_wellness", "allocate_chronic_disease", "allocate_mental_health", "allocate_preventive"]:
                self.allocated_programs.append({**program, "allocated": True})
                self.program_impact = min(1.0, self.program_impact + program["impact_score"] / 10.0)
            elif action_name == "optimize":
                # Optimize program selection
                if program["impact_score"] / program["cost"] > 0.001:
                    self.allocated_programs.append({**program, "allocated": True, "optimized": True})
                    self.program_impact = min(1.0, self.program_impact + program["impact_score"] / 8.0)
                else:
                    self.program_queue.append(program)
            elif action_name == "defer":
                self.program_queue.append(program)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.program_impact
        efficiency_score = len(self.allocated_programs) / 20.0
        financial_score = len(self.allocated_programs) / 20.0
        risk_penalty = len([p for p in self.program_queue if p["impact_score"] > 0.8]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.program_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.program_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"program_impact": self.program_impact, "high_impact_waiting": len([p for p in self.program_queue if p["impact_score"] > 0.8])},
            operational_efficiency={"queue_length": len(self.program_queue), "programs_allocated": len(self.allocated_programs)},
            financial_metrics={"allocated_count": len(self.allocated_programs)},
            patient_satisfaction=1.0 - len(self.program_queue) / 20.0,
            risk_score=len([p for p in self.program_queue if p["impact_score"] > 0.8]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

