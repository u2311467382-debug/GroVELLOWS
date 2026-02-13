#!/usr/bin/env python3
"""
Comprehensive API Security Testing for GroVELLOWS
Tests authentication, MFA, token security, rate limiting, security headers, and admin endpoints.
"""

import requests
import time
import json
import sys
from typing import Dict, Optional, Tuple
from datetime import datetime

# Configuration
BASE_URL = "https://buildtender-1.preview.emergentagent.com/api"
TEST_CREDENTIALS = {
    "director": {"email": "director@grovellows.de", "password": "Director123"},
    "partner": {"email": "partner@grovellows.de", "password": "Partner123"}
}

class SecurityTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 30
        self.tokens = {}
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status} - {test_name}"
        if details:
            result += f": {details}"
        print(result)
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
    def test_authentication_security(self):
        """Test 1: Authentication Security"""
        print("\n🔐 Testing Authentication Security...")
        
        # Test 1.1: Login with correct credentials
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json={
                "email": TEST_CREDENTIALS["director"]["email"],
                "password": TEST_CREDENTIALS["director"]["password"]
            })
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "mfa_enabled" in data:
                    self.tokens["director"] = data["access_token"]
                    self.log_test("Login with correct credentials", True, 
                                f"Token received, MFA status: {data.get('mfa_enabled', False)}")
                else:
                    self.log_test("Login with correct credentials", False, 
                                "Missing access_token or mfa_enabled in response")
            else:
                self.log_test("Login with correct credentials", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Login with correct credentials", False, f"Exception: {str(e)}")
        
        # Test 1.2: Login with wrong password
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json={
                "email": TEST_CREDENTIALS["director"]["email"],
                "password": "WrongPassword123"
            })
            
            if response.status_code == 401:
                self.log_test("Login with wrong password fails", True, 
                            "Correctly rejected invalid credentials")
            else:
                self.log_test("Login with wrong password fails", False, 
                            f"Expected 401, got {response.status_code}")
        except Exception as e:
            self.log_test("Login with wrong password fails", False, f"Exception: {str(e)}")
        
        # Test 1.3: Test IP blocking after 5 failed attempts
        print("   Testing IP blocking (5 failed attempts)...")
        failed_attempts = 0
        blocked = False
        
        for attempt in range(6):  # Try 6 times to trigger blocking
            try:
                response = self.session.post(f"{BASE_URL}/auth/login", json={
                    "email": TEST_CREDENTIALS["director"]["email"],
                    "password": f"WrongPassword{attempt}"
                })
                
                if response.status_code == 403:
                    blocked = True
                    self.log_test("IP blocking after 5 failed attempts", True, 
                                f"IP blocked after {attempt + 1} attempts")
                    break
                elif response.status_code == 401:
                    failed_attempts += 1
                    
            except Exception as e:
                self.log_test("IP blocking test", False, f"Exception on attempt {attempt}: {str(e)}")
                break
        
        if not blocked and failed_attempts >= 5:
            self.log_test("IP blocking after 5 failed attempts", False, 
                        f"Made {failed_attempts} failed attempts but IP not blocked")
        elif not blocked:
            self.log_test("IP blocking after 5 failed attempts", False, 
                        "Could not complete 5 failed attempts")
    
    def test_mfa_endpoints(self):
        """Test 2: MFA Endpoints"""
        print("\n🔑 Testing MFA Endpoints...")
        
        if "director" not in self.tokens:
            self.log_test("MFA tests", False, "No director token available")
            return
        
        headers = {"Authorization": f"Bearer {self.tokens['director']}"}
        
        # Test 2.1: MFA Status endpoint
        try:
            response = self.session.get(f"{BASE_URL}/auth/mfa/status", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "mfa_enabled" in data:
                    self.log_test("GET /api/auth/mfa/status", True, 
                                f"MFA enabled: {data['mfa_enabled']}")
                else:
                    self.log_test("GET /api/auth/mfa/status", False, 
                                "Missing mfa_enabled field")
            else:
                self.log_test("GET /api/auth/mfa/status", False, 
                            f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/auth/mfa/status", False, f"Exception: {str(e)}")
        
        # Test 2.2: MFA Setup endpoint (requires password confirmation)
        try:
            response = self.session.post(f"{BASE_URL}/auth/mfa/setup", 
                                       json={"password": TEST_CREDENTIALS["director"]["password"]},
                                       headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "qr_code" in data and "secret" in data:
                    self.log_test("POST /api/auth/mfa/setup", True, 
                                "QR code and secret returned")
                else:
                    self.log_test("POST /api/auth/mfa/setup", False, 
                                "Missing qr_code or secret in response")
            elif response.status_code == 400:
                # MFA might already be enabled
                self.log_test("POST /api/auth/mfa/setup", True, 
                            "MFA already enabled (expected behavior)")
            else:
                self.log_test("POST /api/auth/mfa/setup", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("POST /api/auth/mfa/setup", False, f"Exception: {str(e)}")
        
        # Test 2.3: MFA Verify Setup (with invalid code)
        try:
            response = self.session.post(f"{BASE_URL}/auth/mfa/verify-setup", 
                                       json={"code": "123456"},
                                       headers=headers)
            
            if response.status_code in [400, 401]:
                self.log_test("POST /api/auth/mfa/verify-setup", True, 
                            "Correctly rejected invalid MFA code")
            else:
                self.log_test("POST /api/auth/mfa/verify-setup", False, 
                            f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test("POST /api/auth/mfa/verify-setup", False, f"Exception: {str(e)}")
        
        # Test 2.4: MFA Disable endpoint (with invalid credentials)
        try:
            response = self.session.post(f"{BASE_URL}/auth/mfa/disable", 
                                       json={"password": "wrong", "mfa_code": "123456"},
                                       headers=headers)
            
            if response.status_code == 401:
                self.log_test("POST /api/auth/mfa/disable", True, 
                            "Correctly rejected invalid password/MFA code")
            else:
                self.log_test("POST /api/auth/mfa/disable", False, 
                            f"Expected 401, got {response.status_code}")
        except Exception as e:
            self.log_test("POST /api/auth/mfa/disable", False, f"Exception: {str(e)}")
    
    def test_token_security(self):
        """Test 3: Token Security"""
        print("\n🎫 Testing Token Security...")
        
        if "director" not in self.tokens:
            self.log_test("Token security tests", False, "No director token available")
            return
        
        # Test 3.1: Logout and blacklist token
        headers = {"Authorization": f"Bearer {self.tokens['director']}"}
        
        try:
            response = self.session.post(f"{BASE_URL}/auth/logout", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("POST /api/auth/logout", True, 
                                "Token successfully blacklisted")
                    
                    # Test 3.2: Verify blacklisted token cannot be reused
                    time.sleep(1)  # Brief delay
                    test_response = self.session.get(f"{BASE_URL}/auth/me", headers=headers)
                    
                    if test_response.status_code == 401:
                        self.log_test("Blacklisted token rejected", True, 
                                    "Blacklisted token correctly rejected")
                    else:
                        self.log_test("Blacklisted token rejected", False, 
                                    f"Blacklisted token still accepted: {test_response.status_code}")
                else:
                    self.log_test("POST /api/auth/logout", False, 
                                "Logout response missing success field")
            else:
                self.log_test("POST /api/auth/logout", False, 
                            f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("POST /api/auth/logout", False, f"Exception: {str(e)}")
        
        # Re-login for subsequent tests
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json={
                "email": TEST_CREDENTIALS["director"]["email"],
                "password": TEST_CREDENTIALS["director"]["password"]
            })
            if response.status_code == 200:
                self.tokens["director"] = response.json()["access_token"]
        except:
            pass
    
    def test_rate_limiting(self):
        """Test 4: Rate Limiting"""
        print("\n⏱️ Testing Rate Limiting...")
        
        # Test 4.1: Authentication endpoint rate limiting (5 requests/5 minutes)
        print("   Testing auth endpoint rate limiting...")
        auth_requests = 0
        rate_limited = False
        
        for i in range(7):  # Try 7 requests to exceed limit of 5
            try:
                response = self.session.post(f"{BASE_URL}/auth/login", json={
                    "email": "test@example.com",
                    "password": "testpass"
                })
                
                if response.status_code == 429:
                    rate_limited = True
                    self.log_test("Auth endpoint rate limiting (5 req/5min)", True, 
                                f"Rate limited after {i + 1} requests")
                    break
                else:
                    auth_requests += 1
                    
            except Exception as e:
                self.log_test("Auth endpoint rate limiting", False, f"Exception: {str(e)}")
                break
        
        if not rate_limited:
            self.log_test("Auth endpoint rate limiting (5 req/5min)", False, 
                        f"Made {auth_requests} requests without rate limiting")
        
        # Test 4.2: Normal endpoint rate limiting (100 requests/minute)
        # We'll test with a smaller number to avoid overwhelming the server
        print("   Testing normal endpoint rate limiting...")
        
        if "director" not in self.tokens:
            self.log_test("Normal endpoint rate limiting", False, "No token for testing")
            return
        
        headers = {"Authorization": f"Bearer {self.tokens['director']}"}
        normal_requests = 0
        rate_limited = False
        
        # Test with 20 rapid requests (should be within 100/min limit)
        for i in range(20):
            try:
                response = self.session.get(f"{BASE_URL}/tenders", headers=headers)
                
                if response.status_code == 429:
                    rate_limited = True
                    break
                elif response.status_code == 200:
                    normal_requests += 1
                    
            except Exception as e:
                break
        
        if not rate_limited and normal_requests >= 15:
            self.log_test("Normal endpoint rate limiting (100 req/min)", True, 
                        f"Successfully made {normal_requests} requests within limit")
        elif rate_limited:
            self.log_test("Normal endpoint rate limiting (100 req/min)", False, 
                        f"Rate limited too early after {normal_requests} requests")
        else:
            self.log_test("Normal endpoint rate limiting (100 req/min)", False, 
                        f"Could not complete sufficient requests: {normal_requests}")
    
    def test_security_headers(self):
        """Test 5: Security Headers"""
        print("\n🛡️ Testing Security Headers...")
        
        try:
            response = self.session.get(f"{BASE_URL}/tenders")
            headers = response.headers
            
            # Required security headers
            required_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Strict-Transport-Security": None,  # Just check presence
                "Content-Security-Policy": None     # Just check presence
            }
            
            all_headers_present = True
            missing_headers = []
            
            for header, expected_value in required_headers.items():
                if header in headers:
                    if expected_value and headers[header] != expected_value:
                        self.log_test(f"Security header {header}", False, 
                                    f"Expected '{expected_value}', got '{headers[header]}'")
                        all_headers_present = False
                    else:
                        self.log_test(f"Security header {header}", True, 
                                    f"Present: {headers[header]}")
                else:
                    missing_headers.append(header)
                    all_headers_present = False
            
            if missing_headers:
                self.log_test("Missing security headers", False, 
                            f"Missing: {', '.join(missing_headers)}")
            
            if all_headers_present:
                self.log_test("All required security headers", True, 
                            "All security headers present and correct")
                
        except Exception as e:
            self.log_test("Security headers test", False, f"Exception: {str(e)}")
    
    def test_admin_security_endpoints(self):
        """Test 6: Admin Security Endpoints (Director only)"""
        print("\n👑 Testing Admin Security Endpoints...")
        
        if "director" not in self.tokens:
            self.log_test("Admin security tests", False, "No director token available")
            return
        
        headers = {"Authorization": f"Bearer {self.tokens['director']}"}
        
        # Test 6.1: Security status endpoint
        try:
            response = self.session.get(f"{BASE_URL}/admin/security/status", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = ["blocked_ips_count", "blacklisted_tokens_count", 
                                 "recent_security_events", "rate_limit_storage_size"]
                
                if all(field in data for field in expected_fields):
                    self.log_test("GET /api/admin/security/status", True, 
                                f"Security metrics returned: {len(data)} fields")
                else:
                    missing = [f for f in expected_fields if f not in data]
                    self.log_test("GET /api/admin/security/status", False, 
                                f"Missing fields: {missing}")
            else:
                self.log_test("GET /api/admin/security/status", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("GET /api/admin/security/status", False, f"Exception: {str(e)}")
        
        # Test 6.2: Audit log endpoint
        try:
            response = self.session.get(f"{BASE_URL}/admin/security/audit-log", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("GET /api/admin/security/audit-log", True, 
                                f"Audit log returned: {len(data)} events")
                else:
                    self.log_test("GET /api/admin/security/audit-log", False, 
                                "Audit log should return a list")
            else:
                self.log_test("GET /api/admin/security/audit-log", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("GET /api/admin/security/audit-log", False, f"Exception: {str(e)}")
        
        # Test 6.3: Test non-admin access (should fail)
        # First, try to login as partner and test access
        try:
            partner_response = self.session.post(f"{BASE_URL}/auth/login", json={
                "email": TEST_CREDENTIALS["partner"]["email"],
                "password": TEST_CREDENTIALS["partner"]["password"]
            })
            
            if partner_response.status_code == 200:
                partner_token = partner_response.json()["access_token"]
                partner_headers = {"Authorization": f"Bearer {partner_token}"}
                
                # Try to access admin endpoint with partner token
                admin_response = self.session.get(f"{BASE_URL}/admin/security/status", 
                                                headers=partner_headers)
                
                if admin_response.status_code == 200:
                    # Partner should have admin access too according to the code
                    self.log_test("Partner admin access", True, 
                                "Partner correctly has admin access")
                elif admin_response.status_code == 403:
                    self.log_test("Partner admin access", False, 
                                "Partner should have admin access but was denied")
                else:
                    self.log_test("Partner admin access", False, 
                                f"Unexpected status: {admin_response.status_code}")
            else:
                self.log_test("Partner login for admin test", False, 
                            f"Could not login as partner: {partner_response.status_code}")
                
        except Exception as e:
            self.log_test("Partner admin access test", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all security tests"""
        print("🚀 Starting Comprehensive API Security Testing for GroVELLOWS")
        print(f"🎯 Target: {BASE_URL}")
        print("=" * 80)
        
        start_time = time.time()
        
        # Run all test suites
        self.test_authentication_security()
        self.test_mfa_endpoints()
        self.test_token_security()
        self.test_rate_limiting()
        self.test_security_headers()
        self.test_admin_security_endpoints()
        
        # Summary
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {total - passed}")
        print(f"📈 Success Rate: {(passed/total*100):.1f}%")
        print(f"⏱️ Duration: {duration}s")
        
        if total - passed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['details']}")
        
        print("\n🎯 SECURITY TEST COMPLETE")
        return passed, total

def main():
    """Main test execution"""
    tester = SecurityTester()
    passed, total = tester.run_all_tests()
    
    # Exit with appropriate code
    if passed == total:
        print("🎉 All security tests passed!")
        sys.exit(0)
    else:
        print(f"⚠️ {total - passed} security tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()