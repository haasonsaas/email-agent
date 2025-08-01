#!/usr/bin/env python3
"""Test script to verify Email Agent installation and basic functionality."""

import sys
import traceback
from pathlib import Path

def test_imports():
    """Test that all main modules can be imported."""
    print("Testing imports...")
    
    try:
        from email_agent import __version__
        print(f"✓ Email Agent version: {__version__}")
    except ImportError as e:
        print(f"✗ Failed to import email_agent: {e}")
        return False
    
    try:
        from email_agent.config import settings
        print("✓ Configuration module imported")
    except ImportError as e:
        print(f"✗ Failed to import config: {e}")
        return False
    
    try:
        from email_agent.models import Email, EmailCategory
        print("✓ Models imported")
    except ImportError as e:
        print(f"✗ Failed to import models: {e}")
        return False
    
    try:
        from email_agent.storage import DatabaseManager
        print("✓ Storage module imported")
    except ImportError as e:
        print(f"✗ Failed to import storage: {e}")
        return False
    
    try:
        from email_agent.agents import EmailAgentCrew
        print("✓ Agents module imported")
    except ImportError as e:
        print(f"✗ Failed to import agents: {e}")
        return False
    
    try:
        from email_agent.cli import app
        print("✓ CLI module imported")
    except ImportError as e:
        print(f"✗ Failed to import CLI: {e}")
        return False
    
    return True

def test_database():
    """Test database initialization."""
    print("\nTesting database...")
    
    try:
        from email_agent.storage import DatabaseManager
        
        # Use temporary database for testing
        db = DatabaseManager("sqlite:///:memory:")
        print("✓ Database manager created")
        
        # Test basic operations
        stats = db.get_email_stats()
        print(f"✓ Database stats: {stats}")
        
        return True
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        traceback.print_exc()
        return False

def test_rules_engine():
    """Test rules engine."""
    print("\nTesting rules engine...")
    
    try:
        from email_agent.rules import RulesEngine, BuiltinRules
        
        engine = RulesEngine()
        print("✓ Rules engine created")
        
        rules = BuiltinRules.get_all_rules()
        print(f"✓ Built-in rules: {len(rules)} rules")
        
        engine.load_rules(rules)
        print("✓ Rules loaded into engine")
        
        return True
    except Exception as e:
        print(f"✗ Rules engine test failed: {e}")
        traceback.print_exc()
        return False

def test_cli():
    """Test CLI functionality."""
    print("\nTesting CLI...")
    
    try:
        from email_agent.cli import app
        import typer.testing
        
        runner = typer.testing.CliRunner()
        result = runner.invoke(app, ["version"])
        
        if result.exit_code == 0:
            print("✓ CLI version command works")
            print(f"  Output: {result.stdout.strip()}")
        else:
            print(f"✗ CLI version failed: {result.stdout}")
            return False
        
        # Test help command
        result = runner.invoke(app, ["--help"])
        if result.exit_code == 0:
            print("✓ CLI help command works")
        else:
            print(f"✗ CLI help failed: {result.stdout}")
            return False
        
        return True
    except Exception as e:
        print(f"✗ CLI test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Email Agent Installation Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_database,
        test_rules_engine,
        test_cli
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Email Agent is ready to use.")
        print("\nNext steps:")
        print("1. Run: email-agent init setup")
        print("2. Configure your email connectors")
        print("3. Start managing your emails!")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())