"""
Clinical Trial Simulator
Simulates clinical trial enrollment, protocol adherence, and outcomes (Veeva, IQVIA)
"""

import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class TrialPhase(Enum):
    PHASE_1 = "phase_1"
    PHASE_2 = "phase_2"
    PHASE_3 = "phase_3"
    PHASE_4 = "phase_4"


class EnrollmentStatus(Enum):
    SCREENING = "screening"
    ENROLLED = "enrolled"
    ACTIVE = "active"
    COMPLETED = "completed"
    DISCONTINUED = "discontinued"
    LOST_TO_FOLLOWUP = "lost_to_followup"


class ProtocolDeviation(Enum):
    MISSED_VISIT = "missed_visit"
    WRONG_DOSAGE = "wrong_dosage"
    CONCOMITANT_MEDICATION = "concomitant_medication"
    OUT_OF_WINDOW = "out_of_window"
    INCLUSION_EXCLUSION_VIOLATION = "inclusion_exclusion_violation"


@dataclass
class TrialPatient:
    """Clinical trial patient representation"""
    patient_id: str
    trial_id: str
    enrollment_date: float
    status: EnrollmentStatus
    treatment_arm: str
    visit_schedule: List[float]
    completed_visits: List[float] = field(default_factory=list)
    deviations: List[ProtocolDeviation] = field(default_factory=list)
    adverse_events: List[str] = field(default_factory=list)
    efficacy_score: float = 0.0
    dropout_probability: float = 0.1


@dataclass
class TrialProtocol:
    """Clinical trial protocol definition"""
    trial_id: str
    phase: TrialPhase
    target_enrollment: int
    current_enrollment: int
    treatment_arms: List[str]
    inclusion_criteria: List[str]
    exclusion_criteria: List[str]
    primary_endpoint: str
    visit_schedule_days: List[int]
    duration_days: int


@dataclass
class TrialState:
    """Current trial state"""
    trial_id: str
    phase: TrialPhase
    enrollment_rate: float
    target_enrollment: int
    current_enrollment: int
    screening_pool: int
    active_patients: int
    completed_patients: int
    dropout_rate: float
    protocol_deviation_rate: float
    enrollment_on_track: bool
    time: float = 0.0


