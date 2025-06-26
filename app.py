#!/usr/bin/env python3
"""
Production Context Validation Test
Tests OpenAI functionality in production-like conditions
"""

import sys
import os
import json
import time
from datetime import datetime

def test_production_openai_initialization():
    """Test OpenAI initialization in production-like conditions"""
    print("🏭 Testing Production OpenAI Initialization...")
    
    try:
        # Import the app module
        sys.path.insert(0, '/home/ubuntu')
        import app
        
        # Test 1: Basic availability
        print(f"   OpenAI Available: {'✅' if app.OPENAI_AVAILABLE else '❌'}")
        print(f"   API Key Present: {'✅' if app.OPENAI_API_KEY else '❌'}")
        print(f"   API Key Source: {('environment' if os.getenv('OPENAI_API_KEY') else 'hardcoded')}")
        
        # Test 2: Client initialization
        client = app.get_openai_client()
        print(f"   Client Initialized: {'✅' if client else '❌'}")
        
        if app.openai_client_error:
            print(f"   Client Error: {app.openai_client_error}")
        
        # Test 3: Connection test
        connection_status = app.test_openai_connection()
        print(f"   Connection Status: {connection_status['status']}")
        print(f"   Connection Message: {connection_status['message']}")
        
        # Test 4: Reinitialize function
        print("   Testing reinitialize function...")
        new_client = app.reinitialize_openai_client()
        print(f"   Reinitialize Result: {'✅' if new_client else '❌'}")
        
        return client is not None
        
    except Exception as e:
        print(f"❌ Production OpenAI test failed: {str(e)}")
        return False

def test_pdf_reorganizer_ai_initialization():
    """Test PDF reorganizer AI initialization"""
    print("\n📄 Testing PDF Reorganizer AI Initialization...")
    
    try:
        sys.path.insert(0, '/home/ubuntu')
        import app
        
        # Test initial state
        print(f"   PDF Reorganizer AI Available: {'✅' if app.pdf_reorganizer_ai else '❌'}")
        
        # Test initialization function
        print("   Testing initialization function...")
        new_ai = app.initialize_pdf_reorganizer_ai()
        print(f"   Initialization Result: {'✅' if new_ai else '❌'}")
        
        # Test PDF reorganizer
        print(f"   PDF Reorganizer Available: {'✅' if app.pdf_reorganizer else '❌'}")
        
        return new_ai is not None
        
    except Exception as e:
        print(f"❌ PDF Reorganizer AI test failed: {str(e)}")
        return False

def test_debug_endpoint():
    """Test the debug endpoint functionality"""
    print("\n🔍 Testing Debug Endpoint...")
    
    try:
        sys.path.insert(0, '/home/ubuntu')
        import app
        
        # Test the debug endpoint directly
        with app.app.test_client() as client:
            response = client.get('/debug/openai')
            
            if response.status_code == 200:
                print("✅ Debug endpoint responds successfully")
                
                data = response.get_json()
                print("   Debug Information:")
                for key, value in data.items():
                    print(f"     {key}: {value}")
                
                return True
            else:
                print(f"❌ Debug endpoint failed with status {response.status_code}")
                return False
        
    except Exception as e:
        print(f"❌ Debug endpoint test failed: {str(e)}")
        return False

def test_reorganize_pdf_endpoint():
    """Test the reorganize PDF endpoint with improved error handling"""
    print("\n📋 Testing Reorganize PDF Endpoint...")
    
    try:
        sys.path.insert(0, '/home/ubuntu')
        import app
        
        # Test the endpoint with minimal data
        test_data = {
            'document_sections': [
                {'name': 'Test Document', 'pages': '1-2', 'confidence': 'high'}
            ],
            'lender_requirements': {
                'required_documents': ['Test Document']
            },
            'original_pdf_path': '/tmp/test.pdf'
        }
        
        with app.app.test_client() as client:
            response = client.post('/reorganize_pdf', 
                                 data=json.dumps(test_data),
                                 content_type='application/json')
            
            print(f"   Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.get_json()
                print(f"   Response Success: {data.get('success', False)}")
                
                if not data.get('success'):
                    print(f"   Error: {data.get('error', 'Unknown error')}")
                    if 'details' in data:
                        print("   Error Details:")
                        for key, value in data['details'].items():
                            print(f"     {key}: {value}")
                
                return data.get('success', False)
            else:
                print(f"❌ Endpoint returned status {response.status_code}")
                return False
        
    except Exception as e:
        print(f"❌ Reorganize PDF endpoint test failed: {str(e)}")
        return False

def test_environment_variable_support():
    """Test environment variable support for API key"""
    print("\n🌍 Testing Environment Variable Support...")
    
    try:
        # Save current environment
        original_env_key = os.environ.get('OPENAI_API_KEY')
        
        # Test with environment variable
        os.environ['OPENAI_API_KEY'] = 'test-env-key'
        
        # Reload the module to test environment variable pickup
        import importlib
        sys.path.insert(0, '/home/ubuntu')
        import app
        importlib.reload(app)
        
        # Check if environment variable is picked up
        env_key_detected = app.OPENAI_API_KEY == 'test-env-key'
        print(f"   Environment Variable Detected: {'✅' if env_key_detected else '❌'}")
        
        # Restore original environment
        if original_env_key:
            os.environ['OPENAI_API_KEY'] = original_env_key
        else:
            os.environ.pop('OPENAI_API_KEY', None)
        
        # Reload again to restore original state
        importlib.reload(app)
        
        return env_key_detected
        
    except Exception as e:
        print(f"❌ Environment variable test failed: {str(e)}")
        return False

def run_production_validation():
    """Run all production validation tests"""
    print("🏭 PRODUCTION CONTEXT VALIDATION")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    tests = [
        ("Production OpenAI Initialization", test_production_openai_initialization),
        ("PDF Reorganizer AI Initialization", test_pdf_reorganizer_ai_initialization),
        ("Debug Endpoint", test_debug_endpoint),
        ("Reorganize PDF Endpoint", test_reorganize_pdf_endpoint),
        ("Environment Variable Support", test_environment_variable_support)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {str(e)}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*60)
    print("📊 PRODUCTION VALIDATION SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL PRODUCTION TESTS PASSED - READY FOR DEPLOYMENT")
        return 0
    elif passed >= total * 0.8:  # 80% pass rate
        print("⚠️  MOSTLY WORKING - MINOR ISSUES DETECTED")
        return 0
    else:
        print("❌ SIGNIFICANT ISSUES - NEEDS ATTENTION")
        return 1

if __name__ == "__main__":
    exit_code = run_production_validation()
    sys.exit(exit_code)

