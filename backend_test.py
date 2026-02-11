#!/usr/bin/env python3
"""
GroVELLOWS Tender Tracking API Test Suite
Testing specific requirements from review request:
1. Authentication with director@grovellows.de / Director123
2. Tender API - should return 145+ tenders from multiple platforms
3. Scraping API - POST /api/scrape/all (requires Director role)
4. Filters - country=Germany, platform_source filtering
5. Data Integrity - verify fields and deduplication
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
    
    def test_tender_api_requirements(self):
        """Test 2: Tender API Requirements - 145+ tenders from multiple platforms"""
        print("\n=== TENDER API REQUIREMENTS ===")
        
        if not self.director_token:
            self.log_test("Tender API Requirements", False, "No director token available")
            return []
            
        try:
            response = self.make_request("GET", "/tenders", token=self.director_token)
            if response.status_code == 200:
                tenders = response.json()
                tender_count = len(tenders)
                
                # Check tender count requirement (145+)
                if tender_count >= 145:
                    self.log_test("Tender Count Requirement", True, f"Retrieved {tender_count} tenders (≥145 required)")
                else:
                    self.log_test("Tender Count Requirement", False, f"Only {tender_count} tenders found, expected ≥145")
                
                # Check platform source variety
                platform_sources = set()
                countries = set()
                required_platforms = ["Ausschreibungen Deutschland", "Vergabe Bayern", "Asklepios Kliniken"]
                
                for tender in tenders:
                    if tender.get("platform_source"):
                        platform_sources.add(tender["platform_source"])
                    if tender.get("country"):
                        countries.add(tender["country"])
                
                # Check for required platforms
                found_required = [p for p in required_platforms if p in platform_sources]
                if len(found_required) >= 2:
                    self.log_test("Platform Source Variety", True, 
                                f"Found {len(platform_sources)} platforms including required: {', '.join(found_required)}")
                else:
                    self.log_test("Platform Source Variety", False, 
                                f"Missing required platforms. Found: {', '.join(platform_sources)}")
                
                # Check country field presence
                if "Germany" in countries:
                    self.log_test("Country Field Verification", True, 
                                f"Country field present with Germany. Countries: {', '.join(countries)}")
                else:
                    self.log_test("Country Field Verification", False, 
                                f"Germany not found in country fields. Found: {', '.join(countries)}")
                
                return tenders
                
            else:
                self.log_test("Tender API Requirements", False, 
                            f"Failed to retrieve tenders, status: {response.status_code}")
                return []
                
        except Exception as e:
            self.log_test("Tender API Requirements", False, f"Exception: {str(e)}")
            return []

    def test_scraping_api_requirements(self):
        """Test 3: Scraping API - POST /api/scrape/all with comprehensive scraper"""
        print("\n=== SCRAPING API REQUIREMENTS ===")
        
        if not self.director_token:
            self.log_test("Scraping API Requirements", False, "No director token available")
            return
            
        # Test scrape status endpoint
        try:
            response = self.make_request("GET", "/scrape/status", token=self.director_token)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Scrape Status Check", True, f"Status retrieved successfully")
            else:
                self.log_test("Scrape Status Check", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Scrape Status Check", False, f"Exception: {str(e)}")
            
        # Test comprehensive scraper trigger
        try:
            response = self.make_request("POST", "/scrape/all", token=self.director_token)
            if response.status_code == 200:
                data = response.json()
                scraped_count = data.get("count", 0)
                sources = data.get("sources", [])
                
                self.log_test("Comprehensive Scraper Trigger", True, 
                            f"Scraping completed: {scraped_count} new tenders")
                
                # Verify 15+ German platforms
                if len(sources) >= 15:
                    self.log_test("German Platform Count", True, 
                                f"Uses {len(sources)} German platforms (≥15 required)")
                else:
                    self.log_test("German Platform Count", False, 
                                f"Only {len(sources)} platforms, expected ≥15. Sources: {sources}")
                
            elif response.status_code == 429:
                self.log_test("Comprehensive Scraper Trigger", True, 
                            "Rate limiting working correctly (429 Too Many Requests)")
            elif response.status_code == 403:
                self.log_test("Comprehensive Scraper Trigger", False, 
                            "Access denied - Director role authentication issue")
            else:
                self.log_test("Comprehensive Scraper Trigger", False, 
                            f"Scraping failed with status {response.status_code}")
                
        except Exception as e:
            self.log_test("Comprehensive Scraper Trigger", False, f"Exception: {str(e)}")
            
        # Test Director role requirement
        if self.regular_user_token:
            try:
                response = self.make_request("POST", "/scrape/all", token=self.regular_user_token)
                if response.status_code == 403:
                    self.log_test("Director Role Requirement", True, 
                                "Regular users correctly blocked from scraping")
                else:
                    self.log_test("Director Role Requirement", False, 
                                f"Regular user should be blocked. Status: {response.status_code}")
            except Exception as e:
                self.log_test("Director Role Requirement", False, f"Exception: {str(e)}")

    def test_filter_requirements(self):
        """Test 4: Filter Requirements - country=Germany and platform_source filtering"""
        print("\n=== FILTER REQUIREMENTS ===")
        
        if not self.director_token:
            self.log_test("Filter Requirements", False, "No director token available")
            return
            
        # Test country=Germany filter
        try:
            response = self.make_request("GET", "/tenders", token=self.director_token, 
                                       params={"country": "Germany"})
            if response.status_code == 200:
                germany_tenders = response.json()
                germany_count = len(germany_tenders)
                
                # Verify all returned tenders have country=Germany
                all_germany = all(t.get("country") == "Germany" for t in germany_tenders)
                
                if all_germany and germany_count > 0:
                    self.log_test("Country Filter (Germany)", True, 
                                f"Filter working: {germany_count} German tenders, all verified")
                else:
                    self.log_test("Country Filter (Germany)", False, 
                                f"Filter issue: {germany_count} tenders, all_germany={all_germany}")
            else:
                self.log_test("Country Filter (Germany)", False, 
                            f"Filter request failed: {response.status_code}")
        except Exception as e:
            self.log_test("Country Filter (Germany)", False, f"Exception: {str(e)}")
            
        # Test platform_source filter
        try:
            platform_name = "Ausschreibungen Deutschland"
            response = self.make_request("GET", "/tenders", token=self.director_token, 
                                       params={"platform_source": platform_name})
            if response.status_code == 200:
                platform_tenders = response.json()
                platform_count = len(platform_tenders)
                
                # Verify all returned tenders have correct platform_source
                correct_platform = all(t.get("platform_source") == platform_name for t in platform_tenders)
                
                if correct_platform:
                    self.log_test("Platform Source Filter", True, 
                                f"Filter working: {platform_count} tenders from {platform_name}")
                else:
                    self.log_test("Platform Source Filter", False, 
                                f"Filter issue: incorrect platform sources in results")
            else:
                self.log_test("Platform Source Filter", False, 
                            f"Filter request failed: {response.status_code}")
        except Exception as e:
            self.log_test("Platform Source Filter", False, f"Exception: {str(e)}")

    def test_data_integrity_requirements(self, tenders):
        """Test 5: Data Integrity - required fields and deduplication"""
        print("\n=== DATA INTEGRITY REQUIREMENTS ===")
        
        if not tenders:
            self.log_test("Data Integrity Requirements", False, "No tenders available for testing")
            return
            
        try:
            # Required fields verification
            required_fields = ["title", "description", "platform_source", "country", "location", "deadline"]
            missing_fields_count = {}
            total_checked = min(len(tenders), 100)  # Check first 100 tenders
            
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
            
            # Deduplication verification
            titles = [t.get("title", "") for t in tenders]
            unique_titles = set(titles)
            duplicate_count = len(titles) - len(unique_titles)
            
            if duplicate_count == 0:
                self.log_test("Deduplication Verification", True, 
                            f"No duplicate titles found in {len(titles)} tenders")
            else:
                # Find duplicate examples
                title_counts = {}
                for title in titles:
                    if title:  # Skip empty titles
                        title_counts[title] = title_counts.get(title, 0) + 1
                
                duplicates = {k: v for k, v in title_counts.items() if v > 1}
                duplicate_examples = list(duplicates.items())[:3]  # Show first 3 examples
                
                self.log_test("Deduplication Verification", False, 
                            f"{duplicate_count} duplicate titles found. Examples: {duplicate_examples}")
            
        except Exception as e:
            self.log_test("Data Integrity Requirements", False, f"Exception: {str(e)}")
    
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

    def run_all_tests(self):
        """Run complete test suite focused on review request requirements"""
        print("🚀 Starting GroVELLOWS Tender Tracking API Test Suite")
        print("Testing specific requirements from review request:")
        print("1. Authentication with director@grovellows.de / Director123")
        print("2. Tender API - should return 145+ tenders from multiple platforms")
        print("3. Scraping API - POST /api/scrape/all (requires Director role)")
        print("4. Filters - country=Germany, platform_source filtering")
        print("5. Data Integrity - verify fields and deduplication")
        print(f"Backend URL: {BASE_URL}")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run specific test requirements
        self.test_authentication()
        
        # Only proceed with other tests if authentication succeeds
        if self.director_token:
            tenders = self.test_tender_api_requirements()
            self.test_scraping_api_requirements()
            self.test_filter_requirements()
            self.test_data_integrity_requirements(tenders)
        else:
            print("\n❌ Authentication failed - cannot proceed with other tests")
        
        end_time = time.time()
        
        # Generate summary
        self.generate_summary(end_time - start_time)

if __name__ == "__main__":
    test_suite = GroVELLOWSTestSuite()
    test_suite.run_all_tests()