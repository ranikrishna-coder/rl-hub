"""
Safety Guardrails
Validates actions and applies safety overrides
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass
from enum import Enum


class OverrideAction(Enum):
    """Actions that can be taken on validation"""
    ALLOW = "allow"
    BLOCK = "block"
    MODIFY = "modify"
    ESCALATE = "escalate"


@dataclass
class SafetyConfig:
    """Configuration for safety guardrails"""
    max_risk_threshold: float = 0.8
    compliance_hard_stop: bool = True
    human_in_the_loop: bool = False
    override_actions: Dict[str, OverrideAction] = None
    
    def __post_init__(self):
        if self.override_actions is None:
            self.override_actions = {}


class SafetyGuardrails:
    """
    Safety guardrails for RL environment actions
    
    Validates actions and can:
    - Allow action
    - Block action
    - Modify action
    - Escalate to human review
    """
    
    def __init__(self, config: Optional[SafetyConfig] = None):
        """
        Initialize safety guardrails
        
        Args:
            config: Safety configuration
        """
        self.config = config or SafetyConfig()
        self.override_history = []
    
    def validate_action(
        self,
        state: np.ndarray,
        action: Any,
        info: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Validate an action and return override if needed
        
        Args:
            state: Current state
            action: Proposed action
            info: Additional context
        
        Returns:
            Tuple of (is_valid, final_action, reason)
            - is_valid: Whether action is safe
            - final_action: Action to take (may be modified)
            - reason: Reason for override (if any)
        """
        info = info or {}
        final_action = action
        reason = None
        
        # Check risk threshold
        if len(state) > 3:
            risk_score = state[3]
            if risk_score > self.config.max_risk_threshold:
                # High risk - check if action is appropriate
                override_action = self._check_high_risk_action(state, action, info)
                if override_action != OverrideAction.ALLOW:
                    final_action, reason = self._apply_override(
                        override_action, state, action, info,
                        f"Risk score {risk_score:.2f} exceeds threshold {self.config.max_risk_threshold}"
                    )
                    return False, final_action, reason
        
        # Check compliance rules
        if self.config.compliance_hard_stop:
            compliance_check = self._check_compliance(state, action, info)
            if not compliance_check[0]:
                override_action = OverrideAction.BLOCK if self.config.compliance_hard_stop else OverrideAction.ESCALATE
                final_action, reason = self._apply_override(
                    override_action, state, action, info,
                    f"Compliance violation: {compliance_check[1]}"
                )
                return False, final_action, reason
        
        # Check for critical patient conditions
        critical_check = self._check_critical_condition(state, action, info)
        if not critical_check[0]:
            override_action = OverrideAction.MODIFY
            final_action, reason = self._apply_override(
                override_action, state, action, info,
                f"Critical condition: {critical_check[1]}"
            )
            return False, final_action, reason
        
        # Action is valid
        return True, final_action, None
    
    def _check_high_risk_action(
        self,
        state: np.ndarray,
        action: Any,
        info: Dict[str, Any]
    ) -> OverrideAction:
        """Check if action is appropriate for high-risk patient"""
        # For high-risk patients, block non-urgent actions
        non_urgent_actions = ["monitoring", "discharge"]
        
        if str(action).lower() in [a.lower() for a in non_urgent_actions]:
            return OverrideAction.BLOCK
        
        return OverrideAction.ALLOW
    
    def _check_compliance(
        self,
        state: np.ndarray,
        action: Any,
        info: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Check compliance rules"""
        treatment_history = info.get('treatment_history', [])
        pathway_step = info.get('pathway_step', 0)
        
        # Check premature discharge
        if action == "discharge" and pathway_step < 3:
            return False, "Premature discharge: minimum pathway steps not met"
        
        # Check for too many procedures
        procedure_count = treatment_history.count("procedure")
        if procedure_count > 2:
            return False, f"Too many procedures: {procedure_count} exceeds limit of 2"
        
        return True, ""
    
    def _check_critical_condition(
        self,
        state: np.ndarray,
        action: Any,
        info: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Check for critical patient conditions"""
        if len(state) > 2:
            severity = state[2]
            if severity > 0.75:  # Critical condition
                # Critical patients should not be discharged
                if action == "discharge":
                    return False, "Critical patient cannot be discharged"
        
        return True, ""
    
    def _apply_override(
        self,
        override_action: OverrideAction,
        state: np.ndarray,
        action: Any,
        info: Dict[str, Any],
        reason: str
    ) -> Tuple[Any, str]:
        """Apply override action"""
        self.override_history.append({
            'original_action': action,
            'override_action': override_action,
            'reason': reason,
            'state': state.copy() if isinstance(state, np.ndarray) else state
        })
        
        if override_action == OverrideAction.BLOCK:
            # Return a safe default action (monitoring)
            return "monitoring", f"BLOCKED: {reason}"
        
        elif override_action == OverrideAction.MODIFY:
            # Modify to a safer action
            if action == "discharge":
                return "monitoring", f"MODIFIED: {reason} - changed discharge to monitoring"
            return action, f"MODIFIED: {reason}"
        
        elif override_action == OverrideAction.ESCALATE:
            # Escalate to human review
            if self.config.human_in_the_loop:
                return action, f"ESCALATED: {reason} - requires human review"
            else:
                # If no human in loop, block the action
                return "monitoring", f"BLOCKED (no human review): {reason}"
        
        return action, reason
    
    def get_override_history(self) -> list:
        """Get history of overrides"""
        return self.override_history.copy()
    
    def clear_history(self):
        """Clear override history"""
        self.override_history = []

