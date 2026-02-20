"""Contract Compliance Scoring Environment - Scores contract compliance (Change Healthcare)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class ContractComplianceScoringEnv(HealthcareRLEnvironment):
    ACTIONS = ["score_contract", "flag_violations", "optimize_compliance", "negotiate_terms", "defer", "escalate"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.contract_queue = []
        self.scored_contracts = []
        self.compliance_score = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.contract_queue = [{"patient": self.patient_generator.generate_patient(), "contract_value": self.np_random.uniform(10000, 100000), "compliance_risk": self.np_random.uniform(0, 1), "violations_count": self.np_random.integers(0, 5), "current_score": self.np_random.uniform(0.5, 1.0)} for _ in range(15)]
        self.scored_contracts = []
        self.compliance_score = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.contract_queue) / 20.0
        state[1] = len(self.scored_contracts) / 20.0
        if self.contract_queue:
            state[2] = self.contract_queue[0]["compliance_risk"]
            state[3] = self.contract_queue[0]["violations_count"] / 5.0
            state[4] = self.contract_queue[0]["current_score"]
        state[5] = self.compliance_score
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.contract_queue:
            contract = self.contract_queue.pop(0)
            if action_name == "score_contract":
                score = contract["current_score"] - (contract["violations_count"] * 0.1)
                contract["current_score"] = max(0, score)
                self.scored_contracts.append({**contract, "scored": True})
                self.compliance_score = min(1.0, self.compliance_score + contract["current_score"] / 10.0)
            elif action_name == "flag_violations":
                contract["violations_count"] = max(0, contract["violations_count"] - 1)
                contract["compliance_risk"] = max(0, contract["compliance_risk"] - 0.1)
                self.contract_queue.insert(0, contract)
            elif action_name == "optimize_compliance":
                contract["current_score"] = min(1.0, contract["current_score"] + 0.15)
                contract["violations_count"] = max(0, contract["violations_count"] - 1)
                contract["compliance_risk"] = max(0, contract["compliance_risk"] - 0.15)
                self.scored_contracts.append({**contract, "optimized": True})
                self.compliance_score = min(1.0, self.compliance_score + contract["current_score"] / 8.0)
            elif action_name == "negotiate_terms":
                contract["current_score"] = min(1.0, contract["current_score"] + 0.1)
                contract["compliance_risk"] = max(0, contract["compliance_risk"] - 0.1)
                self.scored_contracts.append({**contract, "negotiated": True})
                self.compliance_score = min(1.0, self.compliance_score + contract["current_score"] / 10.0)
            elif action_name == "escalate":
                contract["current_score"] = min(1.0, contract["current_score"] + 0.2)
                self.scored_contracts.append({**contract, "escalated": True})
                self.compliance_score = min(1.0, self.compliance_score + contract["current_score"] / 7.0)
            elif action_name == "defer":
                self.contract_queue.append(contract)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.compliance_score
        efficiency_score = len(self.scored_contracts) / 20.0
        financial_score = self.compliance_score
        risk_penalty = len([c for c in self.contract_queue if c["compliance_risk"] > 0.8]) * 0.2
        compliance_penalty = len([c for c in self.contract_queue if c["violations_count"] > 3]) * 0.2
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.contract_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.contract_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"compliance_score": self.compliance_score, "high_risk_contracts": len([c for c in self.contract_queue if c["compliance_risk"] > 0.8])},
            operational_efficiency={"queue_length": len(self.contract_queue), "contracts_scored": len(self.scored_contracts)},
            financial_metrics={"compliance_score": self.compliance_score},
            patient_satisfaction=1.0 - len(self.contract_queue) / 20.0,
            risk_score=len([c for c in self.contract_queue if c["compliance_risk"] > 0.8]) / 15.0,
            compliance_score=1.0 - (len([c for c in self.contract_queue if c["violations_count"] > 3]) / 15.0),
            timestamp=self.time_step
        )

