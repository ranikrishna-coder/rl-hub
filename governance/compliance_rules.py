"""
Compliance Rules
Defines and enforces compliance rules for RL environments
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np


class ComplianceRuleType(Enum):
    """Types of compliance rules"""
    PATHWAY_LENGTH = "pathway_length"
    TREATMENT_SEQUENCE = "treatment_sequence"
    RISK_MANAGEMENT = "risk_management"
    COST_CONTROL = "cost_control"
    CLINICAL_GUIDELINE = "clinical_guideline"


@dataclass
class ComplianceRule:
    """Single compliance rule"""
    rule_type: ComplianceRuleType
    rule_name: str
    description: str
    enabled: bool = True
    severity: str = "warning"  # "warning", "error", "critical"
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class ComplianceRules:
    """
    Manages compliance rules for RL environments
    
    Provides:
    - Rule definition
    - Rule validation
    - Violation tracking
    """
    
    def __init__(self):
        """Initialize compliance rules"""
        self.rules: List[ComplianceRule] = []
        self.violations: List[Dict[str, Any]] = []
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default compliance rules for TreatmentPathwayOptimization"""
        # Pathway length rule
        self.add_rule(ComplianceRule(
            rule_type=ComplianceRuleType.PATHWAY_LENGTH,
            rule_name="minimum_pathway_steps",
            description="Minimum number of pathway steps before discharge",
            enabled=True,
            severity="error",
            parameters={"min_steps": 3}
        ))
        
        # Treatment sequence rule
        self.add_rule(ComplianceRule(
            rule_type=ComplianceRuleType.TREATMENT_SEQUENCE,
            rule_name="max_procedures",
            description="Maximum number of procedures per episode",
            enabled=True,
            severity="warning",
            parameters={"max_procedures": 2}
        ))
        
        # Risk management rule
        self.add_rule(ComplianceRule(
            rule_type=ComplianceRuleType.RISK_MANAGEMENT,
            rule_name="max_risk_score",
            description="Maximum acceptable risk score",
            enabled=True,
            severity="error",
            parameters={"max_risk": 0.8}
        ))
    
    def add_rule(self, rule: ComplianceRule):
        """Add a compliance rule"""
        self.rules.append(rule)
    
    def remove_rule(self, rule_name: str):
        """Remove a compliance rule"""
        self.rules = [r for r in self.rules if r.rule_name != rule_name]
    
    def validate(
        self,
        state: np.ndarray,
        action: Any,
        info: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validate action against all compliance rules
        
        Args:
            state: Current state
            action: Proposed action
            info: Additional context
        
        Returns:
            Tuple of (is_compliant, violations)
        """
        info = info or {}
        violations = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            violation = self._check_rule(rule, state, action, info)
            if violation:
                violations.append(violation)
                self.violations.append(violation)
        
        is_compliant = len(violations) == 0
        return is_compliant, violations
    
    def _check_rule(
        self,
        rule: ComplianceRule,
        state: np.ndarray,
        action: Any,
        info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check a single rule"""
        if rule.rule_type == ComplianceRuleType.PATHWAY_LENGTH:
            return self._check_pathway_length(rule, action, info)
        elif rule.rule_type == ComplianceRuleType.TREATMENT_SEQUENCE:
            return self._check_treatment_sequence(rule, action, info)
        elif rule.rule_type == ComplianceRuleType.RISK_MANAGEMENT:
            return self._check_risk_management(rule, state, info)
        elif rule.rule_type == ComplianceRuleType.COST_CONTROL:
            return self._check_cost_control(rule, info)
        elif rule.rule_type == ComplianceRuleType.CLINICAL_GUIDELINE:
            return self._check_clinical_guideline(rule, state, action, info)
        
        return None
    
    def _check_pathway_length(
        self,
        rule: ComplianceRule,
        action: Any,
        info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check pathway length rule"""
        min_steps = rule.parameters.get('min_steps', 3)
        pathway_step = info.get('pathway_step', 0)
        
        if action == "discharge" and pathway_step < min_steps:
            return {
                'rule_name': rule.rule_name,
                'rule_type': rule.rule_type.value,
                'severity': rule.severity,
                'message': f"Premature discharge: pathway step {pathway_step} < minimum {min_steps}",
                'parameters': {'pathway_step': pathway_step, 'min_steps': min_steps}
            }
        
        return None
    
    def _check_treatment_sequence(
        self,
        rule: ComplianceRule,
        action: Any,
        info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check treatment sequence rule"""
        max_procedures = rule.parameters.get('max_procedures', 2)
        treatment_history = info.get('treatment_history', [])
        procedure_count = treatment_history.count("procedure")
        
        if action == "procedure" and procedure_count >= max_procedures:
            return {
                'rule_name': rule.rule_name,
                'rule_type': rule.rule_type.value,
                'severity': rule.severity,
                'message': f"Too many procedures: {procedure_count + 1} exceeds maximum {max_procedures}",
                'parameters': {'procedure_count': procedure_count + 1, 'max_procedures': max_procedures}
            }
        
        return None
    
    def _check_risk_management(
        self,
        rule: ComplianceRule,
        state: np.ndarray,
        info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check risk management rule"""
        max_risk = rule.parameters.get('max_risk', 0.8)
        
        if len(state) > 3:
            risk_score = state[3]
            if risk_score > max_risk:
                return {
                    'rule_name': rule.rule_name,
                    'rule_type': rule.rule_type.value,
                    'severity': rule.severity,
                    'message': f"Risk score {risk_score:.2f} exceeds maximum {max_risk}",
                    'parameters': {'risk_score': risk_score, 'max_risk': max_risk}
                }
        
        return None
    
    def _check_cost_control(
        self,
        rule: ComplianceRule,
        info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check cost control rule"""
        # Placeholder for cost control rules
        return None
    
    def _check_clinical_guideline(
        self,
        rule: ComplianceRule,
        state: np.ndarray,
        action: Any,
        info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check clinical guideline rule"""
        # Placeholder for clinical guideline rules
        return None
    
    def get_violations(
        self,
        episode_id: Optional[str] = None,
        rule_type: Optional[ComplianceRuleType] = None
    ) -> List[Dict[str, Any]]:
        """Get compliance violations"""
        violations = self.violations.copy()
        
        if episode_id:
            violations = [v for v in violations if v.get('episode_id') == episode_id]
        
        if rule_type:
            violations = [v for v in violations if v.get('rule_type') == rule_type.value]
        
        return violations
    
    def clear_violations(self):
        """Clear violation history"""
        self.violations = []

