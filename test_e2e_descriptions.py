#!/usr/bin/env python3
"""
End-to-end test to verify all RL environment descriptions are unique and relevant
"""
import sys
import os
import re
sys.path.insert(0, '.')

from portal.environment_registry import list_all_environments

def extract_descriptions_from_js():
    """Extract environment descriptions from app.js"""
    js_path = 'api/static/app.js'
    if not os.path.exists(js_path):
        print(f"❌ JavaScript file not found: {js_path}")
        return {}
    
    with open(js_path, 'r') as f:
        js_content = f.read()
    
    # Find the getEnvironmentDescription function
    # Look for the descriptions object
    desc_pattern = r"'([A-Z][a-zA-Z]+)':\s*'([^']{30,})'"
    matches = re.findall(desc_pattern, js_content)
    
    descriptions = {}
    for name, desc in matches:
        # Only include if it looks like an environment name
        if any(c.isupper() for c in name[1:]):
            descriptions[name] = desc
    
    return descriptions

def test_e2e():
    """Run end-to-end test"""
    print("🧪 End-to-End Description Test")
    print("=" * 80)
    
    # Get all environments from registry
    envs = list_all_environments()
    print(f"\n📋 Found {len(envs)} environments in registry")
    
    # Get descriptions from JavaScript
    js_descriptions = extract_descriptions_from_js()
    print(f"📝 Found {len(js_descriptions)} descriptions in JavaScript")
    
    # Check coverage
    env_names = {env['name'] for env in envs}
    covered = env_names.intersection(set(js_descriptions.keys()))
    missing = env_names - set(js_descriptions.keys())
    
    print(f"\n✅ Coverage: {len(covered)}/{len(env_names)} environments have descriptions")
    if missing:
        print(f"⚠️  Missing descriptions for {len(missing)} environments:")
        for name in list(missing)[:10]:
            print(f"   - {name}")
        if len(missing) > 10:
            print(f"   ... and {len(missing) - 10} more")
    
    # Check uniqueness
    desc_to_envs = {}
    for env_name, desc in js_descriptions.items():
        if desc not in desc_to_envs:
            desc_to_envs[desc] = []
        desc_to_envs[desc].append(env_name)
    
    duplicates = {desc: envs for desc, envs in desc_to_envs.items() if len(envs) > 1}
    
    if duplicates:
        print(f"\n❌ Found {len(duplicates)} duplicate descriptions:")
        for desc, envs in list(duplicates.items())[:3]:
            print(f"   Description: {desc[:80]}...")
            print(f"   Used by: {', '.join(envs)}")
        return False
    else:
        print("\n✅ All descriptions are unique!")
    
    # Check description quality
    print("\n📊 Description Quality Check:")
    short = [name for name, desc in js_descriptions.items() if len(desc) < 50]
    if short:
        print(f"⚠️  {len(short)} descriptions are very short (< 50 chars)")
        for name in short[:5]:
            print(f"   - {name}: {js_descriptions[name]}")
    else:
        print("✅ All descriptions have adequate length (>= 50 chars)")
    
    # Check relevance (basic check - descriptions should contain relevant keywords)
    print("\n🔍 Relevance Check:")
    relevance_issues = []
    for env_name, desc in js_descriptions.items():
        # Check if description mentions key terms from environment name
        name_lower = env_name.lower()
        desc_lower = desc.lower()
        
        # Extract key words from environment name
        key_words = [word.lower() for word in re.findall(r'[A-Z][a-z]+', env_name)]
        
        # Check if at least one key word appears in description
        if key_words:
            found = any(word in desc_lower for word in key_words if len(word) > 3)
            if not found:
                relevance_issues.append(env_name)
    
    if relevance_issues:
        print(f"⚠️  {len(relevance_issues)} descriptions may lack relevance:")
        for name in relevance_issues[:5]:
            print(f"   - {name}")
    else:
        print("✅ All descriptions appear relevant to their environment names")
    
    # Check category alignment
    print("\n📂 Category Alignment Check:")
    categories = {}
    for env in envs:
        cat = env.get('category', 'unknown')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(env['name'])
    
    print(f"✅ Found {len(categories)} categories")
    for cat, envs_list in sorted(categories.items()):
        print(f"   {cat}: {len(envs_list)} environments")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 Test Summary:")
    print(f"   Total Environments: {len(envs)}")
    print(f"   Descriptions in JS: {len(js_descriptions)}")
    print(f"   Coverage: {len(covered)}/{len(env_names)} ({100*len(covered)/len(env_names):.1f}%)")
    print(f"   Unique Descriptions: {len(js_descriptions) - len(duplicates)}")
    print(f"   Categories: {len(categories)}")
    
    # Final verdict
    all_good = (
        len(duplicates) == 0 and
        len(missing) == 0 and
        len(short) == 0 and
        len(relevance_issues) == 0
    )
    
    if all_good:
        print("\n✅ All tests passed! Descriptions are unique, relevant, and complete.")
    else:
        print("\n⚠️  Some issues found. Please review the output above.")
    
    return all_good

if __name__ == '__main__':
    success = test_e2e()
    sys.exit(0 if success else 1)

