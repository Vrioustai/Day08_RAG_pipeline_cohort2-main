#!/usr/bin/env python3
"""
Railway Deployment Pre-Check Script
Validates project readiness before deploying to Railway
"""

import os
import sys
from pathlib import Path

def check_file_exists(filename, description):
    """Check if file exists"""
    if Path(filename).exists():
        print(f"✅ {description}: {filename}")
        return True
    else:
        print(f"❌ {description}: {filename} NOT FOUND")
        return False

def check_env_vars():
    """Check if critical env vars are set"""
    required_vars = [
        'OPENAI_API_KEY',
        'JINA_API_KEY',
        'PAGEINDEX_API_KEY',
    ]
    
    all_set = True
    for var in required_vars:
        if var in os.environ:
            value = os.environ[var]
            masked = value[:10] + '...' if len(value) > 10 else value
            print(f"✅ {var}: {masked}")
        else:
            print(f"❌ {var}: NOT SET")
            all_set = False
    
    return all_set

def check_requirements():
    """Check if critical packages are in requirements.txt"""
    if not Path('requirements.txt').exists():
        print("❌ requirements.txt NOT FOUND")
        return False
    
    with open('requirements.txt', 'r') as f:
        content = f.read().lower()
    
    required_packages = ['streamlit', 'python-dotenv', 'openai']
    all_found = True
    
    for pkg in required_packages:
        if pkg in content:
            print(f"✅ Package {pkg} found in requirements.txt")
        else:
            print(f"❌ Package {pkg} NOT in requirements.txt")
            all_found = False
    
    return all_found

def check_procfile():
    """Check Procfile format"""
    if not Path('Procfile').exists():
        print("❌ Procfile NOT FOUND")
        return False
    
    with open('Procfile', 'r') as f:
        content = f.read().strip()
    
    if 'streamlit run' in content:
        print(f"✅ Procfile exists with Streamlit command")
        return True
    else:
        print(f"❌ Procfile format incorrect")
        return False

def check_env_in_gitignore():
    """Check if .env is in .gitignore"""
    if not Path('.gitignore').exists():
        print("⚠️  .gitignore NOT FOUND (create one!)")
        return False
    
    with open('.gitignore', 'r') as f:
        content = f.read()
    
    if '.env' in content:
        print(f"✅ .env is in .gitignore")
        return True
    else:
        print(f"❌ .env is NOT in .gitignore - SECURITY RISK!")
        return False

def main():
    print("🚂 Railway Deployment Pre-Check")
    print("=" * 50)
    
    checks = [
        ("Files", [
            (lambda: check_file_exists('app.py', 'Main app file'), "app.py exists"),
            (lambda: check_file_exists('requirements.txt', 'Requirements'), "requirements.txt exists"),
            (lambda: check_file_exists('Procfile', 'Procfile'), "Procfile exists"),
            (lambda: check_procfile(), "Procfile format"),
            (lambda: check_env_in_gitignore(), ".env in .gitignore"),
        ]),
        ("Requirements", [
            (lambda: check_requirements(), "Required packages"),
        ]),
        ("Environment", [
            (lambda: check_env_vars(), "Environment variables"),
        ]),
    ]
    
    results = {}
    for section, section_checks in checks:
        print(f"\n📋 {section}")
        print("-" * 50)
        results[section] = all(check[0]() for check in section_checks)
    
    print("\n" + "=" * 50)
    if all(results.values()):
        print("✅ All checks passed! Ready for Railway deployment.")
        return 0
    else:
        print("❌ Some checks failed. Please fix before deploying.")
        print("\nNext steps:")
        print("1. Fix any ❌ items above")
        print("2. Run: git add . && git commit -m 'Fix deployment issues'")
        print("3. Run: git push origin main")
        print("4. Deploy on Railway dashboard")
        return 1

if __name__ == '__main__':
    sys.exit(main())
