"""
Patient Data Generator
Synthetic patient profile generator mimicking EHR systems (Epic, Cerner, Allscripts)
"""

import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import random


class ConditionSeverity(Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


class PatientStatus(Enum):
    STABLE = "stable"
    IMPROVING = "improving"
    DETERIORATING = "deteriorating"
    CRITICAL = "critical"
    DISCHARGED = "discharged"


@dataclass
class PatientProfile:
    """Synthetic patient profile"""
    patient_id: str
    age: int
    gender: str
    conditions: List[str]
    medications: List[str]
    vitals: Dict[str, float]
    lab_results: Dict[str, float]
    risk_score: float
    severity: ConditionSeverity
    status: PatientStatus
    admission_date: float
    length_of_stay: float
    readmission_risk: float
    comorbidities: List[str] = field(default_factory=list)
    insurance_type: str = "commercial"
    social_determinants: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "patient_id": self.patient_id,
            "age": self.age,
            "gender": self.gender,
            "conditions": self.conditions,
            "medications": self.medications,
            "vitals": self.vitals,
            "lab_results": self.lab_results,
            "risk_score": self.risk_score,
            "severity": self.severity.value,
            "status": self.status.value,
            "admission_date": self.admission_date,
            "length_of_stay": self.length_of_stay,
            "readmission_risk": self.readmission_risk,
            "comorbidities": self.comorbidities,
            "insurance_type": self.insurance_type,
            "social_determinants": self.social_determinants
        }


