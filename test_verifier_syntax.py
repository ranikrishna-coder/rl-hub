#!/usr/bin/env python3
"""
Syntax-only test for verifier refactoring
Tests code structure without requiring dependencies
"""

import sys
import os
import ast
import re

def check_syntax(file_path):
    """Check Python syntax of a file"""
    try:
        with open(file_path, 'r') as f:
            code = f.read()
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def check_imports(file_path):
    """Check if imports are correct (structure-wise)"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for common import patterns
        issues = []
        
        # Check for relative imports
        if 'from .' in content or 'from ..' in content:
            # This is fine for package structure
            pass
        
        # Check for obvious import errors
        if 'import' in content:
            # Basic check - if file has imports, syntax should be valid
            pass
        
        return True, issues
    except Exception as e:
        return False, [str(e)]

def test_file_structure():
    """Test file structure without executing"""
    print("=" * 80)
    print("SYNTAX AND STRUCTURE TEST (No Dependencies Required)")
    print("=" * 80)
    
    test_files = []
    
    # Verifier files
    for f in ['base_verifier.py', 'clinical_verifier.py', 'operational_verifier.py', 
              'financial_verifier.py', 'compliance_verifier.py', 'ensemble_verifier.py', 
              'verifier_registry.py']:
        test_files.append(('verifiers', f))
    
    # Observability files
    for f in ['reward_logger.py', 'action_trace_logger.py', 'episode_metrics.py', 
              'audit_logger.py']:
        test_files.append(('observability', f))
    
    # Governance files
    for f in ['safety_guardrails.py', 'risk_thresholds.py', 'compliance_rules.py']:
        test_files.append(('governance', f))
    
    # Refactored environment
    test_files.append(('environments/clinical', 'treatment_pathway_optimization.py'))
    
    results = []
    
    for module_dir, filename in test_files:
        file_path = os.path.join(module_dir, filename)
        if os.path.exists(file_path):
            syntax_ok, syntax_error = check_syntax(file_path)
            imports_ok, import_issues = check_imports(file_path)
            
            if syntax_ok and imports_ok:
                results.append((file_path, True, None))
                print(f"✅ {file_path}: Syntax OK")
            else:
                error_msg = syntax_error or str(import_issues)
                results.append((file_path, False, error_msg))
                print(f"❌ {file_path}: {error_msg}")
        else:
            results.append((file_path, False, "File not found"))
            print(f"❌ {file_path}: File not found")
    
    print("\n" + "=" * 80)
    print("STRUCTURE TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    
    print(f"Files checked: {total}")
    print(f"Syntax valid: {passed}")
    print(f"Syntax errors: {total - passed}")
    
    if passed == total:
        print("\n✅ All files have valid Python syntax!")
        print("   (Dependencies like numpy/gymnasium need to be installed for runtime tests)")
        return True
    else:
        print("\n⚠️  Some files have syntax errors")
        for file_path, ok, error in results:
            if not ok:
                print(f"   {file_path}: {error}")
        return False

def check_class_structure():
    """Check that required classes exist"""
    print("\n" + "=" * 80)
    print("CLASS STRUCTURE CHECK")
    print("=" * 80)
    
    checks = [
        ('verifiers/base_verifier.py', 'class BaseVerifier'),
        ('verifiers/clinical_verifier.py', 'class ClinicalVerifier'),
        ('verifiers/operational_verifier.py', 'class OperationalVerifier'),
        ('verifiers/financial_verifier.py', 'class FinancialVerifier'),
        ('verifiers/compliance_verifier.py', 'class ComplianceVerifier'),
        ('verifiers/ensemble_verifier.py', 'class EnsembleVerifier'),
        ('verifiers/verifier_registry.py', 'class VerifierRegistry'),
        ('observability/reward_logger.py', 'class RewardLogger'),
        ('observability/action_trace_logger.py', 'class ActionTraceLogger'),
        ('observability/episode_metrics.py', 'class EpisodeMetricsTracker'),
        ('observability/audit_logger.py', 'class AuditLogger'),
        ('governance/safety_guardrails.py', 'class SafetyGuardrails'),
        ('governance/risk_thresholds.py', 'class RiskThresholds'),
        ('governance/compliance_rules.py', 'class ComplianceRules'),
        ('environments/clinical/treatment_pathway_optimization.py', 'class TreatmentPathwayOptimizationEnv'),
    ]
    
    all_found = True
    for file_path, class_pattern in checks:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            if class_pattern in content:
                print(f"✅ {file_path}: {class_pattern} found")
            else:
                print(f"❌ {file_path}: {class_pattern} NOT found")
                all_found = False
        else:
            print(f"❌ {file_path}: File not found")
            all_found = False
    
    return all_found

def check_method_signatures():
    """Check that required methods exist"""
    print("\n" + "=" * 80)
    print("METHOD SIGNATURE CHECK")
    print("=" * 80)
    
    checks = [
        ('verifiers/base_verifier.py', 'def evaluate'),
        ('verifiers/base_verifier.py', 'def breakdown'),
        ('verifiers/ensemble_verifier.py', 'def evaluate'),
        ('observability/reward_logger.py', 'def log_reward'),
        ('observability/action_trace_logger.py', 'def log_action'),
        ('governance/safety_guardrails.py', 'def validate_action'),
        ('environments/clinical/treatment_pathway_optimization.py', 'def step'),
        ('environments/clinical/treatment_pathway_optimization.py', 'verifier.evaluate'),
    ]
    
    all_found = True
    for file_path, method_pattern in checks:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            if method_pattern in content:
                print(f"✅ {file_path}: {method_pattern} found")
            else:
                print(f"❌ {file_path}: {method_pattern} NOT found")
                all_found = False
        else:
            print(f"❌ {file_path}: File not found")
            all_found = False
    
    return all_found

def main():
    """Run all structure tests"""
    print("\n🔍 VERIFIER REFACTORING - STRUCTURE TEST")
    print("=" * 80)
    print("(Testing code structure without requiring dependencies)\n")
    
    syntax_ok = test_file_structure()
    classes_ok = check_class_structure()
    methods_ok = check_method_signatures()
    
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    
    all_ok = syntax_ok and classes_ok and methods_ok
    
    if all_ok:
        print("✅ All structure checks passed!")
        print("\n📝 Next steps:")
        print("   1. Install dependencies: pip install -r requirements.txt")
        print("   2. Activate virtual environment: source venv/bin/activate")
        print("   3. Run full test: python3 test_verifier_refactor.py")
        return 0
    else:
        print("⚠️  Some structure checks failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())

