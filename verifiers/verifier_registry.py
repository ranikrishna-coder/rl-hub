"""
Verifier Registry
Manages verifier instances and configurations
"""

from typing import Dict, Optional, List, Type
from .base_verifier import BaseVerifier, VerifierConfig
from .clinical_verifier import ClinicalVerifier
from .operational_verifier import OperationalVerifier
from .financial_verifier import FinancialVerifier
from .compliance_verifier import ComplianceVerifier
from .ensemble_verifier import EnsembleVerifier


class VerifierRegistry:
    """
    Registry for managing verifier instances
    
    Provides:
    - Verifier creation and configuration
    - Verifier lookup by name
    - Default verifier sets for environments
    """
    
    _verifier_classes: Dict[str, Type[BaseVerifier]] = {
        'clinical': ClinicalVerifier,
        'operational': OperationalVerifier,
        'financial': FinancialVerifier,
        'compliance': ComplianceVerifier,
        'ensemble': EnsembleVerifier
    }
    
    _instances: Dict[str, BaseVerifier] = {}
    _default_configs: Dict[str, Dict] = {}
    
    @classmethod
    def register_verifier_class(
        cls,
        name: str,
        verifier_class: Type[BaseVerifier]
    ):
        """Register a verifier class"""
        cls._verifier_classes[name] = verifier_class
    
    @classmethod
    def create_verifier(
        cls,
        verifier_type: str,
        config: Optional[VerifierConfig] = None,
        instance_id: Optional[str] = None
    ) -> BaseVerifier:
        """
        Create a verifier instance
        
        Args:
            verifier_type: Type of verifier ('clinical', 'operational', etc.)
            config: Optional configuration
            instance_id: Optional ID for storing instance
        
        Returns:
            Verifier instance
        """
        if verifier_type not in cls._verifier_classes:
            raise ValueError(f"Unknown verifier type: {verifier_type}")
        
        verifier_class = cls._verifier_classes[verifier_type]
        verifier = verifier_class(config)
        
        if instance_id:
            cls._instances[instance_id] = verifier
        
        return verifier
    
    @classmethod
    def create_default_ensemble(
        cls,
        configs: Optional[Dict[str, VerifierConfig]] = None,
        instance_id: Optional[str] = None
    ) -> EnsembleVerifier:
        """
        Create default ensemble verifier for TreatmentPathwayOptimization
        
        Args:
            configs: Optional per-verifier configurations
            instance_id: Optional ID for storing instance
        
        Returns:
            Ensemble verifier with clinical, operational, financial, compliance
        """
        configs = configs or {}
        
        # Create individual verifiers
        clinical = cls.create_verifier('clinical', configs.get('clinical'))
        operational = cls.create_verifier('operational', configs.get('operational'))
        financial = cls.create_verifier('financial', configs.get('financial'))
        compliance = cls.create_verifier('compliance', configs.get('compliance'))
        
        # Create ensemble
        ensemble = EnsembleVerifier(
            verifiers=[clinical, operational, financial, compliance]
        )
        
        if instance_id:
            cls._instances[instance_id] = ensemble
        
        return ensemble
    
    @classmethod
    def get_verifier(cls, instance_id: str) -> Optional[BaseVerifier]:
        """Get verifier instance by ID"""
        return cls._instances.get(instance_id)
    
    @classmethod
    def list_verifier_types(cls) -> List[str]:
        """List available verifier types"""
        return list(cls._verifier_classes.keys())
    
    @classmethod
    def list_instances(cls) -> Dict[str, str]:
        """List all registered instances"""
        return {
            instance_id: verifier.__class__.__name__
            for instance_id, verifier in cls._instances.items()
        }


# Convenience functions
def get_verifier(instance_id: str) -> Optional[BaseVerifier]:
    """Get verifier by ID"""
    return VerifierRegistry.get_verifier(instance_id)


def register_verifier(instance_id: str, verifier: BaseVerifier):
    """Register a verifier instance"""
    VerifierRegistry._instances[instance_id] = verifier