class ClinicalTrialSimulator:
    """
    Simulates clinical trial operations
    Mimics Veeva and IQVIA clinical trial management systems
    """
    
    def __init__(
        self,
        trial_id: str,
        phase: TrialPhase = TrialPhase.PHASE_3,
        target_enrollment: int = 300,
        seed: Optional[int] = None
    ):
        self.rng = np.random.default_rng(seed) if seed else np.random.default_rng()
        
        self.trial_id = trial_id
        self.phase = phase
        
        # Protocol definition
        self.protocol = TrialProtocol(
            trial_id=trial_id,
            phase=phase,
            target_enrollment=target_enrollment,
            current_enrollment=0,
            treatment_arms=["control", "treatment"],
            inclusion_criteria=["age_18_75", "diagnosis_confirmed", "ecog_0_1"],
            exclusion_criteria=["pregnancy", "severe_comorbidity", "concomitant_medication"],
            primary_endpoint="overall_survival",
            visit_schedule_days=[0, 7, 14, 28, 56, 84, 112, 140],
            duration_days=140
        )
        
        self.patients: Dict[str, TrialPatient] = {}
        self.screening_pool: List[str] = []
        self.enrollment_history: List[Dict[str, Any]] = []
        
        self.time = 0.0
    
    def add_to_screening_pool(self, patient_id: str) -> bool:
        """Add patient to screening pool"""
        if patient_id not in self.screening_pool:
            self.screening_pool.append(patient_id)
            return True
        return False
    
    def screen_patient(self, patient_id: str) -> bool:
        """Screen patient for eligibility"""
        if patient_id not in self.screening_pool:
            return False
        
        # Simulate screening success (60% pass rate)
        screening_success = self.rng.random() < 0.6
        
        if screening_success:
            self.screening_pool.remove(patient_id)
            return True
        
        return False
    
    def enroll_patient(
        self,
        patient_id: str,
        treatment_arm: Optional[str] = None
    ) -> Optional[TrialPatient]:
        """Enroll patient in trial"""
        if self.protocol.current_enrollment >= self.protocol.target_enrollment:
            return None
        
        if treatment_arm is None:
            treatment_arm = self.rng.choice(self.protocol.treatment_arms)
        
        # Generate visit schedule
        visit_schedule = [self.time + days for days in self.protocol.visit_schedule_days]
        
        patient = TrialPatient(
            patient_id=patient_id,
            trial_id=self.trial_id,
            enrollment_date=self.time,
            status=EnrollmentStatus.ENROLLED,
            treatment_arm=treatment_arm,
            visit_schedule=visit_schedule,
            dropout_probability=self.rng.uniform(0.05, 0.20)
        )
        
        self.patients[patient_id] = patient
        self.protocol.current_enrollment += 1
        
        self.enrollment_history.append({
            "patient_id": patient_id,
            "enrollment_date": self.time,
            "treatment_arm": treatment_arm
        })
        
        return patient
    
    def record_visit(self, patient_id: str, visit_date: float) -> bool:
        """Record patient visit"""
        if patient_id not in self.patients:
            return False
        
        patient = self.patients[patient_id]
        
        # Check if visit is on schedule
        expected_visits = [v for v in patient.visit_schedule if v <= visit_date]
        if expected_visits and visit_date not in patient.completed_visits:
            # Check for protocol deviation
            if expected_visits:
                expected_visit = min(expected_visits, key=lambda x: abs(x - visit_date))
                if abs(visit_date - expected_visit) > 7:  # More than 7 days off
                    patient.deviations.append(ProtocolDeviation.OUT_OF_WINDOW)
            
            patient.completed_visits.append(visit_date)
            patient.status = EnrollmentStatus.ACTIVE
            
            # Update efficacy score
            patient.efficacy_score = self._calculate_efficacy_score(patient)
            
            return True
        
        return False
    
    def _calculate_efficacy_score(self, patient: TrialPatient) -> float:
        """Calculate patient efficacy score"""
        base_score = self.rng.uniform(0.3, 0.9)
        
        # Treatment arm effect
        if patient.treatment_arm == "treatment":
            base_score += 0.15
        
        # Protocol adherence penalty
        if patient.deviations:
            base_score -= len(patient.deviations) * 0.05
        
        return max(0.0, min(1.0, base_score))
    
    def record_deviation(
        self,
        patient_id: str,
        deviation_type: ProtocolDeviation
    ) -> bool:
        """Record protocol deviation"""
        if patient_id not in self.patients:
            return False
        
        patient = self.patients[patient_id]
        if deviation_type not in patient.deviations:
            patient.deviations.append(deviation_type)
        
        return True
    
    def discontinue_patient(self, patient_id: str, reason: str = "adverse_event") -> bool:
        """Discontinue patient from trial"""
        if patient_id not in self.patients:
            return False
        
        patient = self.patients[patient_id]
        patient.status = EnrollmentStatus.DISCONTINUED
        
        return True
    
    def check_dropout(self, patient_id: str) -> bool:
        """Check if patient drops out"""
        if patient_id not in self.patients:
            return False
        
        patient = self.patients[patient_id]
        
        # Calculate dropout probability based on time and deviations
        dropout_prob = patient.dropout_probability
        if patient.deviations:
            dropout_prob += len(patient.deviations) * 0.1
        
        if self.rng.random() < dropout_prob:
            patient.status = EnrollmentStatus.LOST_TO_FOLLOWUP
            return True
        
        return False
    
    def update(self, time_delta: float):
        """Update simulator state"""
        self.time += time_delta
        
        # Check for dropouts
        for patient_id in list(self.patients.keys()):
            if self.patients[patient_id].status == EnrollmentStatus.ACTIVE:
                self.check_dropout(patient_id)
        
        # Auto-complete visits for some patients
        for patient in self.patients.values():
            if patient.status == EnrollmentStatus.ACTIVE:
                upcoming_visits = [v for v in patient.visit_schedule 
                                 if v <= self.time and v not in patient.completed_visits]
                for visit_date in upcoming_visits:
                    # 80% chance of completing visit
                    if self.rng.random() < 0.8:
                        self.record_visit(patient.patient_id, visit_date)
                    else:
                        patient.deviations.append(ProtocolDeviation.MISSED_VISIT)
    
    def get_state(self) -> TrialState:
        """Get current trial state"""
        active_patients = sum(1 for p in self.patients.values() 
                            if p.status == EnrollmentStatus.ACTIVE)
        completed_patients = sum(1 for p in self.patients.values() 
                               if p.status == EnrollmentStatus.COMPLETED)
        
        total_enrolled = len(self.patients)
        dropout_rate = sum(1 for p in self.patients.values() 
                         if p.status == EnrollmentStatus.DISCONTINUED or 
                         p.status == EnrollmentStatus.LOST_TO_FOLLOWUP) / total_enrolled if total_enrolled > 0 else 0.0
        
        patients_with_deviations = sum(1 for p in self.patients.values() if p.deviations)
        deviation_rate = patients_with_deviations / total_enrolled if total_enrolled > 0 else 0.0
        
        # Enrollment rate (patients per day)
        if self.enrollment_history:
            days_elapsed = self.time - min(e["enrollment_date"] for e in self.enrollment_history)
            enrollment_rate = total_enrolled / days_elapsed if days_elapsed > 0 else 0.0
        else:
            enrollment_rate = 0.0
        
        # Check if on track (should enroll 80% of target in 80% of time)
        expected_enrollment = self.protocol.target_enrollment * 0.8
        enrollment_on_track = self.protocol.current_enrollment >= expected_enrollment
        
        return TrialState(
            trial_id=self.trial_id,
            phase=self.phase,
            enrollment_rate=enrollment_rate,
            target_enrollment=self.protocol.target_enrollment,
            current_enrollment=self.protocol.current_enrollment,
            screening_pool=len(self.screening_pool),
            active_patients=active_patients,
            completed_patients=completed_patients,
            dropout_rate=dropout_rate,
            protocol_deviation_rate=deviation_rate,
            enrollment_on_track=enrollment_on_track,
            time=self.time
        )
    
    def reset(self):
        """Reset simulator to initial state"""
        self.patients = {}
        self.screening_pool = []
        self.enrollment_history = []
        self.protocol.current_enrollment = 0
        self.time = 0.0
    
    def close(self):
        """Clean up resources"""
        pass