class PatientGenerator:
    """
    Generates synthetic patient profiles mimicking Epic/Cerner/Allscripts data structures
    """
    
    COMMON_CONDITIONS = [
        "hypertension", "diabetes", "copd", "heart_failure", "pneumonia",
        "sepsis", "stroke", "mi", "asthma", "ckd", "cancer", "arthritis"
    ]
    
    COMMON_MEDICATIONS = [
        "metformin", "lisinopril", "atorvastatin", "aspirin", "warfarin",
        "insulin", "albuterol", "prednisone", "furosemide", "metoprolol"
    ]
    
    VITAL_SIGNS = ["bp_systolic", "bp_diastolic", "heart_rate", "temperature", 
                   "respiratory_rate", "oxygen_saturation", "pain_score"]
    
    LAB_TESTS = ["glucose", "creatinine", "hemoglobin", "wbc", "platelets",
                 "sodium", "potassium", "troponin", "bnp", "lactate"]
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed) if seed else np.random.default_rng()
    
    def generate_patient(
        self,
        patient_id: Optional[str] = None,
        condition_type: Optional[str] = None,
        severity: Optional[ConditionSeverity] = None,
        age_range: Optional[tuple] = None
    ) -> PatientProfile:
        """Generate a synthetic patient profile"""
        
        patient_id = patient_id or f"PAT_{self.rng.integers(100000, 999999)}"
        age = self.rng.integers(age_range[0], age_range[1]) if age_range else self.rng.integers(18, 90)
        gender = self.rng.choice(["M", "F", "Other"])
        
        # Select condition
        if condition_type:
            conditions = [condition_type]
        else:
            num_conditions = self.rng.integers(1, 4)
            conditions = self.rng.choice(self.COMMON_CONDITIONS, size=num_conditions, replace=False).tolist()
        
        # Determine severity
        if severity is None:
            severity_weights = [0.3, 0.4, 0.2, 0.1]
            severity = self.rng.choice(list(ConditionSeverity), p=severity_weights)
        
        # Generate medications based on conditions
        medications = self._generate_medications(conditions)
        
        # Generate vitals based on severity
        vitals = self._generate_vitals(severity, conditions)
        
        # Generate lab results
        lab_results = self._generate_lab_results(severity, conditions)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(age, conditions, vitals, lab_results)
        
        # Determine status
        status = self._determine_status(severity, risk_score)
        
        # Generate comorbidities
        comorbidities = self._generate_comorbidities(age, conditions)
        
        # Social determinants
        social_determinants = {
            "housing_stability": self.rng.random(),
            "food_security": self.rng.random(),
            "transportation": self.rng.random(),
            "health_literacy": self.rng.random()
        }
        
        return PatientProfile(
            patient_id=patient_id,
            age=age,
            gender=gender,
            conditions=conditions,
            medications=medications,
            vitals=vitals,
            lab_results=lab_results,
            risk_score=risk_score,
            severity=severity,
            status=status,
            admission_date=0.0,  # Will be set by simulator
            length_of_stay=0.0,
            readmission_risk=self._calculate_readmission_risk(age, conditions, comorbidities, risk_score),
            comorbidities=comorbidities,
            insurance_type=self.rng.choice(["commercial", "medicare", "medicaid", "uninsured"]),
            social_determinants=social_determinants
        )
    
    def _generate_medications(self, conditions: List[str]) -> List[str]:
        """Generate medications based on conditions"""
        medication_map = {
            "diabetes": ["metformin", "insulin"],
            "hypertension": ["lisinopril", "metoprolol"],
            "copd": ["albuterol", "prednisone"],
            "heart_failure": ["furosemide", "metoprolol"],
            "mi": ["aspirin", "atorvastatin", "metoprolol"]
        }
        
        medications = []
        for condition in conditions:
            if condition in medication_map:
                medications.extend(medication_map[condition])
        
        # Add common medications
        if not medications:
            num_meds = self.rng.integers(1, 4)
            medications = self.rng.choice(self.COMMON_MEDICATIONS, size=num_meds, replace=False).tolist()
        
        return list(set(medications))
    
    def _generate_vitals(self, severity: ConditionSeverity, conditions: List[str]) -> Dict[str, float]:
        """Generate vital signs based on severity"""
        base_vitals = {
            "bp_systolic": 120.0,
            "bp_diastolic": 80.0,
            "heart_rate": 72.0,
            "temperature": 98.6,
            "respiratory_rate": 16.0,
            "oxygen_saturation": 98.0,
            "pain_score": 0.0
        }
        
        # Adjust based on severity
        severity_multipliers = {
            ConditionSeverity.MILD: 1.0,
            ConditionSeverity.MODERATE: 1.1,
            ConditionSeverity.SEVERE: 1.2,
            ConditionSeverity.CRITICAL: 1.4
        }
        
        multiplier = severity_multipliers[severity]
        
        vitals = {}
        for key, base_value in base_vitals.items():
            if key in ["bp_systolic", "heart_rate", "respiratory_rate", "pain_score"]:
                vitals[key] = base_value * multiplier + self.rng.normal(0, base_value * 0.1)
            elif key == "oxygen_saturation":
                vitals[key] = max(85.0, base_value - (multiplier - 1.0) * 10 + self.rng.normal(0, 2))
            elif key == "temperature":
                vitals[key] = base_value + (multiplier - 1.0) * 2 + self.rng.normal(0, 0.5)
            else:
                vitals[key] = base_value + self.rng.normal(0, base_value * 0.05)
        
        return vitals
    
    def _generate_lab_results(self, severity: ConditionSeverity, conditions: List[str]) -> Dict[str, float]:
        """Generate lab results"""
        normal_ranges = {
            "glucose": (70, 100),
            "creatinine": (0.6, 1.2),
            "hemoglobin": (12, 16),
            "wbc": (4, 11),
            "platelets": (150, 450),
            "sodium": (135, 145),
            "potassium": (3.5, 5.0),
            "troponin": (0, 0.04),
            "bnp": (0, 100),
            "lactate": (0.5, 2.2)
        }
        
        severity_multipliers = {
            ConditionSeverity.MILD: 1.1,
            ConditionSeverity.MODERATE: 1.3,
            ConditionSeverity.SEVERE: 1.6,
            ConditionSeverity.CRITICAL: 2.0
        }
        
        multiplier = severity_multipliers[severity]
        
        lab_results = {}
        for test, (low, high) in normal_ranges.items():
            if severity in [ConditionSeverity.SEVERE, ConditionSeverity.CRITICAL]:
                # Abnormal values for severe cases
                if test in ["glucose", "creatinine", "wbc", "lactate"]:
                    lab_results[test] = high * multiplier + self.rng.normal(0, high * 0.1)
                elif test in ["hemoglobin", "platelets", "sodium", "potassium"]:
                    lab_results[test] = low / multiplier + self.rng.normal(0, low * 0.1)
                else:
                    lab_results[test] = (low + high) / 2 * multiplier + self.rng.normal(0, (high - low) * 0.1)
            else:
                lab_results[test] = self.rng.uniform(low, high)
        
        return lab_results
    
    def _calculate_risk_score(self, age: int, conditions: List[str], 
                             vitals: Dict[str, float], lab_results: Dict[str, float]) -> float:
        """Calculate patient risk score"""
        risk = 0.0
        
        # Age component
        risk += (age - 18) / 100.0
        
        # Condition component
        risk += len(conditions) * 0.1
        
        # Vitals component
        if vitals["oxygen_saturation"] < 90:
            risk += 0.3
        if vitals["heart_rate"] > 120:
            risk += 0.2
        if vitals["temperature"] > 101:
            risk += 0.15
        
        # Lab results component
        if lab_results.get("lactate", 2.2) > 4.0:
            risk += 0.25
        if lab_results.get("troponin", 0.04) > 0.1:
            risk += 0.2
        
        return min(1.0, risk)
    
    def _determine_status(self, severity: ConditionSeverity, risk_score: float) -> PatientStatus:
        """Determine patient status"""
        if severity == ConditionSeverity.CRITICAL or risk_score > 0.8:
            return PatientStatus.CRITICAL
        elif severity == ConditionSeverity.SEVERE or risk_score > 0.6:
            return PatientStatus.DETERIORATING
        elif risk_score < 0.3:
            return PatientStatus.STABLE
        else:
            return PatientStatus.IMPROVING
    
    def _generate_comorbidities(self, age: int, conditions: List[str]) -> List[str]:
        """Generate comorbidities based on age and conditions"""
        comorbidities = []
        
        if age > 65:
            comorbidities.extend(["osteoporosis", "dementia_risk"])
        
        if "diabetes" in conditions:
            comorbidities.append("diabetic_retinopathy")
        
        if "hypertension" in conditions:
            comorbidities.append("kidney_disease_risk")
        
        return comorbidities
    
    def _calculate_readmission_risk(self, age: int, conditions: List[str], 
                                   comorbidities: List[str], risk_score: float) -> float:
        """Calculate readmission risk"""
        risk = risk_score * 0.5
        risk += len(comorbidities) * 0.1
        risk += (age - 18) / 200.0
        return min(1.0, risk)
    
    def generate_batch(self, n: int, **kwargs) -> List[PatientProfile]:
        """Generate a batch of patients"""
        return [self.generate_patient(**kwargs) for _ in range(n)]
    
    def evolve_patient(self, patient: PatientProfile, time_delta: float) -> PatientProfile:
        """Evolve patient state over time"""
        # Update vitals based on treatment and time
        for key in patient.vitals:
            if key == "pain_score":
                patient.vitals[key] = max(0, patient.vitals[key] - time_delta * 0.1)
            elif key == "temperature" and patient.status == PatientStatus.IMPROVING:
                patient.vitals[key] = 98.6 + (patient.vitals[key] - 98.6) * 0.9
        
        # Update risk score
        patient.risk_score = self._calculate_risk_score(
            patient.age, patient.conditions, patient.vitals, patient.lab_results
        )
        
        # Update status
        patient.status = self._determine_status(patient.severity, patient.risk_score)
        
        # Update length of stay
        patient.length_of_stay += time_delta
        
        return patient

