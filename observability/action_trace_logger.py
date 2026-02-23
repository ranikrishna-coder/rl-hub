"""
Action Trace Logger
Logs state-action-state transitions for full traceability
"""

from typing import Dict, Any, Optional, List
import numpy as np
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class ActionTraceEntry:
    """Single action trace entry"""
    episode_id: str
    step_id: int
    before_state: np.ndarray
    action: Any
    after_state: np.ndarray
    transition_info: Dict[str, Any]
    timestamp: datetime
    metadata: Dict[str, Any]


class ActionTraceLogger:
    """
    Logger for action traces
    
    Tracks:
    - Before state
    - Action taken
    - After state
    - Transition information
    """
    
    def __init__(self, persist_to_db: bool = False, db_connection=None):
        """
        Initialize action trace logger
        
        Args:
            persist_to_db: Whether to persist logs to database
            db_connection: Database connection (if persisting)
        """
        self.persist_to_db = persist_to_db
        self.db_connection = db_connection
        self.traces: List[ActionTraceEntry] = []
        self.episode_traces: Dict[str, List[ActionTraceEntry]] = {}
    
    def log_action(
        self,
        episode_id: str,
        step_id: int,
        before_state: np.ndarray,
        action: Any,
        after_state: np.ndarray,
        transition_info: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log an action trace
        
        Args:
            episode_id: Unique episode identifier
            step_id: Step number within episode
            before_state: State before action
            action: Action taken
            after_state: State after action
            transition_info: Information about the transition
            metadata: Additional metadata
        """
        entry = ActionTraceEntry(
            episode_id=episode_id,
            step_id=step_id,
            before_state=before_state.copy() if isinstance(before_state, np.ndarray) else before_state,
            action=action,
            after_state=after_state.copy() if isinstance(after_state, np.ndarray) else after_state,
            transition_info=transition_info or {},
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        # Store in memory
        self.traces.append(entry)
        
        if episode_id not in self.episode_traces:
            self.episode_traces[episode_id] = []
        self.episode_traces[episode_id].append(entry)
        
        # Persist to database if enabled
        if self.persist_to_db and self.db_connection:
            self._persist_to_db(entry)
    
    def get_episode_trace(self, episode_id: str) -> List[ActionTraceEntry]:
        """Get full trace for an episode"""
        return self.episode_traces.get(episode_id, [])
    
    def get_step_trace(self, episode_id: str, step_id: int) -> Optional[ActionTraceEntry]:
        """Get trace for specific step"""
        episode_traces = self.get_episode_trace(episode_id)
        for trace in episode_traces:
            if trace.step_id == step_id:
                return trace
        return None
    
    def get_state_transitions(self, episode_id: str) -> List[Dict[str, Any]]:
        """Get state transitions for an episode"""
        traces = self.get_episode_trace(episode_id)
        return [
            {
                'step_id': trace.step_id,
                'before_state': trace.before_state.tolist() if isinstance(trace.before_state, np.ndarray) else trace.before_state,
                'action': trace.action,
                'after_state': trace.after_state.tolist() if isinstance(trace.after_state, np.ndarray) else trace.after_state,
                'transition_info': trace.transition_info
            }
            for trace in traces
        ]
    
    def _persist_to_db(self, entry: ActionTraceEntry):
        """Persist trace entry to database"""
        # This will be implemented when database schema is ready
        pass
    
    def clear_traces(self):
        """Clear all traces (for testing/debugging)"""
        self.traces = []
        self.episode_traces = {}

