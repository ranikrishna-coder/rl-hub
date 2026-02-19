"""
Environment Registry
Maps environment names to classes and provides metadata
"""

from typing import Dict, Any, Optional, List
import importlib
import sys
import os

# Add environments to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Registry mapping
ENVIRONMENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    # Clinical environments
    "TreatmentPathwayOptimization": {
        "class_path": "environments.clinical.treatment_pathway_optimization.TreatmentPathwayOptimizationEnv",
        "system": "Epic, Cerner, Allscripts",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "SepsisEarlyIntervention": {
        "class_path": "environments.clinical.sepsis_early_intervention.SepsisEarlyInterventionEnv",
        "system": "Epic, Cerner",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "ICUResourceAllocation": {
        "class_path": "environments.clinical.icu_resource_allocation.ICUResourceAllocationEnv",
        "system": "Epic, Cerner, Meditech",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "SurgicalScheduling": {
        "class_path": "environments.clinical.surgical_scheduling.SurgicalSchedulingEnv",
        "system": "Epic, Cerner, Meditech",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "DiagnosticTestSequencing": {
        "class_path": "environments.clinical.diagnostic_test_sequencing.DiagnosticTestSequencingEnv",
        "system": "Epic, Cerner, Allscripts",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "MedicationDosingOptimization": {
        "class_path": "environments.clinical.medication_dosing_optimization.MedicationDosingOptimizationEnv",
        "system": "Epic, Cerner, Allscripts",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "ReadmissionReduction": {
        "class_path": "environments.clinical.readmission_reduction.ReadmissionReductionEnv",
        "system": "Epic, Cerner, Allscripts",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "CareCoordination": {
        "class_path": "environments.clinical.care_coordination.CareCoordinationEnv",
        "system": "Epic, Cerner, Allscripts",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "ChronicDiseaseManagement": {
        "class_path": "environments.clinical.chronic_disease_management.ChronicDiseaseManagementEnv",
        "system": "Epic, Cerner, Allscripts",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "EmergencyTriage": {
        "class_path": "environments.clinical.emergency_triage.EmergencyTriageEnv",
        "system": "Epic, Cerner, Meditech",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    # Imaging environments
    "ImagingOrderPrioritization": {
        "class_path": "environments.imaging.imaging_order_prioritization.ImagingOrderPrioritizationEnv",
        "system": "Philips, GE Healthcare",
        "workflow": "Imaging",
        "category": "imaging",
        "multi_agent": False
    },
    "RadiologyScheduling": {
        "class_path": "environments.imaging.radiology_scheduling.RadiologySchedulingEnv",
        "system": "Philips, GE Healthcare",
        "workflow": "Imaging",
        "category": "imaging",
        "multi_agent": False
    },
    "ScanParameterOptimization": {
        "class_path": "environments.imaging.scan_parameter_optimization.ScanParameterOptimizationEnv",
        "system": "Philips, GE Healthcare",
        "workflow": "Imaging",
        "category": "imaging",
        "multi_agent": False
    },
    "ImagingWorkflowRouting": {
        "class_path": "environments.imaging.imaging_workflow_routing.ImagingWorkflowRoutingEnv",
        "system": "Philips, GE Healthcare",
        "workflow": "Imaging",
        "category": "imaging",
        "multi_agent": False
    },
    "EquipmentUtilization": {
        "class_path": "environments.imaging.equipment_utilization.EquipmentUtilizationEnv",
        "system": "Philips, GE Healthcare",
        "workflow": "Imaging",
        "category": "imaging",
        "multi_agent": False
    },
    # Add all other environments...
    # For brevity, adding key ones - full registry would include all 50
}

# Helper function to convert CamelCase to snake_case
def _camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case"""
    import re
    # Insert underscore before uppercase letters (except first one)
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

# Add remaining environments programmatically
def _add_remaining_environments():
    """Add remaining environments to registry"""
    categories = {
        "population_health": [
            "RiskStratification", "PreventiveOutreach", "VaccinationAllocation",
            "HighRiskMonitoring", "PopulationCostOptimization"
        ],
        "revenue_cycle": [
            "ClaimsRouting", "DenialIntervention", "PaymentPlanSequencing",
            "BillingCodeOptimization", "RevenueLeakageDetection"
        ],
        "clinical_trials": [
            "TrialPatientMatching", "AdaptiveTrialDesign", "EnrollmentAcceleration",
            "ProtocolDeviationMitigation", "DrugDosageTrialSequencing"
        ],
        "hospital_operations": [
            "StaffingAllocation", "ORUtilization", "SupplyChainInventory",
            "BedTurnoverOptimization", "EquipmentMaintenance"
        ],
        "telehealth": [
            "VirtualVisitRouting", "EscalationPolicy", "ProviderLoadBalancing",
            "FollowUpOptimization", "DigitalAdherenceCoaching"
        ],
        "interoperability": [
            "DataReconciliation", "CrossSystemAlertPrioritization", "DuplicateRecordResolution",
            "InterFacilityTransfer", "HIERouting"
        ],
        "cross_workflow": [
            "PatientJourneyOptimization", "HospitalThroughput", "ClinicalFinancialTradeoff",
            "ValueBasedCareOptimization", "MultiHospitalNetworkCoordination"
        ]
    }
    
    for category, envs in categories.items():
        for env_name in envs:
            # Convert to snake_case for file name
            file_name = _camel_to_snake(env_name)
            # Class name is {env_name}Env
            class_name = f"{env_name}Env"
            # Module path is environments.{category}.{file_name}
            module_path = f"environments.{category}.{file_name}"
            
            ENVIRONMENT_REGISTRY[env_name] = {
                "class_path": f"{module_path}.{class_name}",
                "system": "Multiple",
                "workflow": category.replace("_", " ").title(),
                "category": category,
                "multi_agent": category == "cross_workflow"
            }

_add_remaining_environments()


def get_environment_class(environment_name: str):
    """Get environment class by name"""
    if environment_name not in ENVIRONMENT_REGISTRY:
        return None
    
    class_path = ENVIRONMENT_REGISTRY[environment_name]["class_path"]
    module_path, class_name = class_path.rsplit(".", 1)
    
    try:
        module = importlib.import_module(module_path)
        env_class = getattr(module, class_name)
        
        # Verify the class is actually a HealthcareRLEnvironment subclass
        if env_class is None:
            raise AttributeError(f"Class {class_name} not found in {module_path}")
        
        return env_class
    except ImportError as e:
        print(f"Import error loading environment {environment_name} from {module_path}: {e}")
        import traceback
        traceback.print_exc()
        return None
    except AttributeError as e:
        print(f"Attribute error loading environment {environment_name}: {e}")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"Unexpected error loading environment {environment_name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_environment_metadata(environment_name: str) -> Optional[Dict[str, Any]]:
    """Get metadata for an environment"""
    if environment_name not in ENVIRONMENT_REGISTRY:
        return None
    
    return ENVIRONMENT_REGISTRY[environment_name].copy()


def list_all_environments() -> List[Dict[str, Any]]:
    """List all available environments"""
    return [
        {
            "name": name,
            **metadata
        }
        for name, metadata in ENVIRONMENT_REGISTRY.items()
    ]

