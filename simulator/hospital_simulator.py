"""
Hospital Operations Simulator
Simulates hospital bed management, staffing, and resource allocation
"""

import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from .patient_generator import PatientProfile, PatientStatus, ConditionSeverity


class BedType(Enum):
    ICU = "icu"
    STEP_DOWN = "step_down"
    MEDICAL_SURGICAL = "medical_surgical"
    EMERGENCY = "emergency"
    OR = "or"
    PACU = "pacu"


class StaffType(Enum):
    PHYSICIAN = "physician"
    NURSE = "nurse"
    RESPIRATORY_THERAPIST = "respiratory_therapist"
    PHARMACIST = "pharmacist"
    TECHNICIAN = "technician"


@dataclass
class Bed:
    """Hospital bed representation"""
    bed_id: str
    bed_type: BedType
    is_occupied: bool
    patient_id: Optional[str] = None
    admission_time: Optional[float] = None
    expected_discharge: Optional[float] = None


@dataclass
class StaffMember:
    """Staff member representation"""
    staff_id: str
    staff_type: StaffType
    is_available: bool
    current_patients: List[str] = field(default_factory=list)
    max_capacity: int = 5
    skill_level: float = 1.0


@dataclass
class HospitalState:
    """Current state of hospital operations"""
    total_beds: Dict[BedType, int]
    occupied_beds: Dict[BedType, int]
    available_staff: Dict[StaffType, int]
    total_staff: Dict[StaffType, int]
    patient_queue: List[str]
    wait_times: Dict[str, float]
    throughput: float
    occupancy_rate: float
    staff_utilization: Dict[StaffType, float]
    time: float = 0.0


