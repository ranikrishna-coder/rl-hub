"""Trial Protocol Optimization Environment - Optimizes trial protocols (Veeva, IQVIA)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class TrialProtocolOptimizationEnv(HealthcareRLEnvironment):
    ACTIONS = ["optimize_dosing", "adjust_endpoints", "modify_inclusion", "streamline_procedures", "defer", "finalize"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.protocol_queue = []
        self.optimized_protocols = []
        self.protocol_efficiency = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.protocol_queue = [{"patient": self.patient_generator.generate_patient(), "protocol_complexity": self.np_random.uniform(0, 1), "optimization_potential": self.np_random.uniform(0.3, 1.0), "compliance_risk": self.np_random.uniform(0, 0.5)} for _ in range(15)]
        self.optimized_protocols = []
        self.protocol_efficiency = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.protocol_queue) / 20.0
        state[1] = len(self.optimized_protocols) / 20.0
        if self.protocol_queue:
            state[2] = self.protocol_queue[0]["protocol_complexity"]
            state[3] = self.protocol_queue[0]["optimization_potential"]
            state[4] = self.protocol_queue[0]["compliance_risk"]
        state[5] = self.protocol_efficiency
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.protocol_queue:
            protocol = self.protocol_queue.pop(0)
            if action_name == "optimize_dosing":
                protocol["protocol_complexity"] = max(0, protocol["protocol_complexity"] - 0.15)
                protocol["compliance_risk"] = max(0, protocol["compliance_risk"] - 0.1)
                self.optimized_protocols.append({**protocol, "optimization": "dosing"})
                self.protocol_efficiency = min(1.0, self.protocol_efficiency + 0.1)
            elif action_name == "adjust_endpoints":
                protocol["protocol_complexity"] = max(0, protocol["protocol_complexity"] - 0.1)
                self.optimized_protocols.append({**protocol, "optimization": "endpoints"})
                self.protocol_efficiency = min(1.0, self.protocol_efficiency + 0.08)
            elif action_name == "modify_inclusion":
                protocol["optimization_potential"] = min(1.0, protocol["optimization_potential"] + 0.15)
                self.optimized_protocols.append({**protocol, "optimization": "inclusion"})
                self.protocol_efficiency = min(1.0, self.protocol_efficiency + 0.1)
            elif action_name == "streamline_procedures":
                protocol["protocol_complexity"] = max(0, protocol["protocol_complexity"] - 0.2)
                protocol["compliance_risk"] = max(0, protocol["compliance_risk"] - 0.15)
                self.optimized_protocols.append({**protocol, "optimization": "streamlined"})
                self.protocol_efficiency = min(1.0, self.protocol_efficiency + 0.15)
            elif action_name == "finalize":
                self.optimized_protocols.append({**protocol, "optimization": "finalized"})
                self.protocol_efficiency = min(1.0, self.protocol_efficiency + 0.12)
            elif action_name == "defer":
                self.protocol_queue.append(protocol)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.protocol_efficiency
        efficiency_score = len(self.optimized_protocols) / 20.0
        financial_score = len(self.optimized_protocols) / 20.0
        risk_penalty = len([p for p in self.protocol_queue if p["compliance_risk"] > 0.4]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.protocol_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.protocol_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"protocol_efficiency": self.protocol_efficiency, "high_risk_waiting": len([p for p in self.protocol_queue if p["compliance_risk"] > 0.4])},
            operational_efficiency={"queue_length": len(self.protocol_queue), "protocols_optimized": len(self.optimized_protocols)},
            financial_metrics={"optimized_count": len(self.optimized_protocols)},
            patient_satisfaction=1.0 - len(self.protocol_queue) / 20.0,
            risk_score=len([p for p in self.protocol_queue if p["compliance_risk"] > 0.4]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

