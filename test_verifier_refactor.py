#!/usr/bin/env python3
"""
Test script for verifier-based refactoring
Tests TreatmentPathwayOptimization environment with verifiers
"""

import sys
import os
sys.path.insert(0, '.')

def test_verifier_architecture():
    """Test verifier architecture components"""
    print("=" * 80)
    print("TESTING VERIFIER ARCHITECTURE")
    print("=" * 80)
    
    try:
        # Test imports
        from verifiers.base_verifier import BaseVerifier, VerifierConfig
        from verifiers.clinical_verifier import ClinicalVerifier
        from verifiers.operational_verifier import OperationalVerifier
        from verifiers.financial_verifier import FinancialVerifier
        from verifiers.compliance_verifier import ComplianceVerifier
        from verifiers.ensemble_verifier import EnsembleVerifier
        from verifiers.verifier_registry import VerifierRegistry
        
        print("✅ All verifier imports successful")
        
        # Test verifier creation
        clinical = ClinicalVerifier()
        operational = OperationalVerifier()
        financial = FinancialVerifier()
        compliance = ComplianceVerifier()
        
        print("✅ Individual verifiers created")
        
        # Test ensemble
        ensemble = EnsembleVerifier([clinical, operational, financial, compliance])
        print(f"✅ Ensemble verifier created with {len(ensemble.verifiers)} verifiers")
        
        # Test registry
        default_ensemble = VerifierRegistry.create_default_ensemble()
        print(f"✅ Default ensemble created via registry: {len(default_ensemble.verifiers)} verifiers")
        
        return True
        
    except Exception as e:
        print(f"❌ Verifier architecture test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_observability():
    """Test observability layer"""
    print("\n" + "=" * 80)
    print("TESTING OBSERVABILITY LAYER")
    print("=" * 80)
    
    try:
        from observability.reward_logger import RewardLogger
        from observability.action_trace_logger import ActionTraceLogger
        from observability.episode_metrics import EpisodeMetricsTracker
        from observability.audit_logger import AuditLogger, AuditEventType
        
        print("✅ All observability imports successful")
        
        # Test loggers
        reward_logger = RewardLogger()
        action_trace_logger = ActionTraceLogger()
        episode_metrics = EpisodeMetricsTracker()
        audit_logger = AuditLogger()
        
        print("✅ All observability loggers created")
        
        return True
        
    except Exception as e:
        print(f"❌ Observability test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_governance():
    """Test governance layer"""
    print("\n" + "=" * 80)
    print("TESTING GOVERNANCE LAYER")
    print("=" * 80)
    
    try:
        from governance.safety_guardrails import SafetyGuardrails, SafetyConfig
        from governance.risk_thresholds import RiskThresholds, RiskThresholdConfig
        from governance.compliance_rules import ComplianceRules
        
        print("✅ All governance imports successful")
        
        # Test governance components
        safety_config = SafetyConfig()
        safety_guardrails = SafetyGuardrails(safety_config)
        risk_thresholds = RiskThresholds()
        compliance_rules = ComplianceRules()
        
        print("✅ All governance components created")
        
        return True
        
    except Exception as e:
        print(f"❌ Governance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_environment_refactor():
    """Test refactored environment"""
    print("\n" + "=" * 80)
    print("TESTING REFACTORED ENVIRONMENT")
    print("=" * 80)
    
    try:
        from environments.clinical.treatment_pathway_optimization import TreatmentPathwayOptimizationEnv
        from verifiers.verifier_registry import VerifierRegistry
        
        print("✅ Refactored environment import successful")
        
        # Test environment creation with default verifier
        env = TreatmentPathwayOptimizationEnv()
        print("✅ Environment created with default ensemble verifier")
        print(f"   Verifier type: {env.verifier.__class__.__name__}")
        print(f"   Observability enabled: {env.enable_observability}")
        print(f"   Governance enabled: {env.enable_governance}")
        
        # Test environment creation with custom verifier
        custom_verifier = VerifierRegistry.create_default_ensemble()
        env_custom = TreatmentPathwayOptimizationEnv(verifier=custom_verifier)
        print("✅ Environment created with custom verifier")
        
        # Test environment creation without observability/governance
        env_minimal = TreatmentPathwayOptimizationEnv(
            enable_observability=False,
            enable_governance=False
        )
        print("✅ Environment created with minimal features")
        
        return True
        
    except Exception as e:
        print(f"❌ Environment refactor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n🧪 VERIFIER REFACTORING TEST SUITE")
    print("=" * 80)
    
    results = []
    
    results.append(("Verifier Architecture", test_verifier_architecture()))
    results.append(("Observability Layer", test_observability()))
    results.append(("Governance Layer", test_governance()))
    results.append(("Environment Refactor", test_environment_refactor()))
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! Verifier refactoring is complete.")
    else:
        print("\n⚠️  Some tests failed. Please review errors above.")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())

