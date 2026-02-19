"""Emergency Triage Environment - Optimizes ED triage and resource allocation"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator, ConditionSeverity
from simulator.hospital_simulator import HospitalSimulator, BedType

class EmergencyTriageEnv(HealthcareRLEnvironment):
    TRIAGE_LEVELS = ["resuscitation", "emergent", "urgent", "less_urgent", "non_urgent", "discharge"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(21,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.TRIAGE_LEVELS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        self.triage_queue = []
        self.triaged_patients = []
        self.wait_times = {}
    def _initialize_state(self) -> np.ndarray:
        self.triage_queue = [self.patient_generator.generate_patient() for _ in range(8)]
        self.triaged_patients = []
        self.wait_times = {}
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(21, dtype=np.float32)
        state[0] = len(self.triage_queue) / 20.0
        state[1] = len(self.triaged_patients) / 10.0
        if self.triage_queue:
            p = self.triage_queue[0]
            state[2] = p.risk_score
            state[3] = 1.0 if p.severity == ConditionSeverity.CRITICAL else 0.0
            state[4] = p.vitals.get("oxygen_saturation", 98) / 100.0
            state[5] = p.vitals.get("heart_rate", 72) / 150.0
            state[6] = p.vitals.get("bp_systolic", 120) / 200.0
            state[7] = p.vitals.get("temperature", 98.6) / 105.0
            state[8] = p.lab_results.get("lactate", 1.0) / 5.0
        hospital_state = self.hospital_simulator.get_state()
        state[9] = hospital_state.occupied_beds.get(BedType.EMERGENCY, 0) / 15.0
        state[10] = hospital_state.available_staff.get("physician", 0) / 20.0
        state[11] = hospital_state.available_staff.get("nurse", 0) / 80.0
        state[12] = len(self.wait_times) / 10.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        triage_level = self.TRIAGE_LEVELS[action]
        if self.triage_queue:
            patient = self.triage_queue.pop(0)
            self.triaged_patients.append({"patient": patient, "triage": triage_level})
            if triage_level == "resuscitation":
                self.hospital_simulator.admit_patient(patient, BedType.ICU)
            elif triage_level in ["emergent", "urgent"]:
                self.hospital_simulator.admit_patient(patient, BedType.EMERGENCY)
        self.hospital_simulator.update(1.0)
        return {"triage_level": triage_level}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = 1.0 - len(self.triage_queue) / 20.0
        efficiency_score = 1.0 - len(self.wait_times) / 10.0
        financial_score = len(self.triaged_patients) / 20.0
        risk_penalty = len([p for p in self.triage_queue if p.risk_score > 0.7]) * 0.2
        compliance_penalty = 0.0
        if self.triaged_patients:
            last_triage = self.triaged_patients[-1]
            if last_triage["patient"].risk_score > 0.8 and last_triage["triage"] not in ["resuscitation", "emergent"]:
                compliance_penalty = 0.3
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.triage_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or (len(self.triage_queue) == 0 and len(self.triaged_patients) > 0)
    def _get_kpis(self) -> KPIMetrics:
        hospital_state = self.hospital_simulator.get_state()
        return KPIMetrics(
            clinical_outcomes={"triage_accuracy": 1.0 - len([p for p in self.triaged_patients if p["patient"].risk_score > 0.7 and p["triage"] not in ["resuscitation", "emergent"]]) / max(1, len(self.triaged_patients))},
            operational_efficiency={"queue_length": len(self.triage_queue), "ed_occupancy": hospital_state.occupied_beds.get(BedType.EMERGENCY, 0) / 15.0},
            financial_metrics={"throughput": len(self.triaged_patients)},
            patient_satisfaction=1.0 - len(self.triage_queue) / 20.0,
            risk_score=len([p for p in self.triage_queue if p.risk_score > 0.7]) / 10.0,
            compliance_score=1.0 - (0.3 if self.triaged_patients and self.triaged_patients[-1]["patient"].risk_score > 0.8 and self.triaged_patients[-1]["triage"] not in ["resuscitation", "emergent"] else 0.0),
            timestamp=self.time_step
        )

