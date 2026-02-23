"""
Audit Logger
Logs all system events for audit and compliance
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AuditEventType(Enum):
    """Types of audit events"""
    VERIFIER_EVALUATION = "verifier_evaluation"
    ACTION_TAKEN = "action_taken"
    COMPLIANCE_VIOLATION = "compliance_violation"
    GOVERNANCE_OVERRIDE = "governance_override"
    CONFIG_CHANGE = "config_change"
    ERROR = "error"


@dataclass
class AuditLogEntry:
    """Single audit log entry"""
    event_type: AuditEventType
    episode_id: str
    step_id: Optional[int]
    environment_name: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None


class AuditLogger:
    """
    Logger for audit events
    
    Tracks:
    - All verifier evaluations
    - Actions taken
    - Compliance violations
    - Governance overrides
    - Configuration changes
    - Errors
    """
    
    def __init__(self, persist_to_db: bool = False, db_connection=None):
        """
        Initialize audit logger
        
        Args:
            persist_to_db: Whether to persist logs to database
            db_connection: Database connection (if persisting)
        """
        self.persist_to_db = persist_to_db
        self.db_connection = db_connection
        self.logs: List[AuditLogEntry] = []
        self.episode_logs: Dict[str, List[AuditLogEntry]] = {}
    
    def log_event(
        self,
        event_type: AuditEventType,
        episode_id: str,
        environment_name: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        step_id: Optional[int] = None,
        user_id: Optional[str] = None
    ):
        """
        Log an audit event
        
        Args:
            event_type: Type of event
            episode_id: Episode identifier
            environment_name: Name of environment
            message: Human-readable message
            details: Additional event details
            step_id: Step number (if applicable)
            user_id: User who triggered event (if applicable)
        """
        entry = AuditLogEntry(
            event_type=event_type,
            episode_id=episode_id,
            step_id=step_id,
            environment_name=environment_name,
            message=message,
            details=details or {},
            timestamp=datetime.now(),
            user_id=user_id
        )
        
        # Store in memory
        self.logs.append(entry)
        
        if episode_id not in self.episode_logs:
            self.episode_logs[episode_id] = []
        self.episode_logs[episode_id].append(entry)
        
        # Persist to database if enabled
        if self.persist_to_db and self.db_connection:
            self._persist_to_db(entry)
    
    def log_verifier_evaluation(
        self,
        episode_id: str,
        environment_name: str,
        verifier_name: str,
        reward: float,
        breakdown: Dict[str, float],
        step_id: Optional[int] = None
    ):
        """Log verifier evaluation"""
        self.log_event(
            event_type=AuditEventType.VERIFIER_EVALUATION,
            episode_id=episode_id,
            environment_name=environment_name,
            message=f"Verifier {verifier_name} evaluated reward: {reward:.4f}",
            details={
                'verifier_name': verifier_name,
                'reward': reward,
                'breakdown': breakdown
            },
            step_id=step_id
        )
    
    def log_compliance_violation(
        self,
        episode_id: str,
        environment_name: str,
        violation_type: str,
        violation_details: Dict[str, Any],
        step_id: Optional[int] = None
    ):
        """Log compliance violation"""
        self.log_event(
            event_type=AuditEventType.COMPLIANCE_VIOLATION,
            episode_id=episode_id,
            environment_name=environment_name,
            message=f"Compliance violation: {violation_type}",
            details={
                'violation_type': violation_type,
                **violation_details
            },
            step_id=step_id
        )
    
    def log_governance_override(
        self,
        episode_id: str,
        environment_name: str,
        original_action: Any,
        overridden_action: Any,
        reason: str,
        step_id: Optional[int] = None
    ):
        """Log governance override"""
        self.log_event(
            event_type=AuditEventType.GOVERNANCE_OVERRIDE,
            episode_id=episode_id,
            environment_name=environment_name,
            message=f"Governance override: {reason}",
            details={
                'original_action': str(original_action),
                'overridden_action': str(overridden_action),
                'reason': reason
            },
            step_id=step_id
        )
    
    def get_episode_audit_log(self, episode_id: str) -> List[AuditLogEntry]:
        """Get audit log for an episode"""
        return self.episode_logs.get(episode_id, [])
    
    def get_compliance_violations(
        self,
        episode_id: Optional[str] = None,
        environment_name: Optional[str] = None
    ) -> List[AuditLogEntry]:
        """Get all compliance violations"""
        violations = [
            log for log in self.logs
            if log.event_type == AuditEventType.COMPLIANCE_VIOLATION
        ]
        
        if episode_id:
            violations = [v for v in violations if v.episode_id == episode_id]
        
        if environment_name:
            violations = [v for v in violations if v.environment_name == environment_name]
        
        return violations
    
    def _persist_to_db(self, entry: AuditLogEntry):
        """Persist audit log entry to database"""
        # This will be implemented when database schema is ready
        pass
    
    def clear_logs(self):
        """Clear all audit logs (for testing/debugging)"""
        self.logs = []
        self.episode_logs = {}