class HospitalSimulator:
    """
    Simulates hospital operations including bed management and staffing
    """
    
    def __init__(
        self,
        num_icu_beds: int = 20,
        num_step_down: int = 30,
        num_med_surg: int = 100,
        num_emergency: int = 15,
        num_or: int = 10,
        num_pacu: int = 8,
        seed: Optional[int] = None
    ):
        self.rng = np.random.default_rng(seed) if seed else np.random.default_rng()
        
        # Initialize beds
        self.beds: Dict[str, Bed] = {}
        self._initialize_beds(num_icu_beds, num_step_down, num_med_surg, 
                             num_emergency, num_or, num_pacu)
        
        # Initialize staff
        self.staff: Dict[str, StaffMember] = {}
        self._initialize_staff()
        
        # Patient tracking
        self.patients: Dict[str, PatientProfile] = {}
        self.patient_queue: List[str] = []
        self.wait_times: Dict[str, float] = {}
        
        self.time = 0.0
    
    def _initialize_beds(self, icu: int, step_down: int, med_surg: int, 
                        emergency: int, or_beds: int, pacu: int):
        """Initialize hospital beds"""
        bed_configs = [
            (BedType.ICU, icu),
            (BedType.STEP_DOWN, step_down),
            (BedType.MEDICAL_SURGICAL, med_surg),
            (BedType.EMERGENCY, emergency),
            (BedType.OR, or_beds),
            (BedType.PACU, pacu)
        ]
        
        for bed_type, count in bed_configs:
            for i in range(count):
                bed_id = f"{bed_type.value}_{i}"
                self.beds[bed_id] = Bed(
                    bed_id=bed_id,
                    bed_type=bed_type,
                    is_occupied=False
                )
    
    def _initialize_staff(self):
        """Initialize hospital staff"""
        staff_configs = [
            (StaffType.PHYSICIAN, 20),
            (StaffType.NURSE, 80),
            (StaffType.RESPIRATORY_THERAPIST, 10),
            (StaffType.PHARMACIST, 5),
            (StaffType.TECHNICIAN, 15)
        ]
        
        for staff_type, count in staff_configs:
            for i in range(count):
                staff_id = f"{staff_type.value}_{i}"
                self.staff[staff_id] = StaffMember(
                    staff_id=staff_id,
                    staff_type=staff_type,
                    is_available=True,
                    max_capacity=5 if staff_type == StaffType.NURSE else 10,
                    skill_level=self.rng.uniform(0.8, 1.0)
                )
    
    def admit_patient(self, patient: PatientProfile, bed_type: Optional[BedType] = None) -> bool:
        """Admit patient to hospital"""
        if bed_type is None:
            bed_type = self._determine_bed_type(patient)
        
        # Find available bed
        bed = self._find_available_bed(bed_type)
        if bed is None:
            # Add to queue
            self.patient_queue.append(patient.patient_id)
            self.wait_times[patient.patient_id] = 0.0
            return False
        
        # Assign bed
        bed.is_occupied = True
        bed.patient_id = patient.patient_id
        bed.admission_time = self.time
        bed.expected_discharge = self.time + self._estimate_los(patient)
        
        # Assign staff
        self._assign_staff(patient)
        
        # Track patient
        self.patients[patient.patient_id] = patient
        
        return True
    
    def _determine_bed_type(self, patient: PatientProfile) -> BedType:
        """Determine appropriate bed type for patient"""
        if patient.severity.value == "critical" or patient.status == PatientStatus.CRITICAL:
            return BedType.ICU
        elif patient.severity.value == "severe":
            return BedType.STEP_DOWN
        elif "surgery" in patient.conditions:
            return BedType.OR
        else:
            return BedType.MEDICAL_SURGICAL
    
    def _find_available_bed(self, bed_type: BedType) -> Optional[Bed]:
        """Find available bed of specified type"""
        for bed in self.beds.values():
            if bed.bed_type == bed_type and not bed.is_occupied:
                return bed
        return None
    
    def _estimate_los(self, patient: PatientProfile) -> float:
        """Estimate length of stay"""
        base_los = {
            ConditionSeverity.MILD: 2.0,
            ConditionSeverity.MODERATE: 4.0,
            ConditionSeverity.SEVERE: 7.0,
            ConditionSeverity.CRITICAL: 10.0
        }
        
        los = base_los.get(patient.severity, 5.0)
        los += len(patient.comorbidities) * 0.5
        los += self.rng.normal(0, los * 0.3)
        
        return max(1.0, los)
    
    def _assign_staff(self, patient: PatientProfile):
        """Assign staff to patient"""
        required_staff = {
            StaffType.PHYSICIAN: 1,
            StaffType.NURSE: 1 if patient.severity.value in ["mild", "moderate"] else 2
        }
        
        for staff_type, count in required_staff.items():
            assigned = 0
            for staff in self.staff.values():
                if (staff.staff_type == staff_type and 
                    staff.is_available and 
                    len(staff.current_patients) < staff.max_capacity):
                    staff.current_patients.append(patient.patient_id)
                    staff.is_available = len(staff.current_patients) < staff.max_capacity
                    assigned += 1
                    if assigned >= count:
                        break
    
    def discharge_patient(self, patient_id: str) -> bool:
        """Discharge patient from hospital"""
        if patient_id not in self.patients:
            return False
        
        # Free bed
        for bed in self.beds.values():
            if bed.patient_id == patient_id:
                bed.is_occupied = False
                bed.patient_id = None
                bed.admission_time = None
                bed.expected_discharge = None
                break
        
        # Free staff
        for staff in self.staff.values():
            if patient_id in staff.current_patients:
                staff.current_patients.remove(patient_id)
                staff.is_available = len(staff.current_patients) < staff.max_capacity
        
        # Remove patient
        del self.patients[patient_id]
        
        # Process queue
        if self.patient_queue:
            next_patient_id = self.patient_queue.pop(0)
            if next_patient_id in self.wait_times:
                del self.wait_times[next_patient_id]
        
        return True
    
    def update(self, time_delta: float):
        """Update simulator state"""
        self.time += time_delta
        
        # Update wait times
        for patient_id in self.patient_queue:
            self.wait_times[patient_id] = self.wait_times.get(patient_id, 0.0) + time_delta
        
        # Check for discharges
        patients_to_discharge = []
        for patient_id, patient in self.patients.items():
            for bed in self.beds.values():
                if bed.patient_id == patient_id and bed.expected_discharge:
                    if self.time >= bed.expected_discharge:
                        patients_to_discharge.append(patient_id)
                    break
        
        for patient_id in patients_to_discharge:
            self.discharge_patient(patient_id)
    
    def get_state(self) -> HospitalState:
        """Get current hospital state"""
        total_beds = {}
        occupied_beds = {}
        
        for bed_type in BedType:
            total_beds[bed_type] = sum(1 for b in self.beds.values() if b.bed_type == bed_type)
            occupied_beds[bed_type] = sum(1 for b in self.beds.values() 
                                        if b.bed_type == bed_type and b.is_occupied)
        
        available_staff = {}
        total_staff = {}
        staff_utilization = {}
        
        for staff_type in StaffType:
            total = sum(1 for s in self.staff.values() if s.staff_type == staff_type)
            available = sum(1 for s in self.staff.values() 
                          if s.staff_type == staff_type and s.is_available)
            total_staff[staff_type] = total
            available_staff[staff_type] = available
            staff_utilization[staff_type] = 1.0 - (available / total) if total > 0 else 0.0
        
        total_bed_count = sum(total_beds.values())
        occupied_bed_count = sum(occupied_beds.values())
        occupancy_rate = occupied_bed_count / total_bed_count if total_bed_count > 0 else 0.0
        
        throughput = len([p for p in self.patients.values() 
                         if self.time - p.admission_date < 1.0]) if hasattr(self, 'time') else 0.0
        
        return HospitalState(
            total_beds=total_beds,
            occupied_beds=occupied_beds,
            available_staff=available_staff,
            total_staff=total_staff,
            patient_queue=[p for p in self.patient_queue],
            wait_times=self.wait_times.copy(),
            throughput=throughput,
            occupancy_rate=occupancy_rate,
            staff_utilization=staff_utilization,
            time=self.time
        )
    
    def reset(self):
        """Reset simulator to initial state"""
        for bed in self.beds.values():
            bed.is_occupied = False
            bed.patient_id = None
            bed.admission_time = None
            bed.expected_discharge = None
        
        for staff in self.staff.values():
            staff.is_available = True
            staff.current_patients = []
        
        self.patients = {}
        self.patient_queue = []
        self.wait_times = {}
        self.time = 0.0
    
    def close(self):
        """Clean up resources"""
        pass

