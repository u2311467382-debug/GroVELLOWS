#!/usr/bin/env python3
"""
GroVELLOWS Backend API Testing Suite
Tests all backend endpoints including new features:
- Application Tracking
- Building Typology Filtering  
- LinkedIn Integration
- Portal Management
- Seed Data Verification
"""

import requests
import json
import sys
from datetime import datetime
import os

# Get backend URL from frontend .env
BACKEND_URL = "https://grovellows.preview.emergentagent.com/api"

# Test credentials
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "test123"

class GroVELLOWSAPITester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.auth_token = None
        self.test_user_id = None
        self.test_tender_id = None
        self.results = []
        
    def log_result(self, test_name, success, message, details=None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        print(f"{status}: {test_name} - {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def make_request(self, method, endpoint, data=None, headers=None):
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        default_headers = {"Content-Type": "application/json"}
        
        if self.auth_token:
            default_headers["Authorization"] = f"Bearer {self.auth_token}"
            
        if headers:
            default_headers.update(headers)
            
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=default_headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=default_headers, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, headers=default_headers, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=default_headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return response
        except requests.exceptions.RequestException as e:
            return None, str(e)
    
    def test_user_registration_and_login(self):
        """Test user registration and login flow"""
        print("\n=== Testing Authentication ===")
        
        # Test registration
        register_data = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "name": "Test User",
            "role": "Project Manager",
            "linkedin_url": "https://linkedin.com/in/testuser"
        }
        
        response = self.make_request("POST", "/auth/register", register_data)
        if response and response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            self.test_user_id = data.get("user", {}).get("id")
            self.log_result("User Registration", True, "User registered successfully")
        elif response and response.status_code == 400:
            # User might already exist, try login
            self.log_result("User Registration", True, "User already exists, proceeding to login")
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("User Registration", False, f"Registration failed: {error_msg}")
        
        # Test login
        login_data = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        
        response = self.make_request("POST", "/auth/login", login_data)
        if response and response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            self.test_user_id = data.get("user", {}).get("id")
            self.log_result("User Login", True, "Login successful", {"user_id": self.test_user_id})
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("User Login", False, f"Login failed: {error_msg}")
            return False
            
        return True
    
    def test_seed_data(self):
        """Test seed data endpoint"""
        print("\n=== Testing Seed Data ===")
        
        response = self.make_request("POST", "/seed-data")
        if response and response.status_code == 200:
            self.log_result("Seed Data", True, "Sample data seeded successfully")
            return True
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Seed Data", False, f"Seed data failed: {error_msg}")
            return False
    
    def test_get_tenders(self):
        """Test getting tenders and store a tender ID for further tests"""
        print("\n=== Testing Tender Retrieval ===")
        
        response = self.make_request("GET", "/tenders")
        if response and response.status_code == 200:
            tenders = response.json()
            if tenders:
                self.test_tender_id = tenders[0]["id"]
                self.log_result("Get Tenders", True, f"Retrieved {len(tenders)} tenders", {"tender_count": len(tenders), "first_tender_id": self.test_tender_id})
                return True
            else:
                self.log_result("Get Tenders", False, "No tenders found in database")
                return False
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Get Tenders", False, f"Failed to get tenders: {error_msg}")
            return False
    
    def test_building_typology_filtering(self):
        """Test building typology filtering"""
        print("\n=== Testing Building Typology Filtering ===")
        
        # Test Healthcare filter
        response = self.make_request("GET", "/tenders?building_typology=Healthcare")
        if response and response.status_code == 200:
            healthcare_tenders = response.json()
            self.log_result("Healthcare Filter", True, f"Found {len(healthcare_tenders)} healthcare tenders")
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Healthcare Filter", False, f"Healthcare filter failed: {error_msg}")
        
        # Test Data Center filter
        response = self.make_request("GET", "/tenders?building_typology=Data%20Center")
        if response and response.status_code == 200:
            datacenter_tenders = response.json()
            self.log_result("Data Center Filter", True, f"Found {len(datacenter_tenders)} data center tenders")
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Data Center Filter", False, f"Data center filter failed: {error_msg}")
    
    def test_application_tracking(self):
        """Test application tracking endpoints"""
        print("\n=== Testing Application Tracking ===")
        
        if not self.test_tender_id:
            self.log_result("Application Tracking", False, "No tender ID available for testing")
            return
        
        # Test apply to tender
        response = self.make_request("POST", f"/tenders/{self.test_tender_id}/apply")
        if response and response.status_code == 200:
            self.log_result("Apply to Tender", True, "Successfully applied to tender")
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Apply to Tender", False, f"Apply failed: {error_msg}")
        
        # Test update application status
        response = self.make_request("PUT", f"/tenders/{self.test_tender_id}/application-status?status=Won")
        if response and response.status_code == 200:
            self.log_result("Update Application Status", True, "Successfully updated status to Won")
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Update Application Status", False, f"Status update failed: {error_msg}")
        
        # Test get my applications
        response = self.make_request("GET", "/my-applications")
        if response and response.status_code == 200:
            applications = response.json()
            self.log_result("Get My Applications", True, f"Retrieved {len(applications)} applications")
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Get My Applications", False, f"Get applications failed: {error_msg}")
        
        # Test unapply from tender
        response = self.make_request("DELETE", f"/tenders/{self.test_tender_id}/apply")
        if response and response.status_code == 200:
            self.log_result("Unapply from Tender", True, "Successfully removed application")
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Unapply from Tender", False, f"Unapply failed: {error_msg}")
    
    def test_linkedin_integration(self):
        """Test LinkedIn integration endpoints"""
        print("\n=== Testing LinkedIn Integration ===")
        
        if not self.test_tender_id:
            self.log_result("LinkedIn Integration", False, "No tender ID available for testing")
            return
        
        # Test add LinkedIn connection
        linkedin_data = {
            "name": "Test User",
            "profile_url": "https://linkedin.com/in/test",
            "role": "Project Manager",
            "company": "Test Company",
            "notes": "Met at construction conference"
        }
        
        response = self.make_request("POST", f"/tenders/{self.test_tender_id}/linkedin", linkedin_data)
        if response and response.status_code == 200:
            self.log_result("Add LinkedIn Connection", True, "Successfully added LinkedIn connection")
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Add LinkedIn Connection", False, f"Add LinkedIn connection failed: {error_msg}")
        
        # Test remove LinkedIn connection (index 0)
        response = self.make_request("DELETE", f"/tenders/{self.test_tender_id}/linkedin/0")
        if response and response.status_code == 200:
            self.log_result("Remove LinkedIn Connection", True, "Successfully removed LinkedIn connection")
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Remove LinkedIn Connection", False, f"Remove LinkedIn connection failed: {error_msg}")
    
    def test_portal_management(self):
        """Test portal management endpoints"""
        print("\n=== Testing Portal Management ===")
        
        # Test get public portals
        response = self.make_request("GET", "/portals/public")
        if response and response.status_code == 200:
            portals = response.json()
            hospital_portals = [p for p in portals if p.get("type") == "hospital"]
            self.log_result("Get Public Portals", True, f"Retrieved {len(portals)} portals, {len(hospital_portals)} hospital portals")
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Get Public Portals", False, f"Get portals failed: {error_msg}")
    
    def test_favorites_system(self):
        """Test favorites system"""
        print("\n=== Testing Favorites System ===")
        
        if not self.test_tender_id:
            self.log_result("Favorites System", False, "No tender ID available for testing")
            return
        
        # Test add to favorites
        response = self.make_request("POST", f"/favorites/{self.test_tender_id}")
        if response and response.status_code == 200:
            self.log_result("Add to Favorites", True, "Successfully added to favorites")
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Add to Favorites", False, f"Add to favorites failed: {error_msg}")
        
        # Test get favorites
        response = self.make_request("GET", "/favorites")
        if response and response.status_code == 200:
            favorites = response.json()
            self.log_result("Get Favorites", True, f"Retrieved {len(favorites)} favorites")
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Get Favorites", False, f"Get favorites failed: {error_msg}")
        
        # Test remove from favorites
        response = self.make_request("DELETE", f"/favorites/{self.test_tender_id}")
        if response and response.status_code == 200:
            self.log_result("Remove from Favorites", True, "Successfully removed from favorites")
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Remove from Favorites", False, f"Remove from favorites failed: {error_msg}")
    
    def test_sharing_system(self):
        """Test sharing system"""
        print("\n=== Testing Sharing System ===")
        
        if not self.test_tender_id:
            self.log_result("Sharing System", False, "No tender ID available for testing")
            return
        
        # Test share tender
        share_data = {
            "tender_id": self.test_tender_id,
            "shared_with": [self.test_user_id],
            "message": "Check out this interesting tender"
        }
        
        response = self.make_request("POST", "/share", share_data)
        if response and response.status_code == 200:
            self.log_result("Share Tender", True, "Successfully shared tender")
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Share Tender", False, f"Share tender failed: {error_msg}")
        
        # Test get shares
        response = self.make_request("GET", "/shares")
        if response and response.status_code == 200:
            shares = response.json()
            self.log_result("Get Shares", True, f"Retrieved {len(shares)} shares")
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Get Shares", False, f"Get shares failed: {error_msg}")
    
    def test_notification_preferences(self):
        """Test notification preferences"""
        print("\n=== Testing Notification Preferences ===")
        
        # Test update preferences
        preferences_data = {
            "new_tenders": True,
            "status_changes": False,
            "ipa_tenders": True,
            "project_management": True,
            "daily_digest": False
        }
        
        response = self.make_request("PUT", "/auth/preferences", preferences_data)
        if response and response.status_code == 200:
            self.log_result("Update Notification Preferences", True, "Successfully updated preferences")
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Update Notification Preferences", False, f"Update preferences failed: {error_msg}")
        
        # Test get current user (to verify preferences)
        response = self.make_request("GET", "/auth/me")
        if response and response.status_code == 200:
            user_data = response.json()
            prefs = user_data.get("notification_preferences", {})
            self.log_result("Get User Profile", True, "Successfully retrieved user profile", {"preferences": prefs})
        else:
            error_msg = response.text if response else "Connection failed"
            self.log_result("Get User Profile", False, f"Get user profile failed: {error_msg}")
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting GroVELLOWS Backend API Tests")
        print(f"Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Authentication is required for all other tests
        if not self.test_user_registration_and_login():
            print("❌ Authentication failed - cannot proceed with other tests")
            return False
        
        # Seed data first
        self.test_seed_data()
        
        # Get tenders to have test data
        self.test_get_tenders()
        
        # Test all features
        self.test_building_typology_filtering()
        self.test_application_tracking()
        self.test_linkedin_integration()
        self.test_portal_management()
        self.test_favorites_system()
        self.test_sharing_system()
        self.test_notification_preferences()
        
        # Print summary
        self.print_summary()
        
        return True
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = len([r for r in self.results if "✅" in r["status"]])
        failed = len([r for r in self.results if "❌" in r["status"]])
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/total*100):.1f}%" if total > 0 else "0%")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.results:
                if "❌" in result["status"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\n✅ PASSED TESTS:")
        for result in self.results:
            if "✅" in result["status"]:
                print(f"  - {result['test']}")

if __name__ == "__main__":
    tester = GroVELLOWSAPITester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)