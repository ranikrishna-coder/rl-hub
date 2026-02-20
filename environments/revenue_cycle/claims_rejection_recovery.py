"""Claims Rejection Recovery Environment - Recovers rejected claims (Change Healthcare)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class ClaimsRejectionRecoveryEnv(HealthcareRLEnvironment):
    ACTIONS = ["resubmit_claim", "correct_and_resubmit", "appeal_denial", "write_off", "defer", "escalate"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.rejected_claims = []
        self.recovered_claims = []
        self.recovery_rate = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.rejected_claims = [{"patient": self.patient_generator.generate_patient(), "claim_amount": self.np_random.uniform(500, 5000), "rejection_reason": self.np_random.choice(["coding", "documentation", "eligibility", "duplicate"]), "recovery_probability": self.np_random.uniform(0.2, 0.9), "days_since_rejection": 0.0} for _ in range(15)]
        self.recovered_claims = []
        self.recovery_rate = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.rejected_claims) / 20.0
        state[1] = len(self.recovered_claims) / 20.0
        if self.rejected_claims:
            state[2] = self.rejected_claims[0]["claim_amount"] / 5000.0
            state[3] = self.rejected_claims[0]["recovery_probability"]
            state[4] = self.rejected_claims[0]["days_since_rejection"] / 90.0
        state[5] = self.recovery_rate
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.rejected_claims:
            claim = self.rejected_claims.pop(0)
            if action_name == "resubmit_claim":
                recovered = claim["claim_amount"] * claim["recovery_probability"] * 0.6
                self.recovered_claims.append({**claim, "status": "resubmitted", "recovered": recovered})
                self.recovery_rate = min(1.0, self.recovery_rate + recovered / 10000.0)
            elif action_name == "correct_and_resubmit":
                recovered = claim["claim_amount"] * min(1.0, claim["recovery_probability"] + 0.2)
                self.recovered_claims.append({**claim, "status": "corrected", "recovered": recovered})
                self.recovery_rate = min(1.0, self.recovery_rate + recovered / 10000.0)
            elif action_name == "appeal_denial":
                recovered = claim["claim_amount"] * min(1.0, claim["recovery_probability"] + 0.3)
                self.recovered_claims.append({**claim, "status": "appealed", "recovered": recovered})
                self.recovery_rate = min(1.0, self.recovery_rate + recovered / 10000.0)
            elif action_name == "write_off":
                self.recovered_claims.append({**claim, "status": "written_off", "recovered": 0.0})
            elif action_name == "escalate":
                recovered = claim["claim_amount"] * min(1.0, claim["recovery_probability"] + 0.4)
                self.recovered_claims.append({**claim, "status": "escalated", "recovered": recovered})
                self.recovery_rate = min(1.0, self.recovery_rate + recovered / 10000.0)
            elif action_name == "defer":
                claim["days_since_rejection"] += 7.0
                self.rejected_claims.append(claim)
        for claim in self.rejected_claims:
            claim["days_since_rejection"] += 1.0
            claim["recovery_probability"] = max(0.1, claim["recovery_probability"] - 0.01)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.recovery_rate
        efficiency_score = len(self.recovered_claims) / 20.0
        financial_score = self.recovery_rate
        risk_penalty = len([c for c in self.rejected_claims if c["days_since_rejection"] > 60 and c["recovery_probability"] < 0.3]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.rejected_claims) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.rejected_claims) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"recovery_rate": self.recovery_rate, "old_rejections_waiting": len([c for c in self.rejected_claims if c["days_since_rejection"] > 60])},
            operational_efficiency={"queue_length": len(self.rejected_claims), "claims_recovered": len(self.recovered_claims)},
            financial_metrics={"recovery_rate": self.recovery_rate},
            patient_satisfaction=1.0 - len(self.rejected_claims) / 20.0,
            risk_score=len([c for c in self.rejected_claims if c["days_since_rejection"] > 60 and c["recovery_probability"] < 0.3]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

