"""
Episode Metrics
Tracks aggregate metrics across episodes
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np


@dataclass
class EpisodeMetricsRecord:
    """Metrics for a single episode (dataclass). Use EpisodeMetricsTracker to track multiple episodes."""
    episode_id: str
    environment_name: str
    cumulative_reward: float
    clinical_score: float
    efficiency_score: float
    financial_score: float
    compliance_violations: int
    episode_length: int
    final_risk_score: float
    total_cost: float
    timestamp: datetime
    metadata: Dict[str, Any]


class EpisodeMetricsTracker:
    """
    Tracks metrics across episodes
    
    Aggregates:
    - Cumulative reward
    - Clinical outcomes
    - Operational efficiency
    - Financial performance
    - Compliance violations
    """
    
    def __init__(self, persist_to_db: bool = False, db_connection=None, **kwargs):
        """
        Initialize episode metrics tracker.
        Extra kwargs are ignored (e.g. from mistaken use of EpisodeMetricsRecord fields).
        """
        self.persist_to_db = persist_to_db
        self.db_connection = db_connection
        self.metrics: Dict[str, EpisodeMetricsRecord] = {}
    
    def record_episode(
        self,
        episode_id: str,
        environment_name: str,
        cumulative_reward: float,
        clinical_score: float,
        efficiency_score: float,
        financial_score: float,
        compliance_violations: int,
        episode_length: int,
        final_risk_score: float,
        total_cost: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record metrics for an episode
        
        Args:
            episode_id: Unique episode identifier
            environment_name: Name of environment
            cumulative_reward: Total reward for episode
            clinical_score: Aggregate clinical score
            efficiency_score: Aggregate efficiency score
            financial_score: Aggregate financial score
            compliance_violations: Number of compliance violations
            episode_length: Number of steps in episode
            final_risk_score: Risk score at end of episode
            total_cost: Total cost for episode
            metadata: Additional metadata
        """
        metrics = EpisodeMetricsRecord(
            episode_id=episode_id,
            environment_name=environment_name,
            cumulative_reward=cumulative_reward,
            clinical_score=clinical_score,
            efficiency_score=efficiency_score,
            financial_score=financial_score,
            compliance_violations=compliance_violations,
            episode_length=episode_length,
            final_risk_score=final_risk_score,
            total_cost=total_cost,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self.metrics[episode_id] = metrics
        
        # Persist to database if enabled
        if self.persist_to_db and self.db_connection:
            self._persist_to_db(metrics)
    
    def get_episode_metrics(self, episode_id: str) -> Optional[EpisodeMetricsRecord]:
        """Get metrics for specific episode"""
        return self.metrics.get(episode_id)
    
    def get_aggregate_metrics(
        self,
        environment_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get aggregate metrics across episodes
        
        Args:
            environment_name: Filter by environment name (optional)
            limit: Limit number of episodes to aggregate (optional)
        
        Returns:
            Dictionary with aggregate statistics
        """
        filtered_metrics = list(self.metrics.values())
        
        if environment_name:
            filtered_metrics = [m for m in filtered_metrics if m.environment_name == environment_name]
        
        if limit:
            filtered_metrics = filtered_metrics[-limit:]
        
        if not filtered_metrics:
            return {}
        
        return {
            'num_episodes': len(filtered_metrics),
            'avg_cumulative_reward': np.mean([m.cumulative_reward for m in filtered_metrics]),
            'avg_clinical_score': np.mean([m.clinical_score for m in filtered_metrics]),
            'avg_efficiency_score': np.mean([m.efficiency_score for m in filtered_metrics]),
            'avg_financial_score': np.mean([m.financial_score for m in filtered_metrics]),
            'total_compliance_violations': sum(m.compliance_violations for m in filtered_metrics),
            'avg_episode_length': np.mean([m.episode_length for m in filtered_metrics]),
            'avg_final_risk_score': np.mean([m.final_risk_score for m in filtered_metrics]),
            'avg_total_cost': np.mean([m.total_cost for m in filtered_metrics])
        }
    
    def _persist_to_db(self, metrics: EpisodeMetricsRecord):
        """Persist metrics to database"""
        # This will be implemented when database schema is ready
        pass
    
    def clear_metrics(self):
        """Clear all metrics (for testing/debugging)"""
        self.metrics = {}


# Backward compatibility: EpisodeMetrics is the tracker (not the dataclass)
EpisodeMetrics = EpisodeMetricsTracker

