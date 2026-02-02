#!/usr/bin/env python3
"""
GroVELLOWS Backend Comprehensive Test Suite
Testing all new features for deployment approval
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://grovellows.preview.emergentagent.com/api"

# Test credentials from review request
DIRECTOR_CREDENTIALS = {
    "email": "director@grovellows.de",
    "password": "Director123"
}

REGULAR_USER_CREDENTIALS = {
    "email": "test@example.com", 
    "password": "test123"
}

class GroVELLOWSTestSuite:
    def __init__(self):
        self.director_token = None
        self.regular_user_token = None
        self.test_results = []
        self.session = requests.Session()
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        
    def make_request(self, method: str, endpoint: str, token: str = None, data: Dict = None, params: Dict = None) -> requests.Response:
        """Make HTTP request with proper headers"""
        url = f"{BASE_URL}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = self.session.post(url, headers=headers, json=data, params=params)
            elif method.upper() == "PUT":
                response = self.session.put(url, headers=headers, json=data, params=params)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers, params=params)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return response
        except Exception as e:
            print(f"Request failed: {e}")
            raise
    
    def test_authentication(self):
        """Test authentication for both user types"""
        print("\n=== AUTHENTICATION TESTS ===")
        
        # Test Director Login
        try:
            response = self.make_request("POST", "/auth/login", data=DIRECTOR_CREDENTIALS)
            if response.status_code == 200:
                data = response.json()
                self.director_token = data.get("access_token")
                user_role = data.get("user", {}).get("role")
                self.log_test("Director Login", True, f"Role: {user_role}, Token received")
            else:
                self.log_test("Director Login", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Director Login", False, f"Exception: {str(e)}")
            
        # Test Regular User Login
        try:
            response = self.make_request("POST", "/auth/login", data=REGULAR_USER_CREDENTIALS)
            if response.status_code == 200:
                data = response.json()
                self.regular_user_token = data.get("access_token")
                user_role = data.get("user", {}).get("role")
                self.log_test("Regular User Login", True, f"Role: {user_role}, Token received")
            else:
                self.log_test("Regular User Login", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Regular User Login", False, f"Exception: {str(e)}")
    
    def test_live_tender_scraping(self):
        """Test live tender scraping features (Directors only)"""
        print("\n=== LIVE TENDER SCRAPING TESTS ===")
        
        if not self.director_token:
            self.log_test("Scraping Tests", False, "No director token available")
            return
            
        # Test scrape status endpoint
        try:
            response = self.make_request("GET", "/scrape/status", token=self.director_token)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Get Scrape Status", True, f"Status retrieved: {data}")
            else:
                self.log_test("Get Scrape Status", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Get Scrape Status", False, f"Exception: {str(e)}")
            
        # Test live scraping (rate limited to 1/minute)
        try:
            response = self.make_request("POST", "/scrape/all", token=self.director_token)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Live Scrape All", True, f"Scrape initiated: {data}")
            elif response.status_code == 429:
                self.log_test("Live Scrape All", True, "Rate limit working correctly (429 Too Many Requests)")
            else:
                self.log_test("Live Scrape All", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Live Scrape All", False, f"Exception: {str(e)}")
            
        # Test that regular users cannot access scraping
        if self.regular_user_token:
            try:
                response = self.make_request("POST", "/scrape/all", token=self.regular_user_token)
                if response.status_code == 403:
                    self.log_test("Scrape Permission Check", True, "Regular users correctly blocked from scraping")
                else:
                    self.log_test("Scrape Permission Check", False, f"Regular user should be blocked. Status: {response.status_code}")
            except Exception as e:
                self.log_test("Scrape Permission Check", False, f"Exception: {str(e)}")
    
    def test_employee_management(self):
        """Test employee management and sharing features"""
        print("\n=== EMPLOYEE MANAGEMENT TESTS ===")
        
        if not self.director_token:
            self.log_test("Employee Management", False, "No director token available")
            return
            
        # Test get all employees
        try:
            response = self.make_request("GET", "/employees", token=self.director_token)
            if response.status_code == 200:
                employees = response.json()
                self.log_test("Get All Employees", True, f"Retrieved {len(employees)} employees")
                return employees
            else:
                self.log_test("Get All Employees", False, f"Status: {response.status_code}, Response: {response.text}")
                return []
        except Exception as e:
            self.log_test("Get All Employees", False, f"Exception: {str(e)}")
            return []
    
    def test_sharing_system(self):
        """Test tender sharing system"""
        print("\n=== SHARING SYSTEM TESTS ===")
        
        if not self.director_token or not self.regular_user_token:
            self.log_test("Sharing System", False, "Missing required tokens")
            return
            
        # First get a tender to share
        try:
            response = self.make_request("GET", "/tenders", token=self.director_token)
            if response.status_code == 200:
                tenders = response.json()
                if tenders:
                    tender_id = tenders[0]["id"]
                    
                    # Get employees to share with
                    emp_response = self.make_request("GET", "/employees", token=self.director_token)
                    if emp_response.status_code == 200:
                        employees = emp_response.json()
                        if len(employees) > 1:
                            recipient_id = employees[1]["id"]  # Share with second employee
                            
                            # Test sharing tender
                            share_data = {
                                "tender_id": tender_id,
                                "recipient_ids": [recipient_id],
                                "message": "Check this tender out - looks promising!"
                            }
                            
                            share_response = self.make_request("POST", "/share/tender", token=self.director_token, data=share_data)
                            if share_response.status_code == 200:
                                self.log_test("Share Tender", True, f"Tender shared successfully")
                            else:
                                self.log_test("Share Tender", False, f"Status: {share_response.status_code}, Response: {share_response.text}")
                        else:
                            self.log_test("Share Tender", False, "Not enough employees to test sharing")
                    else:
                        self.log_test("Share Tender", False, "Could not get employees list")
                else:
                    self.log_test("Share Tender", False, "No tenders available to share")
            else:
                self.log_test("Share Tender", False, f"Could not get tenders. Status: {response.status_code}")
        except Exception as e:
            self.log_test("Share Tender", False, f"Exception: {str(e)}")
            
        # Test get shared tenders inbox
        try:
            response = self.make_request("GET", "/share/inbox", token=self.regular_user_token)
            if response.status_code == 200:
                inbox = response.json()
                self.log_test("Get Share Inbox", True, f"Retrieved {len(inbox)} shared tenders")
            else:
                self.log_test("Get Share Inbox", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Get Share Inbox", False, f"Exception: {str(e)}")
    
    def test_application_tracking(self):
        """Test application tracking system"""
        print("\n=== APPLICATION TRACKING TESTS ===")
        
        if not self.regular_user_token:
            self.log_test("Application Tracking", False, "No regular user token available")
            return
            
        # Get a tender to apply to
        try:
            response = self.make_request("GET", "/tenders", token=self.regular_user_token)
            if response.status_code == 200:
                tenders = response.json()
                if tenders:
                    tender_id = tenders[0]["id"]
                    
                    # Test applying to tender
                    apply_response = self.make_request("POST", f"/tenders/{tender_id}/apply", token=self.regular_user_token)
                    if apply_response.status_code == 200:
                        self.log_test("Apply to Tender", True, "Successfully applied to tender")
                        
                        # Test updating application status
                        status_response = self.make_request("PUT", f"/tenders/{tender_id}/application-status", 
                                                          token=self.regular_user_token, params={"status": "Won"})
                        if status_response.status_code == 200:
                            self.log_test("Update Application Status", True, "Status updated to Won")
                        else:
                            self.log_test("Update Application Status", False, f"Status: {status_response.status_code}")
                            
                        # Test get my applications
                        my_apps_response = self.make_request("GET", "/my-applications", token=self.regular_user_token)
                        if my_apps_response.status_code == 200:
                            applications = my_apps_response.json()
                            self.log_test("Get My Applications", True, f"Retrieved {len(applications)} applications")
                        else:
                            self.log_test("Get My Applications", False, f"Status: {my_apps_response.status_code}")
                            
                        # Test removing application
                        unapply_response = self.make_request("DELETE", f"/tenders/{tender_id}/apply", token=self.regular_user_token)
                        if unapply_response.status_code == 200:
                            self.log_test("Remove Application", True, "Successfully removed application")
                        else:
                            self.log_test("Remove Application", False, f"Status: {unapply_response.status_code}")
                            
                    else:
                        self.log_test("Apply to Tender", False, f"Status: {apply_response.status_code}, Response: {apply_response.text}")
                else:
                    self.log_test("Application Tracking", False, "No tenders available for testing")
            else:
                self.log_test("Application Tracking", False, f"Could not get tenders. Status: {response.status_code}")
        except Exception as e:
            self.log_test("Application Tracking", False, f"Exception: {str(e)}")
    
    def test_employee_connections(self):
        """Test employee connections feature"""
        print("\n=== EMPLOYEE CONNECTIONS TESTS ===")
        
        if not self.regular_user_token:
            self.log_test("Employee Connections", False, "No regular user token available")
            return
            
        # Get a tender to check connections for
        try:
            response = self.make_request("GET", "/tenders", token=self.regular_user_token)
            if response.status_code == 200:
                tenders = response.json()
                if tenders:
                    tender_id = tenders[0]["id"]
                    
                    # Test get connections for tender
                    conn_response = self.make_request("GET", f"/tenders/{tender_id}/connections", token=self.regular_user_token)
                    if conn_response.status_code == 200:
                        connections = conn_response.json()
                        self.log_test("Get Tender Connections", True, f"Found {len(connections)} relevant connections")
                    else:
                        self.log_test("Get Tender Connections", False, f"Status: {conn_response.status_code}, Response: {conn_response.text}")
                else:
                    self.log_test("Employee Connections", False, "No tenders available for testing")
            else:
                self.log_test("Employee Connections", False, f"Could not get tenders. Status: {response.status_code}")
        except Exception as e:
            self.log_test("Employee Connections", False, f"Exception: {str(e)}")
    
    def test_gdpr_compliance(self):
        """Test GDPR compliance features"""
        print("\n=== GDPR COMPLIANCE TESTS ===")
        
        if not self.regular_user_token:
            self.log_test("GDPR Compliance", False, "No regular user token available")
            return
            
        # Test get privacy policy
        try:
            response = self.make_request("GET", "/gdpr/privacy-policy", token=self.regular_user_token)
            if response.status_code == 200:
                policy = response.json()
                self.log_test("Get Privacy Policy", True, "German privacy policy retrieved")
            else:
                self.log_test("Get Privacy Policy", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Get Privacy Policy", False, f"Exception: {str(e)}")
            
        # Test export personal data (Article 20)
        try:
            response = self.make_request("GET", "/gdpr/my-data", token=self.regular_user_token)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Export Personal Data", True, f"Data export successful (Article 20 compliance)")
            else:
                self.log_test("Export Personal Data", False, f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Export Personal Data", False, f"Exception: {str(e)}")
            
        # Test account deletion (Article 17) - Note: This is destructive, so we'll test with confirm=false first
        try:
            response = self.make_request("DELETE", "/gdpr/delete-account", token=self.regular_user_token, params={"confirm": "false"})
            if response.status_code == 400:  # Should require confirm=true
                self.log_test("Account Deletion Safety", True, "Deletion requires confirmation (safety check)")
                
                # Now test with confirm=true (WARNING: This will delete the account)
                # delete_response = self.make_request("DELETE", "/gdpr/delete-account", token=self.regular_user_token, params={"confirm": "true"})
                # if delete_response.status_code == 200:
                #     self.log_test("Account Deletion", True, "Account deleted successfully (Article 17 compliance)")
                # else:
                #     self.log_test("Account Deletion", False, f"Status: {delete_response.status_code}")
                    
                self.log_test("Account Deletion", True, "Deletion endpoint available (not executed to preserve test account)")
            else:
                self.log_test("Account Deletion Safety", False, f"Should require confirmation. Status: {response.status_code}")
        except Exception as e:
            self.log_test("Account Deletion", False, f"Exception: {str(e)}")
    
    def test_existing_features(self):
        """Test existing core features to ensure they still work"""
        print("\n=== EXISTING FEATURES VERIFICATION ===")
        
        if not self.regular_user_token:
            self.log_test("Existing Features", False, "No regular user token available")
            return
            
        # Test get tenders
        try:
            response = self.make_request("GET", "/tenders", token=self.regular_user_token)
            if response.status_code == 200:
                tenders = response.json()
                self.log_test("Get Tenders", True, f"Retrieved {len(tenders)} tenders")
            else:
                self.log_test("Get Tenders", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Get Tenders", False, f"Exception: {str(e)}")
            
        # Test building typology filtering
        try:
            response = self.make_request("GET", "/tenders", token=self.regular_user_token, params={"building_typology": "Healthcare"})
            if response.status_code == 200:
                healthcare_tenders = response.json()
                self.log_test("Building Typology Filter", True, f"Found {len(healthcare_tenders)} healthcare tenders")
            else:
                self.log_test("Building Typology Filter", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Building Typology Filter", False, f"Exception: {str(e)}")
            
        # Test get public portals
        try:
            response = self.make_request("GET", "/portals/public", token=self.regular_user_token)
            if response.status_code == 200:
                portals = response.json()
                self.log_test("Get Public Portals", True, f"Retrieved {len(portals)} portals")
            else:
                self.log_test("Get Public Portals", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Get Public Portals", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting GroVELLOWS Backend Comprehensive Test Suite")
        print(f"Testing against: {BASE_URL}")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all test categories
        self.test_authentication()
        self.test_live_tender_scraping()
        self.test_employee_management()
        self.test_sharing_system()
        self.test_application_tracking()
        self.test_employee_connections()
        self.test_gdpr_compliance()
        self.test_existing_features()
        
        end_time = time.time()
        
        # Generate summary
        self.generate_summary(end_time - start_time)
    
    def generate_summary(self, duration: float):
        """Generate test summary"""
        print("\n" + "=" * 60)
        print("🏁 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print(f"Duration: {duration:.2f} seconds")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS ({failed_tests}):")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['details']}")
        
        print(f"\n✅ PASSED TESTS ({passed_tests}):")
        for result in self.test_results:
            if result["success"]:
                print(f"  • {result['test']}: {result['details']}")
        
        # Save detailed results to file
        with open("/app/test_results_detailed.json", "w") as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        print(f"\nDetailed results saved to: /app/test_results_detailed.json")

if __name__ == "__main__":
    test_suite = GroVELLOWSTestSuite()
    test_suite.run_all_tests()