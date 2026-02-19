#!/usr/bin/env python3
"""
Quick server check and start script
"""

import sys
import os

# Check dependencies
print("Checking dependencies...")
missing = []
try:
    import fastapi
    print("✓ fastapi installed")
except ImportError:
    missing.append("fastapi")
    print("✗ fastapi missing")

try:
    import uvicorn
    print("✓ uvicorn installed")
except ImportError:
    missing.append("uvicorn")
    print("✗ uvicorn missing")

try:
    import gymnasium
    print("✓ gymnasium installed")
except ImportError:
    missing.append("gymnasium")
    print("✗ gymnasium missing")

if missing:
    print(f"\n❌ Missing dependencies: {', '.join(missing)}")
    print("Install with: pip install -r requirements.txt")
    sys.exit(1)

# Check imports
print("\nChecking imports...")
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from api.main import app
    print("✓ API imports successful")
except Exception as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Check environment registry
try:
    from portal.environment_registry import list_all_environments
    envs = list_all_environments()
    print(f"✓ Environment registry: {len(envs)} environments found")
except Exception as e:
    print(f"✗ Registry error: {e}")
    sys.exit(1)

print("\n✅ All checks passed! Server should start successfully.")
print("\nTo start the server, run:")
print("  python -m api.main")
print("\nOr use:")
print("  uvicorn api.main:app --reload --host 0.0.0.0 --port 8000")

