#!/usr/bin/env python3
"""
Focused Security Test for GroVELLOWS - Addressing specific issues found
"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "https://buildtender-1.preview.emergentagent.com/api"
DIRECTOR_CREDENTIALS = {"email": "director@grovellows.de", "password": "Director123"}

def test_authentication_and_mfa():
    """Test authentication and MFA functionality"""
    print("🔐 Testing Authentication & MFA...")
    
    session = requests.Session()
    session.timeout = 30
    
    # Test login
    try:
        response = session.post(f"{BASE_URL}/auth/login", json=DIRECTOR_CREDENTIALS)
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            mfa_enabled = data.get("mfa_enabled", False)
            print(f"✅ Login successful - MFA enabled: {mfa_enabled}")
            
            if token:
                headers = {"Authorization": f"Bearer {token}"}
                
                # Test MFA status
                mfa_response = session.get(f"{BASE_URL}/auth/mfa/status", headers=headers)
                if mfa_response.status_code == 200:
                    print("✅ MFA status endpoint working")
                else:
                    print(f"❌ MFA status failed: {mfa_response.status_code}")
                
                # Test MFA setup
                setup_response = session.post(f"{BASE_URL}/auth/mfa/setup", 
                                            json={"password": DIRECTOR_CREDENTIALS["password"]},
                                            headers=headers)
                if setup_response.status_code in [200, 400]:  # 400 if already enabled
                    print("✅ MFA setup endpoint working")
                else:
                    print(f"❌ MFA setup failed: {setup_response.status_code}")
                
                # Test logout and token blacklisting
                logout_response = session.post(f"{BASE_URL}/auth/logout", headers=headers)
                if logout_response.status_code == 200:
                    print("✅ Logout successful")
                    
                    # Test blacklisted token
                    test_response = session.get(f"{BASE_URL}/auth/me", headers=headers)
                    if test_response.status_code == 401:
                        print("✅ Token blacklisting working")
                    else:
                        print(f"❌ Token still valid after logout: {test_response.status_code}")
                else:
                    print(f"❌ Logout failed: {logout_response.status_code}")
            else:
                print("❌ No token received")
        else:
            print(f"❌ Login failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Authentication test error: {e}")

def test_rate_limiting():
    """Test rate limiting on auth endpoints"""
    print("\n⏱️ Testing Rate Limiting...")
    
    session = requests.Session()
    session.timeout = 10
    
    # Test auth endpoint rate limiting
    attempts = 0
    rate_limited = False
    
    for i in range(3):  # Try fewer attempts to avoid overwhelming
        try:
            response = session.post(f"{BASE_URL}/auth/login", json={
                "email": "nonexistent@test.com",
                "password": "wrongpass"
            })
            attempts += 1
            
            if response.status_code == 429:
                rate_limited = True
                print(f"✅ Rate limiting triggered after {attempts} attempts")
                break
            elif response.status_code == 401:
                print(f"   Attempt {i+1}: 401 (expected)")
            else:
                print(f"   Attempt {i+1}: {response.status_code}")
                
        except Exception as e:
            print(f"   Attempt {i+1} error: {e}")
            break
    
    if not rate_limited:
        print(f"⚠️ Rate limiting not triggered in {attempts} attempts (may need more attempts)")

def test_security_headers():
    """Test security headers"""
    print("\n🛡️ Testing Security Headers...")
    
    try:
        response = requests.get(f"{BASE_URL}/tenders", timeout=10)
        headers = response.headers
        
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Strict-Transport-Security": True,  # Just check presence
            "Content-Security-Policy": True,
            "X-XSS-Protection": True,
            "Referrer-Policy": True
        }
        
        for header, expected in security_headers.items():
            if header in headers:
                if expected == True:
                    print(f"✅ {header}: Present")
                elif headers[header] == expected:
                    print(f"✅ {header}: {headers[header]}")
                else:
                    print(f"⚠️ {header}: Expected '{expected}', got '{headers[header]}'")
            else:
                print(f"❌ {header}: Missing")
                
    except Exception as e:
        print(f"❌ Security headers test error: {e}")

def test_admin_endpoints():
    """Test admin security endpoints with fresh login"""
    print("\n👑 Testing Admin Security Endpoints...")
    
    session = requests.Session()
    session.timeout = 30
    
    try:
        # Fresh login
        login_response = session.post(f"{BASE_URL}/auth/login", json=DIRECTOR_CREDENTIALS)
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test security status
            status_response = session.get(f"{BASE_URL}/admin/security/status", headers=headers)
            if status_response.status_code == 200:
                data = status_response.json()
                print(f"✅ Security status endpoint working - {len(data)} metrics returned")
            else:
                print(f"❌ Security status failed: {status_response.status_code} - {status_response.text}")
            
            # Test audit log
            audit_response = session.get(f"{BASE_URL}/admin/security/audit-log", headers=headers)
            if audit_response.status_code == 200:
                data = audit_response.json()
                print(f"✅ Audit log endpoint working - {len(data)} events returned")
            else:
                print(f"❌ Audit log failed: {audit_response.status_code} - {audit_response.text}")
        else:
            print(f"❌ Could not login for admin test: {login_response.status_code}")
            
    except Exception as e:
        print(f"❌ Admin endpoints test error: {e}")

def test_ip_blocking_simulation():
    """Simulate IP blocking test with fewer attempts"""
    print("\n🚫 Testing IP Blocking (Simulation)...")
    
    session = requests.Session()
    session.timeout = 10
    
    failed_attempts = 0
    blocked = False
    
    # Try 3 failed attempts (less aggressive)
    for i in range(3):
        try:
            response = session.post(f"{BASE_URL}/auth/login", json={
                "email": DIRECTOR_CREDENTIALS["email"],
                "password": f"wrong_password_{i}"
            })
            
            if response.status_code == 403:
                blocked = True
                print(f"✅ IP blocking triggered after {i+1} attempts")
                break
            elif response.status_code == 401:
                failed_attempts += 1
                print(f"   Failed attempt {i+1}: 401")
            else:
                print(f"   Attempt {i+1}: {response.status_code}")
                
        except Exception as e:
            print(f"   Attempt {i+1} error: {e}")
            break
    
    if not blocked:
        print(f"⚠️ IP not blocked after {failed_attempts} attempts (may need 5 total attempts)")

def main():
    """Run focused security tests"""
    print("🔒 GroVELLOWS Security Test - Focused Analysis")
    print("=" * 60)
    
    start_time = time.time()
    
    test_authentication_and_mfa()
    test_rate_limiting()
    test_security_headers()
    test_admin_endpoints()
    test_ip_blocking_simulation()
    
    duration = round(time.time() - start_time, 2)
    print(f"\n⏱️ Test completed in {duration}s")
    print("=" * 60)

if __name__ == "__main__":
    main()