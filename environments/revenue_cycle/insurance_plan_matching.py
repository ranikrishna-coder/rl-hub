"""Insurance Plan Matching Environment - Matches insurance plans (Change Healthcare)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class InsurancePlanMatchingEnv(HealthcareRLEnvironment):
    ACTIONS = ["match_plan", "verify_eligibility", "update_plan", "flag_mismatch", "defer", "auto_match"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.matching_queue = []
        self.matched_plans = []
        self.matching_accuracy = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.matching_queue = [{"patient": self.patient_generator.generate_patient(), "plan_match_score": self.np_random.uniform(0.3, 1.0), "eligibility_status": self.np_random.choice(["active", "inactive", "unknown"]), "coverage_level": self.np_random.uniform(0.5, 1.0)} for _ in range(15)]
        self.matched_plans = []
        self.matching_accuracy = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.matching_queue) / 20.0
        state[1] = len(self.matched_plans) / 20.0
        if self.matching_queue:
            state[2] = self.matching_queue[0]["plan_match_score"]
            state[3] = 1.0 if self.matching_queue[0]["eligibility_status"] == "active" else (0.5 if self.matching_queue[0]["eligibility_status"] == "unknown" else 0.0)
            state[4] = self.matching_queue[0]["coverage_level"]
        state[5] = self.matching_accuracy
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.matching_queue:
            plan = self.matching_queue.pop(0)
            if action_name == "match_plan":
                if plan["plan_match_score"] > 0.7:
                    self.matched_plans.append({**plan, "status": "matched"})
                    self.matching_accuracy = min(1.0, self.matching_accuracy + plan["plan_match_score"] / 10.0)
                else:
                    plan["plan_match_score"] += 0.1
                    self.matching_queue.append(plan)
            elif action_name == "verify_eligibility":
                if plan["eligibility_status"] == "unknown":
                    plan["eligibility_status"] = "active" if self.np_random.random() > 0.3 else "inactive"
                plan["plan_match_score"] = min(1.0, plan["plan_match_score"] + 0.15)
                self.matching_queue.insert(0, plan)
            elif action_name == "update_plan":
                plan["plan_match_score"] = min(1.0, plan["plan_match_score"] + 0.2)
                plan["coverage_level"] = min(1.0, plan["coverage_level"] + 0.1)
                self.matched_plans.append({**plan, "status": "updated"})
                self.matching_accuracy = min(1.0, self.matching_accuracy + plan["plan_match_score"] / 8.0)
            elif action_name == "auto_match":
                if plan["plan_match_score"] > 0.8 and plan["eligibility_status"] == "active":
                    self.matched_plans.append({**plan, "status": "auto_matched"})
                    self.matching_accuracy = min(1.0, self.matching_accuracy + plan["plan_match_score"] / 10.0)
                else:
                    self.matching_queue.append(plan)
            elif action_name == "flag_mismatch":
                self.matched_plans.append({**plan, "status": "flagged"})
            elif action_name == "defer":
                self.matching_queue.append(plan)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.matching_accuracy
        efficiency_score = len(self.matched_plans) / 20.0
        financial_score = self.matching_accuracy
        risk_penalty = len([p for p in self.matching_queue if p["plan_match_score"] < 0.5]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.matching_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.matching_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"matching_accuracy": self.matching_accuracy, "low_match_waiting": len([p for p in self.matching_queue if p["plan_match_score"] < 0.5])},
            operational_efficiency={"queue_length": len(self.matching_queue), "plans_matched": len(self.matched_plans)},
            financial_metrics={"matching_accuracy": self.matching_accuracy},
            patient_satisfaction=1.0 - len(self.matching_queue) / 20.0,
            risk_score=len([p for p in self.matching_queue if p["plan_match_score"] < 0.5]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

