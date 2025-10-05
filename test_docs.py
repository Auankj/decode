#!/usr/bin/env python3
"""
Test script to verify documentation endpoints are working properly.
"""
import requests
import time
import sys

def test_endpoint(url, name):
    """Test an endpoint and return status."""
    try:
        response = requests.get(url, timeout=10)
        content_length = len(response.text)
        
        if response.status_code == 200:
            if content_length > 100:  # Reasonable content size
                print(f"✅ {name}: Working (Status: {response.status_code}, Size: {content_length} chars)")
                return True
            else:
                print(f"⚠️  {name}: Empty or minimal content (Status: {response.status_code}, Size: {content_length} chars)")
                return False
        else:
            print(f"❌ {name}: Failed (Status: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ {name}: Error - {e}")
        return False

def main():
    """Run all documentation tests."""
    print("🧪 Testing Cookie Licking Detector Documentation Endpoints")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # Test endpoints
    tests = [
        (f"{base_url}/", "API Root"),
        (f"{base_url}/openapi.json", "OpenAPI Specification"),
        (f"{base_url}/docs", "Swagger UI Documentation"),
        (f"{base_url}/redoc", "ReDoc Documentation"),
        (f"{base_url}/health", "Health Check"),
        (f"{base_url}/metrics", "Prometheus Metrics")
    ]
    
    results = []
    
    for url, name in tests:
        result = test_endpoint(url, name)
        results.append((name, result))
        time.sleep(0.5)  # Brief pause between requests
    
    print("\n📊 Summary:")
    print("-" * 30)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} endpoints working")
    
    if passed == total:
        print("🎉 All documentation endpoints are working perfectly!")
        return 0
    else:
        print("⚠️  Some endpoints need attention.")
        return 1

if __name__ == "__main__":
    sys.exit(main())