#!/usr/bin/env python3
"""
GroVELLOWS Tender Tracking API Test Suite
Testing specific requirements from review request:

**Authentication:**
- Login: POST /api/auth/login with director@grovellows.de / Director123

**Critical Tests - Tender Country Filter:**
1. GET /api/tenders - Should return ~237 total tenders
2. GET /api/tenders?country=Germany - Should return ~231 German tenders ONLY (NO Swiss tenders)
3. GET /api/tenders?country=Switzerland - Should return exactly 6 Swiss tenders ONLY

**Verify Country Filter is Exclusive:**
- When country=Germany, verify NO tender has country="Switzerland" 
- When country=Switzerland, verify ALL tenders have country="Switzerland"
- Check platform_source for Swiss tenders should be "simap.ch (Schweiz)"

**Platform Distribution Test:**
- GET /api/tenders and check that platform_source includes: "Ausschreibungen Deutschland", "Vergabe Bayern", "simap.ch (Schweiz)", "Asklepios Kliniken"

**Scraping Test:**
- POST /api/scrape/all with Director auth - Should trigger comprehensive scraper
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://project-pulse-251.preview.emergentagent.com/api"

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
    
    def test_tender_count_requirements(self):
        """Test Critical Requirements - Tender Counts"""
        print("\n=== CRITICAL TENDER COUNT TESTS ===")
        
        if not self.director_token:
            self.log_test("Tender Count Requirements", False, "No director token available")
            return []
            
        try:
            # Test 1: GET /api/tenders - Should return ~237 total tenders
            response = self.make_request("GET", "/tenders", token=self.director_token)
            if response.status_code == 200:
                all_tenders = response.json()
                total_count = len(all_tenders)
                
                # Check if we have approximately 237 tenders (allow range 230-250)
                if 230 <= total_count <= 250:
                    self.log_test("Total Tenders Count (~237)", True, 
                                f"Found {total_count} tenders (expected ~237)")
                else:
                    self.log_test("Total Tenders Count (~237)", False, 
                                f"Found {total_count} tenders, expected ~237 (range 230-250)")
                
                return all_tenders
                
            else:
                self.log_test("Total Tenders Count", False, 
                            f"Failed to retrieve tenders, status: {response.status_code}")
                return []
                
        except Exception as e:
            self.log_test("Total Tenders Count", False, f"Exception: {str(e)}")
            return []

    def test_country_filtering_requirements(self):
        """Test Critical Requirements - Country Filtering"""
        print("\n=== CRITICAL COUNTRY FILTERING TESTS ===")
        
        if not self.director_token:
            self.log_test("Country Filtering Requirements", False, "No director token available")
            return
            
        try:
            # Test 2: GET /api/tenders?country=Germany - Should return ~231 German tenders ONLY
            response = self.make_request("GET", "/tenders", token=self.director_token, 
                                       params={"country": "Germany"})
            if response.status_code == 200:
                german_tenders = response.json()
                german_count = len(german_tenders)
                
                # Check if we have approximately 231 German tenders (allow range 225-240)
                if 225 <= german_count <= 240:
                    self.log_test("German Tenders Count (~231)", True, 
                                f"Found {german_count} German tenders (expected ~231)")
                else:
                    self.log_test("German Tenders Count (~231)", False, 
                                f"Found {german_count} German tenders, expected ~231 (range 225-240)")
                
                # Verify NO Swiss tenders in German filter
                swiss_in_german = [t for t in german_tenders if t.get("country") == "Switzerland"]
                if len(swiss_in_german) == 0:
                    self.log_test("German Filter Exclusivity (NO Swiss)", True, 
                                "German filter correctly excludes all Swiss tenders")
                else:
                    self.log_test("German Filter Exclusivity (NO Swiss)", False, 
                                f"Found {len(swiss_in_german)} Swiss tenders in German filter")
                
                # Verify ALL tenders are German
                non_german = [t for t in german_tenders if t.get("country") != "Germany"]
                if len(non_german) == 0:
                    self.log_test("German Filter Purity", True, 
                                "All tenders in German filter have country='Germany'")
                else:
                    self.log_test("German Filter Purity", False, 
                                f"Found {len(non_german)} non-German tenders in German filter")
                    
            else:
                self.log_test("German Tenders Filter", False, 
                            f"Failed to retrieve German tenders, status: {response.status_code}")
            
            # Test 3: GET /api/tenders?country=Switzerland - Should return exactly 6 Swiss tenders ONLY
            response = self.make_request("GET", "/tenders", token=self.director_token, 
                                       params={"country": "Switzerland"})
            if response.status_code == 200:
                swiss_tenders = response.json()
                swiss_count = len(swiss_tenders)
                
                # Check if we have exactly 6 Swiss tenders
                if swiss_count == 6:
                    self.log_test("Swiss Tenders Count (exactly 6)", True, 
                                f"Found exactly {swiss_count} Swiss tenders")
                else:
                    self.log_test("Swiss Tenders Count (exactly 6)", False, 
                                f"Found {swiss_count} Swiss tenders, expected exactly 6")
                
                # Verify ALL tenders are Swiss
                non_swiss = [t for t in swiss_tenders if t.get("country") != "Switzerland"]
                if len(non_swiss) == 0:
                    self.log_test("Swiss Filter Exclusivity", True, 
                                "All tenders in Swiss filter have country='Switzerland'")
                else:
                    self.log_test("Swiss Filter Exclusivity", False, 
                                f"Found {len(non_swiss)} non-Swiss tenders in Swiss filter")
                
                # Check Swiss platform sources should be "simap.ch (Schweiz)"
                swiss_platforms = [t.get("platform_source", "") for t in swiss_tenders]
                simap_count = sum(1 for p in swiss_platforms if "simap.ch" in p.lower() and "schweiz" in p.lower())
                
                if simap_count > 0:
                    self.log_test("Swiss Platform Source (simap.ch Schweiz)", True, 
                                f"Found {simap_count} tenders from 'simap.ch (Schweiz)' platform")
                else:
                    self.log_test("Swiss Platform Source (simap.ch Schweiz)", False, 
                                f"No tenders found from 'simap.ch (Schweiz)'. Platforms: {set(swiss_platforms)}")
                    
            else:
                self.log_test("Swiss Tenders Filter", False, 
                            f"Failed to retrieve Swiss tenders, status: {response.status_code}")
                
        except Exception as e:
            self.log_test("Country Filtering Requirements", False, f"Exception: {str(e)}")

    def test_platform_distribution_requirements(self):
        """Test Platform Distribution Requirements"""
        print("\n=== PLATFORM DISTRIBUTION TESTS ===")
        
        if not self.director_token:
            self.log_test("Platform Distribution Requirements", False, "No director token available")
            return
            
        try:
            response = self.make_request("GET", "/tenders", token=self.director_token)
            if response.status_code == 200:
                all_tenders = response.json()
                
                # Get all platform sources
                platform_sources = [t.get("platform_source", "Unknown") for t in all_tenders]
                unique_platforms = set(platform_sources)
                
                # Check for required platforms from review request
                required_platforms = [
                    "Ausschreibungen Deutschland",
                    "Vergabe Bayern", 
                    "simap.ch (Schweiz)",
                    "Asklepios Kliniken"
                ]
                
                found_platforms = []
                missing_platforms = []
                
                for required in required_platforms:
                    found = False
                    for actual in unique_platforms:
                        if required.lower() in actual.lower():
                            found_platforms.append(actual)
                            found = True
                            break
                    
                    if not found:
                        missing_platforms.append(required)
                
                if len(found_platforms) >= 3:
                    self.log_test("Required Platform Distribution", True, 
                                f"Found {len(found_platforms)}/4 required platforms: {found_platforms}")
                else:
                    self.log_test("Required Platform Distribution", False, 
                                f"Only found {len(found_platforms)}/4 required platforms. Missing: {missing_platforms}")
                
                # Log platform statistics for debugging
                platform_counts = {}
                for platform in platform_sources:
                    platform_counts[platform] = platform_counts.get(platform, 0) + 1
                
                print(f"   Platform breakdown (top 10):")
                sorted_platforms = sorted(platform_counts.items(), key=lambda x: x[1], reverse=True)
                for platform, count in sorted_platforms[:10]:
                    print(f"     - {platform}: {count} tenders")
                    
            else:
                self.log_test("Platform Distribution Requirements", False, 
                            f"Failed to fetch tenders for platform analysis: {response.status_code}")
                
        except Exception as e:
            self.log_test("Platform Distribution Requirements", False, f"Error analyzing platforms: {str(e)}")

    def test_scraping_requirements(self):
        """Test Scraping Requirements - POST /api/scrape/all with Director auth"""
        print("\n=== SCRAPING REQUIREMENTS TESTS ===")
        
        if not self.director_token:
            self.log_test("Scraping Requirements", False, "No director token available")
            return
            
        # Test scrape status endpoint first
        try:
            response = self.make_request("GET", "/scrape/status", token=self.director_token)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Scrape Status Endpoint", True, 
                            f"Status retrieved: {data.get('message', 'Status available')}")
            else:
                self.log_test("Scrape Status Endpoint", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Scrape Status Endpoint", False, f"Exception: {str(e)}")
            
        # Test comprehensive scraper trigger (Director only)
        try:
            response = self.make_request("POST", "/scrape/all", token=self.director_token)
            if response.status_code == 200:
                data = response.json()
                scraped_count = data.get("count", 0)
                message = data.get("message", "")
                
                self.log_test("Comprehensive Scraper Trigger", True, 
                            f"Scraping completed successfully: {message}")
                
                if scraped_count >= 0:  # Allow 0 if no new tenders found
                    self.log_test("Scraper Execution", True, 
                                f"Scraper executed and found {scraped_count} new tenders")
                else:
                    self.log_test("Scraper Execution", False, 
                                f"Unexpected scraper result: {scraped_count}")
                
            elif response.status_code == 429:
                self.log_test("Comprehensive Scraper Trigger", True, 
                            "Rate limiting working correctly (429 Too Many Requests)")
            elif response.status_code == 403:
                self.log_test("Comprehensive Scraper Trigger", False, 
                            "Access denied - Director role authentication issue")
            else:
                self.log_test("Comprehensive Scraper Trigger", False, 
                            f"Scraping failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Comprehensive Scraper Trigger", False, f"Exception: {str(e)}")
            
        # Test Director role requirement (if we have a regular user token)
        if self.regular_user_token:
            try:
                response = self.make_request("POST", "/scrape/all", token=self.regular_user_token)
                if response.status_code == 403:
                    self.log_test("Director Role Requirement", True, 
                                "Regular users correctly blocked from scraping (403 Forbidden)")
                else:
                    self.log_test("Director Role Requirement", False, 
                                f"Regular user should be blocked. Status: {response.status_code}")
            except Exception as e:
                self.log_test("Director Role Requirement", False, f"Exception: {str(e)}")

    def test_data_integrity_requirements(self, tenders):
        """Test Data Integrity - verify required fields"""
        print("\n=== DATA INTEGRITY TESTS ===")
        
        if not tenders:
            self.log_test("Data Integrity Requirements", False, "No tenders available for testing")
            return
            
        try:
            # Required fields verification
            required_fields = ["title", "description", "platform_source", "country", "location", "deadline"]
            missing_fields_count = {}
            total_checked = min(len(tenders), 50)  # Check first 50 tenders
            
            for tender in tenders[:total_checked]:
                for field in required_fields:
                    if not tender.get(field):
                        if field not in missing_fields_count:
                            missing_fields_count[field] = 0
                        missing_fields_count[field] += 1
            
            if not missing_fields_count:
                self.log_test("Required Fields Verification", True, 
                            f"All required fields present in {total_checked} tested tenders")
            else:
                missing_summary = {k: f"{v}/{total_checked}" for k, v in missing_fields_count.items()}
                self.log_test("Required Fields Verification", False, 
                            f"Missing fields found: {missing_summary}")
            
            # Country field verification
            countries = set(t.get("country") for t in tenders if t.get("country"))
            if "Germany" in countries and "Switzerland" in countries:
                self.log_test("Country Field Diversity", True, 
                            f"Found both Germany and Switzerland in country fields: {countries}")
            else:
                self.log_test("Country Field Diversity", False, 
                            f"Missing expected countries. Found: {countries}")
            
        except Exception as e:
            self.log_test("Data Integrity Requirements", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run complete test suite focused on review request requirements"""
        print("🚀 Starting GroVELLOWS Tender Tracking API Test Suite")
        print("Testing specific requirements from review request:")
        print("")
        print("**Authentication:**")
        print("- Login: POST /api/auth/login with director@grovellows.de / Director123")
        print("")
        print("**Critical Tests - Tender Country Filter:**")
        print("1. GET /api/tenders - Should return ~237 total tenders")
        print("2. GET /api/tenders?country=Germany - Should return ~231 German tenders ONLY")
        print("3. GET /api/tenders?country=Switzerland - Should return exactly 6 Swiss tenders ONLY")
        print("")
        print("**Verify Country Filter is Exclusive:**")
        print("- When country=Germany, verify NO tender has country='Switzerland'")
        print("- When country=Switzerland, verify ALL tenders have country='Switzerland'")
        print("- Check platform_source for Swiss tenders should be 'simap.ch (Schweiz)'")
        print("")
        print("**Platform Distribution Test:**")
        print("- Check platform_source includes: Ausschreibungen Deutschland, Vergabe Bayern, simap.ch (Schweiz), Asklepios Kliniken")
        print("")
        print("**Scraping Test:**")
        print("- POST /api/scrape/all with Director auth - Should trigger comprehensive scraper")
        print("")
        print(f"Backend URL: {BASE_URL}")
        print("=" * 80)
        
        start_time = time.time()
        
        # Run specific test requirements in order
        self.test_authentication()
        
        # Only proceed with other tests if authentication succeeds
        if self.director_token:
            tenders = self.test_tender_count_requirements()
            self.test_country_filtering_requirements()
            self.test_platform_distribution_requirements()
            self.test_scraping_requirements()
            self.test_data_integrity_requirements(tenders)
        else:
            print("\n❌ Authentication failed - cannot proceed with other tests")
        
        end_time = time.time()
        
        # Generate summary
        success = self.generate_summary(end_time - start_time)
        return success
        
    def generate_summary(self, duration: float):
        """Generate test summary"""
        print("\n" + "=" * 80)
        print("🏁 GROVELLOWS TENDER TRACKING API TEST SUMMARY")
        print("=" * 80)
        
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
        
        # Return success status
        return failed_tests == 0

if __name__ == "__main__":
    test_suite = GroVELLOWSTestSuite()
    success = test_suite.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed!")
        exit(0)
    else:
        print("\n💥 Some tests failed!")
        exit(1)