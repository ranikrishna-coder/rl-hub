"""
Treatment Pathway Optimization Environment (Refactored with Verifiers)
Optimizes treatment sequences for patients with multiple conditions
System: Epic, Cerner, Allscripts

REFACTORED: Uses verifier-based reward calculation instead of direct calculation
"""

import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional, Tuple
import sys
import os
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from environments.base_environment import HealthcareRLEnvironment, KPIMetrics
from simulator.patient_generator import PatientGenerator, ConditionSeverity
from simulator.hospital_simulator import HospitalSimulator

# Import verifier architecture
from verifiers.base_verifier import BaseVerifier
from verifiers.ensemble_verifier import EnsembleVerifier
from verifiers.verifier_registry import VerifierRegistry

# Import observability
from observability.reward_logger import RewardLogger
from observability.action_trace_logger import ActionTraceLogger
from observability.episode_metrics import EpisodeMetricsTracker
from observability.audit_logger import AuditLogger, AuditEventType

# Import governance
from governance.safety_guardrails import SafetyGuardrails
from governance.compliance_rules import ComplianceRules


class TreatmentPathwayOptimizationEnv(HealthcareRLEnvironment):
    """
    Optimizes treatment pathways for patients with complex conditions
    
    REFACTORED ARCHITECTURE:
    - Reward calculation delegated to verifier modules
    - Multiple verifiers can be attached (ensemble)
    - All rewards logged to observability layer
    - Governance controls validate actions
    
    State: Patient demographics, conditions, vitals, lab results, current treatments
    Action: Select next treatment step (medication, procedure, test, discharge)
    Reward: Calculated by verifier modules (clinical, operational, financial, compliance)
    """
    
    TREATMENT_OPTIONS = [
        "medication_adjustment",
        "diagnostic_test",
        "specialist_consult",
        "procedure",
        "monitoring",
        "discharge"
    ]
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        verifier: Optional[BaseVerifier] = None,
        enable_observability: bool = True,
        enable_governance: bool = True,
        **kwargs
    ):
        """
        Initialize environment with verifier-based architecture
        
        Args:
            config: Environment configuration
            verifier: Verifier instance (if None, creates default ensemble)
            enable_observability: Enable observability logging
            enable_governance: Enable governance controls
        """
        super().__init__(config, **kwargs)
        
        # State space: 20 features
        # [age, gender_encoded, condition_severity, risk_score, vitals(7), labs(5), 
        #  current_treatments(3), pathway_step, days_in_pathway, readmission_risk]
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(20,), dtype=np.float32
        )
        
        # Action space: 6 treatment options
        self.action_space = spaces.Discrete(len(self.TREATMENT_OPTIONS))
        
        # Initialize simulators
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        
        # Patient tracking
        self.current_patient = None
        self.pathway_step = 0
        self.treatment_history = []
        self.total_cost = 0.0
        
        # Treatment costs
        self.treatment_costs = {
            "medication_adjustment": 50.0,
            "diagnostic_test": 200.0,
            "specialist_consult": 300.0,
            "procedure": 1000.0,
            "monitoring": 100.0,
            "discharge": 0.0
        }
        
        # VERIFIER ARCHITECTURE
        # Use provided verifier or create default ensemble
        if verifier is None:
            self.verifier = VerifierRegistry.create_default_ensemble(
                instance_id=f"treatment_pathway_{id(self)}"
            )
        else:
            self.verifier = verifier
        
        # OBSERVABILITY LAYER
        self.enable_observability = enable_observability
        if enable_observability:
            self.reward_logger = RewardLogger()
            self.action_trace_logger = ActionTraceLogger()
            self.episode_metrics = EpisodeMetricsTracker()
            self.audit_logger = AuditLogger()
        else:
            self.reward_logger = None
            self.action_trace_logger = None
            self.episode_metrics = None
            self.audit_logger = None
        
        # GOVERNANCE LAYER
        self.enable_governance = enable_governance
        if enable_governance:
            from governance.safety_guardrails import SafetyGuardrails, SafetyConfig
            from governance.compliance_rules import ComplianceRules
            
            safety_config = SafetyConfig(
                max_risk_threshold=0.8,
                compliance_hard_stop=True,
                human_in_the_loop=False
            )
            self.safety_guardrails = SafetyGuardrails(safety_config)
            self.compliance_rules = ComplianceRules()
        else:
            self.safety_guardrails = None
            self.compliance_rules = None
        
        # Episode tracking
        self.episode_id = None
        self.cumulative_reward = 0.0
        self.compliance_violations = []
    
    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Reset environment to initial state"""
        obs, info = super().reset(seed=seed, options=options)
        
        # Generate new episode ID
        self.episode_id = str(uuid.uuid4())
        self.cumulative_reward = 0.0
        self.compliance_violations = []
        
        # Log episode start
        if self.audit_logger:
            self.audit_logger.log_event(
                AuditEventType.ACTION_TAKEN,
                self.episode_id,
                "TreatmentPathwayOptimization",
                "Episode started",
                {"pathway_step": 0}
            )
        
        return obs, info
    
    def _initialize_state(self) -> np.ndarray:
        """Initialize patient and pathway"""
        self.current_patient = self.patient_generator.generate_patient()
        self.pathway_step = 0
        self.treatment_history = []
        self.total_cost = 0.0
        
        return self._get_state_features()
    
    def _get_state_features(self) -> np.ndarray:
        """Extract current state features"""
        if self.current_patient is None:
            return np.zeros(20, dtype=np.float32)
        
        p = self.current_patient
        
        # Encode gender (M=1, F=0, Other=0.5)
        gender_enc = 1.0 if p.gender == "M" else (0.0 if p.gender == "F" else 0.5)
        
        # Encode severity (mild=0.25, moderate=0.5, severe=0.75, critical=1.0)
        severity_enc = {
            ConditionSeverity.MILD: 0.25,
            ConditionSeverity.MODERATE: 0.5,
            ConditionSeverity.SEVERE: 0.75,
            ConditionSeverity.CRITICAL: 1.0
        }[p.severity]
        
        # Vitals (normalized)
        vitals = [
            p.vitals.get("bp_systolic", 120) / 200.0,
            p.vitals.get("heart_rate", 72) / 150.0,
            p.vitals.get("temperature", 98.6) / 105.0,
            p.vitals.get("respiratory_rate", 16) / 30.0,
            p.vitals.get("oxygen_saturation", 98) / 100.0,
            p.vitals.get("pain_score", 0) / 10.0,
            p.vitals.get("bp_diastolic", 80) / 120.0
        ]
        
        # Lab results (normalized)
        labs = [
            p.lab_results.get("glucose", 100) / 200.0,
            p.lab_results.get("creatinine", 1.0) / 2.0,
            p.lab_results.get("hemoglobin", 14) / 20.0,
            p.lab_results.get("wbc", 7) / 20.0,
            p.lab_results.get("lactate", 1.0) / 5.0
        ]
        
        # Current treatments (one-hot encoded for top 3)
        current_treatments = [0.0, 0.0, 0.0]
        for i, med in enumerate(p.medications[:3]):
            current_treatments[i] = 1.0
        
        state = np.array([
            p.age / 100.0,
            gender_enc,
            severity_enc,
            p.risk_score,
            *vitals,
            *labs,
            *current_treatments,
            self.pathway_step / 10.0,
            self.current_patient.length_of_stay / 30.0,
            p.readmission_risk
        ], dtype=np.float32)
        
        return state
    
    def _apply_action(self, action: int) -> Dict[str, Any]:
        """Apply treatment action"""
        treatment = self.TREATMENT_OPTIONS[action]
        self.treatment_history.append(treatment)
        self.pathway_step += 1
        
        transition_info = {
            "treatment": treatment,
            "pathway_step": self.pathway_step,
            "cost": self.treatment_costs[treatment]
        }
        
        self.total_cost += self.treatment_costs[treatment]
        
        # Simulate treatment effect
        if treatment == "medication_adjustment":
            # Improve vitals
            self.current_patient.vitals["pain_score"] = max(0, self.current_patient.vitals["pain_score"] - 1.0)
            self.current_patient.risk_score = max(0, self.current_patient.risk_score - 0.05)
        
        elif treatment == "diagnostic_test":
            # Update lab results (simulate test revealing information)
            self.current_patient.lab_results["glucose"] += self.np_random.normal(0, 5)
        
        elif treatment == "specialist_consult":
            # Improve condition management
            self.current_patient.risk_score = max(0, self.current_patient.risk_score - 0.1)
        
        elif treatment == "procedure":
            # Significant improvement
            self.current_patient.risk_score = max(0, self.current_patient.risk_score - 0.2)
            self.current_patient.vitals["pain_score"] = max(0, self.current_patient.vitals["pain_score"] - 2.0)
        
        elif treatment == "monitoring":
            # No immediate effect, but tracks progress
            pass
        
        elif treatment == "discharge":
            # Patient ready for discharge
            transition_info["discharged"] = True
        
        # Evolve patient state
        self.current_patient = self.patient_generator.evolve_patient(
            self.current_patient, 1.0
        )
        
        return transition_info
    
    def step(
        self, action: Any
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Execute one step in the environment
        
        REFACTORED: Uses verifier for reward calculation and logs to observability
        """
        self.time_step += 1
        
        # Get current state
        current_state = self._get_state_features()
        previous_risk = current_state[3] if len(current_state) > 3 else 0.5
        
        # GOVERNANCE: Validate action before applying
        if self.enable_governance and self.safety_guardrails:
            is_valid, final_action, reason = self.safety_guardrails.validate_action(
                current_state, action, {
                    'treatment_history': self.treatment_history,
                    'pathway_step': self.pathway_step,
                    'patient': self.current_patient
                }
            )
            
            if not is_valid:
                # Action was overridden
                if self.audit_logger:
                    self.audit_logger.log_governance_override(
                        self.episode_id,
                        "TreatmentPathwayOptimization",
                        action,
                        final_action,
                        reason or "Safety guardrail triggered",
                        self.time_step
                    )
                
                # Use overridden action
                action = final_action if isinstance(final_action, int) else self.TREATMENT_OPTIONS.index(final_action) if final_action in self.TREATMENT_OPTIONS else action
        
        # Apply action and get transition info
        transition_info = self._apply_action(action)
        
        # Get next state
        next_state = self._get_state_features()
        current_risk = next_state[3] if len(next_state) > 3 else previous_risk
        
        # OBSERVABILITY: Log action trace
        if self.action_trace_logger:
            self.action_trace_logger.log_action(
                self.episode_id,
                self.time_step,
                current_state,
                action,
                next_state,
                transition_info,
                {'patient': self.current_patient.__dict__ if self.current_patient else None}
            )
        
        # VERIFIER: Calculate reward using verifier
        verifier_info = {
            'patient': self.current_patient,
            'previous_risk_score': previous_risk,
            'treatment_history': self.treatment_history,
            'pathway_step': self.pathway_step,
            'total_cost': self.total_cost,
            'cost': transition_info.get('cost', 0.0),
            **transition_info
        }
        
        reward, reward_breakdown = self.verifier.evaluate(
            current_state,
            action,
            next_state,
            verifier_info
        )
        
        # OBSERVABILITY: Log reward
        if self.reward_logger:
            verifier_name = self.verifier.__class__.__name__
            if isinstance(self.verifier, EnsembleVerifier):
                verifier_name = "EnsembleVerifier"
            
            self.reward_logger.log_reward(
                self.episode_id,
                self.time_step,
                current_state,
                action,
                reward,
                reward_breakdown,
                verifier_name,
                verifier_info
            )
            
            # Audit log
            if self.audit_logger:
                self.audit_logger.log_verifier_evaluation(
                    self.episode_id,
                    "TreatmentPathwayOptimization",
                    verifier_name,
                    reward,
                    reward_breakdown,
                    self.time_step
                )
        
        # Update cumulative reward
        self.cumulative_reward += reward
        
        # COMPLIANCE: Check compliance rules
        if self.enable_governance and self.compliance_rules:
            is_compliant, violations = self.compliance_rules.validate(
                next_state,
                self.TREATMENT_OPTIONS[action],
                verifier_info
            )
            
            if violations:
                self.compliance_violations.extend(violations)
                
                # Log violations
                if self.audit_logger:
                    for violation in violations:
                        self.audit_logger.log_compliance_violation(
                            self.episode_id,
                            "TreatmentPathwayOptimization",
                            violation.get('rule_type', 'unknown'),
                            violation,
                            self.time_step
                        )
        
        # Check termination
        terminated = self._is_done()
        truncated = self.time_step >= self.max_steps
        
        # Get KPIs
        kpis = self._get_kpis()
        self.kpi_history.append(kpis)
        
        # OBSERVABILITY: Record episode metrics if done
        if terminated or truncated:
            if self.episode_metrics:
                # Extract scores from reward breakdown
                clinical_score = reward_breakdown.get('ClinicalVerifier_risk_improvement', 0.0) + \
                               reward_breakdown.get('ClinicalVerifier_vital_stability', 0.0)
                efficiency_score = reward_breakdown.get('OperationalVerifier_pathway_efficiency', 0.0)
                financial_score = reward_breakdown.get('FinancialVerifier_cost_effectiveness', 0.0)
                
                self.episode_metrics.record_episode(
                    self.episode_id,
                    "TreatmentPathwayOptimization",
                    self.cumulative_reward,
                    clinical_score,
                    efficiency_score,
                    financial_score,
                    len(self.compliance_violations),
                    self.time_step,
                    current_risk,
                    self.total_cost,
                    {'treatment_history': self.treatment_history}
                )
        
        # Build info dictionary
        info = {
            "time_step": self.time_step,
            "reward_breakdown": reward_breakdown,
            "kpis": kpis.__dict__,
            "transition_info": transition_info,
            "episode_id": self.episode_id,
            "compliance_violations": len(self.compliance_violations)
        }
        
        return next_state, reward, terminated, truncated, info
    
    # REMOVED: _calculate_reward_components - now handled by verifier
    
    def _is_done(self) -> bool:
        """Check if episode is done"""
        if self.current_patient is None:
            return True
        
        # Done if discharged or pathway too long
        if len(self.treatment_history) > 0 and self.treatment_history[-1] == "discharge":
            return True
        
        if self.pathway_step >= 15:
            return True
        
        # Done if patient critical and no improvement
        if (self.current_patient.severity == ConditionSeverity.CRITICAL and 
            self.current_patient.risk_score > 0.8 and self.pathway_step > 5):
            return True
        
        return False
    
    def _get_kpis(self) -> KPIMetrics:
        """Calculate KPI metrics"""
        if self.current_patient is None:
            return KPIMetrics(
                clinical_outcomes={},
                operational_efficiency={},
                financial_metrics={},
                patient_satisfaction=0.0,
                risk_score=0.0,
                compliance_score=0.0,
                timestamp=self.time_step
            )
        
        p = self.current_patient
        
        return KPIMetrics(
            clinical_outcomes={
                "risk_score": p.risk_score,
                "vital_stability": 1.0 - abs(p.vitals.get("oxygen_saturation", 98) - 98) / 20.0,
                "condition_severity": p.severity.value
            },
            operational_efficiency={
                "pathway_length": self.pathway_step,
                "treatment_efficiency": self.pathway_step / max(1, len(set(self.treatment_history))),
                "time_to_improvement": self.pathway_step
            },
            financial_metrics={
                "total_cost": self.total_cost,
                "cost_per_step": self.total_cost / max(1, self.pathway_step),
                "cost_effectiveness": (1.0 - p.risk_score) / max(0.01, self.total_cost / 1000.0)
            },
            patient_satisfaction=1.0 - p.vitals.get("pain_score", 0) / 10.0,
            risk_score=p.risk_score,
            compliance_score=1.0 - (self.treatment_history.count("discharge") if self.pathway_step < 3 else 0) * 0.3,
            timestamp=self.time_step
        )
    
    def get_reward_breakdown(self) -> Dict[str, float]:
        """Get reward breakdown from last step"""
        if self.reward_logger and self.episode_id:
            latest_logs = self.reward_logger.get_episode_rewards(self.episode_id)
            if latest_logs:
                return latest_logs[-1].reward_breakdown
        return {}
    
    def get_observability_data(self) -> Dict[str, Any]:
        """Get observability data for current episode"""
        if not self.enable_observability:
            return {}
        
        data = {
            'episode_id': self.episode_id,
            'reward_summary': None,
            'action_traces': None,
            'episode_metrics': None,
            'audit_log': None
        }
        
        if self.reward_logger and self.episode_id:
            data['reward_summary'] = self.reward_logger.get_episode_summary(self.episode_id)
        
        if self.action_trace_logger and self.episode_id:
            data['action_traces'] = self.action_trace_logger.get_state_transitions(self.episode_id)
        
        if self.episode_metrics and self.episode_id:
            data['episode_metrics'] = self.episode_metrics.get_episode_metrics(self.episode_id)
            if data['episode_metrics']:
                data['episode_metrics'] = data['episode_metrics'].__dict__
        
        if self.audit_logger and self.episode_id:
            data['audit_log'] = [
                {
                    'event_type': log.event_type.value,
                    'message': log.message,
                    'details': log.details,
                    'timestamp': log.timestamp.isoformat()
                }
                for log in self.audit_logger.get_episode_audit_log(self.episode_id)
            ]
        
        return data

