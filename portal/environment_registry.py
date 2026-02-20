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
    # New Clinical environments (51-60)
    "PainManagementOptimization": {
        "class_path": "environments.clinical.pain_management_optimization.PainManagementOptimizationEnv",
        "system": "Epic, Cerner, Allscripts, Meditech",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "AntibioticStewardship": {
        "class_path": "environments.clinical.antibiotic_stewardship.AntibioticStewardshipEnv",
        "system": "Epic, Cerner, Allscripts, Meditech",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "OncologyTreatmentSequencing": {
        "class_path": "environments.clinical.oncology_treatment_sequencing.OncologyTreatmentSequencingEnv",
        "system": "Epic, Cerner, Allscripts",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "LabTestPrioritization": {
        "class_path": "environments.clinical.lab_test_prioritization.LabTestPrioritizationEnv",
        "system": "Epic, Cerner, Allscripts, Meditech",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "ICUVentilatorAllocation": {
        "class_path": "environments.clinical.icu_ventilator_allocation.ICUVentilatorAllocationEnv",
        "system": "Epic, Cerner, Meditech",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "StrokeInterventionScheduling": {
        "class_path": "environments.clinical.stroke_intervention_scheduling.StrokeInterventionSchedulingEnv",
        "system": "Epic, Cerner, Allscripts",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "CardiacCareOptimization": {
        "class_path": "environments.clinical.cardiac_care_optimization.CardiacCareOptimizationEnv",
        "system": "Epic, Cerner, Meditech",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "DiabetesMonitoringOptimization": {
        "class_path": "environments.clinical.diabetes_monitoring_optimization.DiabetesMonitoringOptimizationEnv",
        "system": "Epic, Cerner, Allscripts",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "MentalHealthInterventionSequencing": {
        "class_path": "environments.clinical.mental_health_intervention_sequencing.MentalHealthInterventionSequencingEnv",
        "system": "Epic, Cerner, Allscripts, Meditech",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    "PostOperativeFollowupOptimization": {
        "class_path": "environments.clinical.post_operative_followup_optimization.PostOperativeFollowupOptimizationEnv",
        "system": "Epic, Cerner, Meditech",
        "workflow": "Clinical",
        "category": "clinical",
        "multi_agent": False
    },
    # New Imaging environments (61-63)
    "MRIScanScheduling": {
        "class_path": "environments.imaging.mri_scan_scheduling.MRIScanSchedulingEnv",
        "system": "Philips, GE",
        "workflow": "Imaging",
        "category": "imaging",
        "multi_agent": False
    },
    "CTScanPrioritization": {
        "class_path": "environments.imaging.ct_scan_prioritization.CTScanPrioritizationEnv",
        "system": "Philips, GE",
        "workflow": "Imaging",
        "category": "imaging",
        "multi_agent": False
    },
    "RadiologistTaskAssignment": {
        "class_path": "environments.imaging.radiologist_task_assignment.RadiologistTaskAssignmentEnv",
        "system": "Philips, GE",
        "workflow": "Imaging",
        "category": "imaging",
        "multi_agent": False
    },
    "UltrasoundResourceAllocation": {
        "class_path": "environments.imaging.ultrasound_resource_allocation.UltrasoundResourceAllocationEnv",
        "system": "Philips, GE",
        "workflow": "Imaging",
        "category": "imaging",
        "multi_agent": False
    },
    "PACSWorkflowOptimization": {
        "class_path": "environments.imaging.pacs_workflow_optimization.PACSWorkflowOptimizationEnv",
        "system": "Philips, GE",
        "workflow": "Imaging",
        "category": "imaging",
        "multi_agent": False
    },
    "ImagingResultTriage": {
        "class_path": "environments.imaging.imaging_result_triage.ImagingResultTriageEnv",
        "system": "Philips, GE",
        "workflow": "Imaging",
        "category": "imaging",
        "multi_agent": False
    },
    "AIAssistedDiagnostics": {
        "class_path": "environments.imaging.ai_assisted_diagnostics.AIAssistedDiagnosticsEnv",
        "system": "Philips, GE",
        "workflow": "Imaging",
        "category": "imaging",
        "multi_agent": False
    },
    "ImagingStudyBatchScheduling": {
        "class_path": "environments.imaging.imaging_study_batch_scheduling.ImagingStudyBatchSchedulingEnv",
        "system": "Philips, GE",
        "workflow": "Imaging",
        "category": "imaging",
        "multi_agent": False
    },
    "OncologyImagingPathway": {
        "class_path": "environments.imaging.oncology_imaging_pathway.OncologyImagingPathwayEnv",
        "system": "Philips, GE",
        "workflow": "Imaging",
        "category": "imaging",
        "multi_agent": False
    },
    "ImagingQualityControl": {
        "class_path": "environments.imaging.imaging_quality_control.ImagingQualityControlEnv",
        "system": "Philips, GE",
        "workflow": "Imaging",
        "category": "imaging",
        "multi_agent": False
    },
    # Population Health environments (71-80)
    "ChronicDiseaseOutreach": {
        "class_path": "environments.population_health.chronic_disease_outreach.ChronicDiseaseOutreachEnv",
        "system": "Health Catalyst, Innovaccer",
        "workflow": "Population Health",
        "category": "population_health",
        "multi_agent": False
    },
    "TelemonitoringOptimization": {
        "class_path": "environments.population_health.telemonitoring_optimization.TelemonitoringOptimizationEnv",
        "system": "Health Catalyst, Innovaccer",
        "workflow": "Population Health",
        "category": "population_health",
        "multi_agent": False
    },
    "PreventiveScreeningPolicy": {
        "class_path": "environments.population_health.preventive_screening_policy.PreventiveScreeningPolicyEnv",
        "system": "Health Catalyst, Innovaccer",
        "workflow": "Population Health",
        "category": "population_health",
        "multi_agent": False
    },
    "HighRiskPatientEngagement": {
        "class_path": "environments.population_health.high_risk_patient_engagement.HighRiskPatientEngagementEnv",
        "system": "Health Catalyst, Innovaccer",
        "workflow": "Population Health",
        "category": "population_health",
        "multi_agent": False
    },
    "PopulationHealthCostAllocation": {
        "class_path": "environments.population_health.population_health_cost_allocation.PopulationHealthCostAllocationEnv",
        "system": "Health Catalyst, Innovaccer",
        "workflow": "Population Health",
        "category": "population_health",
        "multi_agent": False
    },
    "CommunityHealthProgramAllocation": {
        "class_path": "environments.population_health.community_health_program_allocation.CommunityHealthProgramAllocationEnv",
        "system": "Health Catalyst, Innovaccer",
        "workflow": "Population Health",
        "category": "population_health",
        "multi_agent": False
    },
    "ReadmissionRiskMitigation": {
        "class_path": "environments.population_health.readmission_risk_mitigation.ReadmissionRiskMitigationEnv",
        "system": "Health Catalyst, Innovaccer",
        "workflow": "Population Health",
        "category": "population_health",
        "multi_agent": False
    },
    "HealthLiteracyIntervention": {
        "class_path": "environments.population_health.health_literacy_intervention.HealthLiteracyInterventionEnv",
        "system": "Health Catalyst, Innovaccer",
        "workflow": "Population Health",
        "category": "population_health",
        "multi_agent": False
    },
    "LifestyleInterventionSequencing": {
        "class_path": "environments.population_health.lifestyle_intervention_sequencing.LifestyleInterventionSequencingEnv",
        "system": "Health Catalyst, Innovaccer",
        "workflow": "Population Health",
        "category": "population_health",
        "multi_agent": False
    },
    "VaccinationDrivePrioritization": {
        "class_path": "environments.population_health.vaccination_drive_prioritization.VaccinationDrivePrioritizationEnv",
        "system": "Health Catalyst, Innovaccer",
        "workflow": "Population Health",
        "category": "population_health",
        "multi_agent": False
    },
    # Revenue Cycle environments (81-90)
    "PatientBillingPrioritization": {
        "class_path": "environments.revenue_cycle.patient_billing_prioritization.PatientBillingPrioritizationEnv",
        "system": "Change Healthcare",
        "workflow": "Revenue Cycle",
        "category": "revenue_cycle",
        "multi_agent": False
    },
    "ClaimsRejectionRecovery": {
        "class_path": "environments.revenue_cycle.claims_rejection_recovery.ClaimsRejectionRecoveryEnv",
        "system": "Change Healthcare",
        "workflow": "Revenue Cycle",
        "category": "revenue_cycle",
        "multi_agent": False
    },
    "PreAuthorizationWorkflow": {
        "class_path": "environments.revenue_cycle.pre_authorization_workflow.PreAuthorizationWorkflowEnv",
        "system": "Change Healthcare",
        "workflow": "Revenue Cycle",
        "category": "revenue_cycle",
        "multi_agent": False
    },
    "DenialAppealsSequencing": {
        "class_path": "environments.revenue_cycle.denial_appeals_sequencing.DenialAppealsSequencingEnv",
        "system": "Change Healthcare",
        "workflow": "Revenue Cycle",
        "category": "revenue_cycle",
        "multi_agent": False
    },
    "PaymentReconciliation": {
        "class_path": "environments.revenue_cycle.payment_reconciliation.PaymentReconciliationEnv",
        "system": "Change Healthcare",
        "workflow": "Revenue Cycle",
        "category": "revenue_cycle",
        "multi_agent": False
    },
    "CostToCollectOptimization": {
        "class_path": "environments.revenue_cycle.cost_to_collect_optimization.CostToCollectOptimizationEnv",
        "system": "Change Healthcare",
        "workflow": "Revenue Cycle",
        "category": "revenue_cycle",
        "multi_agent": False
    },
    "ContractComplianceScoring": {
        "class_path": "environments.revenue_cycle.contract_compliance_scoring.ContractComplianceScoringEnv",
        "system": "Change Healthcare",
        "workflow": "Revenue Cycle",
        "category": "revenue_cycle",
        "multi_agent": False
    },
    "InsurancePlanMatching": {
        "class_path": "environments.revenue_cycle.insurance_plan_matching.InsurancePlanMatchingEnv",
        "system": "Change Healthcare",
        "workflow": "Revenue Cycle",
        "category": "revenue_cycle",
        "multi_agent": False
    },
    "RevenueForecastSimulation": {
        "class_path": "environments.revenue_cycle.revenue_forecast_simulation.RevenueForecastSimulationEnv",
        "system": "Change Healthcare",
        "workflow": "Revenue Cycle",
        "category": "revenue_cycle",
        "multi_agent": False
    },
    "PatientFinancialCounseling": {
        "class_path": "environments.revenue_cycle.patient_financial_counseling.PatientFinancialCounselingEnv",
        "system": "Change Healthcare",
        "workflow": "Revenue Cycle",
        "category": "revenue_cycle",
        "multi_agent": False
    },
    # Clinical Trials environments (91-100)
    "AdaptiveCohortAllocation": {
        "class_path": "environments.clinical_trials.adaptive_cohort_allocation.AdaptiveCohortAllocationEnv",
        "system": "Veeva, IQVIA",
        "workflow": "Clinical Trials",
        "category": "clinical_trials",
        "multi_agent": False
    },
    "TrialProtocolOptimization": {
        "class_path": "environments.clinical_trials.trial_protocol_optimization.TrialProtocolOptimizationEnv",
        "system": "Veeva, IQVIA",
        "workflow": "Clinical Trials",
        "category": "clinical_trials",
        "multi_agent": False
    },
    "DrugSupplySequencing": {
        "class_path": "environments.clinical_trials.drug_supply_sequencing.DrugSupplySequencingEnv",
        "system": "Veeva, IQVIA",
        "workflow": "Clinical Trials",
        "category": "clinical_trials",
        "multi_agent": False
    },
    "TrialSiteResourceAllocation": {
        "class_path": "environments.clinical_trials.trial_site_resource_allocation.TrialSiteResourceAllocationEnv",
        "system": "Veeva, IQVIA",
        "workflow": "Clinical Trials",
        "category": "clinical_trials",
        "multi_agent": False
    },
    "PatientFollowUpScheduling": {
        "class_path": "environments.clinical_trials.patient_follow_up_scheduling.PatientFollowUpSchedulingEnv",
        "system": "Veeva, IQVIA",
        "workflow": "Clinical Trials",
        "category": "clinical_trials",
        "multi_agent": False
    },
    "EnrollmentFunnelOptimization": {
        "class_path": "environments.clinical_trials.enrollment_funnel_optimization.EnrollmentFunnelOptimizationEnv",
        "system": "Veeva, IQVIA",
        "workflow": "Clinical Trials",
        "category": "clinical_trials",
        "multi_agent": False
    },
    "AdverseEventPrediction": {
        "class_path": "environments.clinical_trials.adverse_event_prediction.AdverseEventPredictionEnv",
        "system": "Veeva, IQVIA",
        "workflow": "Clinical Trials",
        "category": "clinical_trials",
        "multi_agent": False
    },
    "TrialOutcomeForecasting": {
        "class_path": "environments.clinical_trials.trial_outcome_forecasting.TrialOutcomeForecastingEnv",
        "system": "Veeva, IQVIA",
        "workflow": "Clinical Trials",
        "category": "clinical_trials",
        "multi_agent": False
    },
    "PatientRetentionSequencing": {
        "class_path": "environments.clinical_trials.patient_retention_sequencing.PatientRetentionSequencingEnv",
        "system": "Veeva, IQVIA",
        "workflow": "Clinical Trials",
        "category": "clinical_trials",
        "multi_agent": False
    },
    "MultiTrialResourceCoordination": {
        "class_path": "environments.clinical_trials.multi_trial_resource_coordination.MultiTrialResourceCoordinationEnv",
        "system": "Veeva, IQVIA",
        "workflow": "Clinical Trials",
        "category": "clinical_trials",
        "multi_agent": False
    },
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
    # Define category-specific systems
    category_systems = {
        "population_health": "Health Catalyst, Innovaccer",
        "revenue_cycle": "Change Healthcare",
        "clinical_trials": "Veeva, IQVIA",
        "hospital_operations": "Epic, Cerner, Meditech",
        "telehealth": "Teladoc, Amwell, Doxy.me",
        "interoperability": "InterSystems, Redox, Mirth",
        "cross_workflow": "Epic, Cerner, Allscripts, Meditech"
    }
    
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
        system = category_systems.get(category, "Multiple")
        for env_name in envs:
            # Convert to snake_case for file name
            file_name = _camel_to_snake(env_name)
            # Class name is {env_name}Env
            class_name = f"{env_name}Env"
            # Module path is environments.{category}.{file_name}
            module_path = f"environments.{category}.{file_name}"
            
            ENVIRONMENT_REGISTRY[env_name] = {
                "class_path": f"{module_path}.{class_name}",
                "system": system,
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

