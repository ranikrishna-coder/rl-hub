"""Risk Stratification Environment - Stratifies patient populations by risk (Health Catalyst, Innovaccer)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class RiskStratificationEnv(HealthcareRLEnvironment):
    STRATA = ["low_risk", "moderate_risk", "high_risk", "critical_risk", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.STRATA))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.patient_population = []
        self.stratified_patients = {"low_risk": [], "moderate_risk": [], "high_risk": [], "critical_risk": []}
    def _initialize_state(self) -> np.ndarray:
        self.patient_population = self.patient_generator.generate_batch(20)
        self.stratified_patients = {k: [] for k in self.STRATA if k != "no_action"}
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.patient_population) / 30.0
        if self.patient_population:
            p = self.patient_population[0]
            state[1] = p.risk_score
            state[2] = p.age / 100.0
            state[3] = len(p.conditions) / 5.0
            state[4] = len(p.comorbidities) / 5.0
            state[5] = p.readmission_risk
        state[6] = len(self.stratified_patients["low_risk"]) / 10.0
        state[7] = len(self.stratified_patients["moderate_risk"]) / 10.0
        state[8] = len(self.stratified_patients["high_risk"]) / 10.0
        state[9] = len(self.stratified_patients["critical_risk"]) / 10.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        stratum = self.STRATA[action]
        if self.patient_population and stratum != "no_action":
            patient = self.patient_population.pop(0)
            self.stratified_patients[stratum].append(patient)
        return {"stratum": stratum}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        accuracy_score = 1.0
        if self.stratified_patients["critical_risk"]:
            avg_risk = np.mean([p.risk_score for p in self.stratified_patients["critical_risk"]])
            if avg_risk < 0.7:
                accuracy_score = 0.7
        efficiency_score = 1.0 - len(self.patient_population) / 30.0
        financial_score = len([p for p in self.stratified_patients["high_risk"] + self.stratified_patients["critical_risk"]]) / 20.0
        return {
            RewardComponent.CLINICAL: accuracy_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.patient_population) / 30.0,
            RewardComponent.RISK_PENALTY: len([p for p in self.patient_population if p.risk_score > 0.8]) / 10.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 25 or len(self.patient_population) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"high_risk_identified": len(self.stratified_patients["high_risk"]) + len(self.stratified_patients["critical_risk"])},
            operational_efficiency={"patients_stratified": sum(len(v) for v in self.stratified_patients.values())},
            financial_metrics={"risk_management_cost": sum(len(v) for v in self.stratified_patients.values()) * 100},
            patient_satisfaction=1.0 - len(self.patient_population) / 30.0,
            risk_score=len([p for p in self.patient_population if p.risk_score > 0.8]) / 10.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

