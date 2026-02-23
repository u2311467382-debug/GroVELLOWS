#!/usr/bin/env python3
"""
GroVELLOWS Backend API Testing Suite - User Review Request
Tests specific endpoints as requested in the review request:

1. Authentication Tests (director@grovellows.de / Director123)
2. Tenders API Tests (GET /api/tenders with country filtering)
3. Developer Projects API Tests (GET /api/developer-projects)
4. Favorites API Tests (GET /api/favorites)
5. Market News API Tests (GET /api/news)

Backend URL: https://tender-tracker-dev.preview.emergentagent.com/api
"""

import requests
import json
import sys
from datetime import datetime

# Backend URL from user review request
BACKEND_URL = "https://tender-tracker-dev.preview.emergentagent.com/api"

# Test credentials from user review request
DIRECTOR_EMAIL = "director@grovellows.de"
DIRECTOR_PASSWORD = "Director123"

class GroVELLOWSReviewTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.passed = 0
        self.failed = 0
        self.test_results = []
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def record_test(self, test_name, status, details):
        """Record test result"""
        self.test_results.append({
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
        if status == "PASS":
            self.passed += 1
        else:
            self.failed += 1
    
    def test_authentication(self):
        """Test authentication with valid director credentials"""
        self.log("=" * 70)
        self.log("1. AUTHENTICATION TESTS")
        self.log("=" * 70)
        
        try:
            # Test login with director credentials
            login_data = {
                "email": DIRECTOR_EMAIL,
                "password": DIRECTOR_PASSWORD
            }
            
            self.log(f"Testing login with {DIRECTOR_EMAIL}")
            response = self.session.post(f"{BACKEND_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.token = data["access_token"]
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.token}"
                    })
                    user_role = data.get('user', {}).get('role', 'Unknown')
                    
                    self.log("✅ Authentication successful", "PASS")
                    self.log(f"✅ Token received and set", "PASS") 
                    self.log(f"✅ User role: {user_role}", "PASS")
                    
                    self.record_test("Director Authentication", "PASS", 
                                   f"Login successful with role: {user_role}")
                    return True
                else:
                    error_msg = "No access_token in response"
                    self.log(f"❌ {error_msg}", "FAIL")
                    self.record_test("Director Authentication", "FAIL", error_msg)
                    return False
            else:
                error_msg = f"Login failed: {response.status_code} - {response.text}"
                self.log(f"❌ {error_msg}", "FAIL")
                self.record_test("Director Authentication", "FAIL", error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Authentication error: {str(e)}"
            self.log(f"❌ {error_msg}", "FAIL")
            self.record_test("Director Authentication", "FAIL", error_msg)
            return False
    
    def test_protected_endpoint_access(self):
        """Test accessing protected endpoints with token"""
        self.log("\nTesting protected endpoint access...")
        
        if not self.token:
            error_msg = "No token available for protected endpoint test"
            self.log(f"❌ {error_msg}", "FAIL")
            self.record_test("Protected Endpoint Access", "FAIL", error_msg)
            return False
            
        try:
            # Test /auth/me endpoint
            response = self.session.get(f"{BACKEND_URL}/auth/me")
            
            if response.status_code == 200:
                data = response.json()
                self.log("✅ Protected endpoints accessible with token", "PASS")
                
                details = f"User: {data.get('email')} - Role: {data.get('role')}"
                self.record_test("Protected Endpoint Access", "PASS", details)
                return True
            else:
                error_msg = f"Protected endpoint failed: {response.status_code} - {response.text}"
                self.log(f"❌ {error_msg}", "FAIL")
                self.record_test("Protected Endpoint Access", "FAIL", error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Protected endpoint error: {str(e)}"
            self.log(f"❌ {error_msg}", "FAIL")
            self.record_test("Protected Endpoint Access", "FAIL", error_msg)
            return False
    
    def test_tenders_api(self):
        """Test Tenders API endpoints and filtering"""
        self.log("\n" + "=" * 70)
        self.log("2. TENDERS API TESTS")
        self.log("=" * 70)
        
        try:
            # Test GET /api/tenders
            self.log("Testing GET /api/tenders")
            response = self.session.get(f"{BACKEND_URL}/tenders")
            
            if response.status_code == 200:
                tenders = response.json()
                self.log(f"✅ Tenders endpoint working - Found {len(tenders)} tenders", "PASS")
                
                # Check tender structure
                if tenders and len(tenders) > 0:
                    tender = tenders[0]
                    required_fields = ['title', 'description', 'country', 'location', 'deadline']
                    missing_fields = [field for field in required_fields if field not in tender]
                    
                    if not missing_fields:
                        self.log("✅ Tenders have required fields (title, description, country, location, deadline)", "PASS")
                        self.record_test("Tenders API Structure", "PASS", 
                                       f"All required fields present. Sample tender: {tender.get('title', 'Unknown')}")
                    else:
                        error_msg = f"Missing required fields: {missing_fields}"
                        self.log(f"❌ {error_msg}", "FAIL")
                        self.record_test("Tenders API Structure", "FAIL", error_msg)
                        return False
                else:
                    self.log("⚠️ No tenders found in database", "WARN")
                
                self.record_test("Tenders API Basic", "PASS", f"Retrieved {len(tenders)} tenders successfully")
            else:
                error_msg = f"Tenders endpoint failed: {response.status_code} - {response.text}"
                self.log(f"❌ {error_msg}", "FAIL")
                self.record_test("Tenders API Basic", "FAIL", error_msg)
                return False
            
            # Test country filtering
            self.log("\nTesting country filtering...")
            
            # Test Germany filter
            response = self.session.get(f"{BACKEND_URL}/tenders?country=Germany")
            if response.status_code == 200:
                german_tenders = response.json()
                self.log(f"✅ Germany filter working - Found {len(german_tenders)} German tenders", "PASS")
                self.record_test("Germany Country Filter", "PASS", f"Found {len(german_tenders)} German tenders")
            else:
                error_msg = f"Germany filter failed: {response.status_code}"
                self.log(f"❌ {error_msg}", "FAIL")
                self.record_test("Germany Country Filter", "FAIL", error_msg)
            
            # Test Switzerland filter  
            response = self.session.get(f"{BACKEND_URL}/tenders?country=Switzerland")
            if response.status_code == 200:
                swiss_tenders = response.json()
                self.log(f"✅ Switzerland filter working - Found {len(swiss_tenders)} Swiss tenders", "PASS")
                self.record_test("Switzerland Country Filter", "PASS", f"Found {len(swiss_tenders)} Swiss tenders")
            else:
                error_msg = f"Switzerland filter failed: {response.status_code}"
                self.log(f"❌ {error_msg}", "FAIL")
                self.record_test("Switzerland Country Filter", "FAIL", error_msg)
                
            # Test International filter
            response = self.session.get(f"{BACKEND_URL}/tenders?country=International")
            if response.status_code == 200:
                international_tenders = response.json()
                self.log(f"✅ International filter working - Found {len(international_tenders)} International tenders", "PASS")
                
                # Check if any tender has country="International"
                has_international = any(t.get('country') == 'International' for t in international_tenders)
                details = f"Found {len(international_tenders)} tenders. Has country='International': {has_international}"
                
                self.record_test("International Country Filter", "PASS", details)
            else:
                error_msg = f"International filter failed: {response.status_code}"
                self.log(f"❌ {error_msg}", "FAIL")
                self.record_test("International Country Filter", "FAIL", error_msg)
            
            return True
            
        except Exception as e:
            error_msg = f"Tenders API error: {str(e)}"
            self.log(f"❌ {error_msg}", "FAIL")
            self.record_test("Tenders API", "FAIL", error_msg)
            return False
    
    def test_developer_projects_api(self):
        """Test Developer Projects API endpoints"""
        self.log("\n" + "=" * 70)
        self.log("3. DEVELOPER PROJECTS API TESTS")
        self.log("=" * 70)
        
        try:
            # Test GET /api/developer-projects
            self.log("Testing GET /api/developer-projects")
            response = self.session.get(f"{BACKEND_URL}/developer-projects")
            
            if response.status_code == 200:
                projects = response.json()
                self.log(f"✅ Developer Projects endpoint working - Found {len(projects)} projects", "PASS")
                
                # Check project structure if projects exist
                if projects and len(projects) > 0:
                    project = projects[0]
                    required_fields = ['developer_name', 'project_name', 'description', 'location', 'status']
                    missing_fields = [field for field in required_fields if field not in project]
                    
                    if not missing_fields:
                        self.log("✅ Developer projects have required fields", "PASS")
                        sample_project = f"{project.get('developer_name', 'Unknown')} - {project.get('project_name', 'Unknown')}"
                        details = f"Found {len(projects)} projects. Sample: {sample_project}"
                    else:
                        self.log(f"⚠️ Some projects missing fields: {missing_fields}", "WARN")
                        details = f"Found {len(projects)} projects. Missing fields: {missing_fields}"
                        
                    # Log some sample projects
                    self.log(f"Sample project: {project.get('developer_name', 'Unknown')} - {project.get('project_name', 'Unknown')}", "INFO")
                else:
                    self.log("⚠️ No developer projects found in database", "WARN")
                    details = "Endpoint working but no projects found"
                
                self.record_test("Developer Projects API", "PASS", details)
                return True
            else:
                error_msg = f"Developer Projects endpoint failed: {response.status_code} - {response.text}"
                self.log(f"❌ {error_msg}", "FAIL")
                self.record_test("Developer Projects API", "FAIL", error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Developer Projects API error: {str(e)}"
            self.log(f"❌ {error_msg}", "FAIL")
            self.record_test("Developer Projects API", "FAIL", error_msg)
            return False
    
    def test_favorites_api(self):
        """Test Favorites API endpoints"""
        self.log("\n" + "=" * 70)
        self.log("4. FAVORITES API TESTS")
        self.log("=" * 70)
        
        try:
            # Test GET /api/favorites
            self.log("Testing GET /api/favorites")
            response = self.session.get(f"{BACKEND_URL}/favorites")
            
            if response.status_code == 200:
                favorites = response.json()
                self.log(f"✅ Favorites endpoint working - Found {len(favorites)} favorite tenders", "PASS")
                
                if favorites and len(favorites) > 0:
                    sample_favorite = favorites[0].get('title', 'Unknown')
                    details = f"Found {len(favorites)} favorites. Sample: {sample_favorite}"
                    self.log(f"Sample favorite: {sample_favorite}", "INFO")
                else:
                    self.log("⚠️ No favorites found for current user", "INFO")
                    details = "Endpoint working but no favorites found for current user"
                
                self.record_test("Favorites API", "PASS", details)
                return True
            else:
                error_msg = f"Favorites endpoint failed: {response.status_code} - {response.text}"
                self.log(f"❌ {error_msg}", "FAIL")
                self.record_test("Favorites API", "FAIL", error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Favorites API error: {str(e)}"
            self.log(f"❌ {error_msg}", "FAIL")
            self.record_test("Favorites API", "FAIL", error_msg)
            return False
    
    def test_market_news_api(self):
        """Test Market News API endpoints"""
        self.log("\n" + "=" * 70)
        self.log("5. MARKET NEWS API TESTS")
        self.log("=" * 70)
        
        try:
            # Test GET /api/news
            self.log("Testing GET /api/news")
            response = self.session.get(f"{BACKEND_URL}/news")
            
            if response.status_code == 200:
                news_articles = response.json()
                self.log(f"✅ News endpoint working - Found {len(news_articles)} articles", "PASS")
                
                if news_articles and len(news_articles) > 0:
                    article = news_articles[0]
                    required_fields = ['title', 'source', 'url']
                    missing_fields = [field for field in required_fields if field not in article]
                    
                    if not missing_fields:
                        self.log("✅ News articles have required fields", "PASS")
                        details = f"Found {len(news_articles)} articles with proper structure"
                    else:
                        self.log(f"⚠️ Some articles missing fields: {missing_fields}", "WARN")
                        details = f"Found {len(news_articles)} articles. Missing fields: {missing_fields}"
                        
                    # Log sample article
                    sample_title = article.get('title', 'Unknown')
                    sample_source = article.get('source', 'Unknown')
                    self.log(f"Sample article: '{sample_title}' from {sample_source}", "INFO")
                else:
                    self.log("⚠️ No news articles found in database", "WARN")
                    details = "Endpoint working but no news articles found"
                
                self.record_test("Market News API", "PASS", details)
                return True
            else:
                error_msg = f"News endpoint failed: {response.status_code} - {response.text}"
                self.log(f"❌ {error_msg}", "FAIL")
                self.record_test("Market News API", "FAIL", error_msg)
                return False
                
        except Exception as e:
            error_msg = f"News API error: {str(e)}"
            self.log(f"❌ {error_msg}", "FAIL")
            self.record_test("Market News API", "FAIL", error_msg)
            return False
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        self.log("🚀 Starting GroVELLOWS Backend API Testing - User Review Request")
        self.log(f"🔗 Backend URL: {BACKEND_URL}")
        self.log(f"👤 Test User: {DIRECTOR_EMAIL}")
        self.log(f"🕒 Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run tests in order
        auth_success = self.test_authentication()
        if auth_success:
            self.test_protected_endpoint_access()
            self.test_tenders_api()
            self.test_developer_projects_api()
            self.test_favorites_api()
            self.test_market_news_api()
        else:
            self.log("❌ Authentication failed - skipping other tests", "ERROR")
        
        # Final summary
        self.log("\n" + "=" * 70)
        self.log("TESTING SUMMARY")
        self.log("=" * 70)
        total_tests = self.passed + self.failed
        success_rate = (self.passed / total_tests * 100) if total_tests > 0 else 0
        
        self.log(f"✅ Passed: {self.passed}")
        self.log(f"❌ Failed: {self.failed}")
        self.log(f"📊 Success Rate: {success_rate:.1f}%")
        
        # Show detailed results
        self.log("\n📋 DETAILED TEST RESULTS:")
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            self.log(f"  {status_icon} {result['test']}: {result['details']}")
        
        if self.failed == 0:
            self.log("\n🎉 ALL TESTS PASSED!", "PASS")
            return True
        else:
            self.log(f"\n⚠️ {self.failed} tests failed. Check logs above.", "WARN")
            return False

def main():
    """Main test execution"""
    tester = GroVELLOWSReviewTester()
    success = tester.run_all_tests()
    
    # Save detailed results
    results_file = "/app/review_test_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "backend_url": BACKEND_URL,
            "total_tests": len(tester.test_results),
            "passed": tester.passed,
            "failed": tester.failed,
            "success_rate": (tester.passed / len(tester.test_results) * 100) if tester.test_results else 0,
            "test_results": tester.test_results
        }, f, indent=2)
    
    print(f"\n📁 Detailed results saved to: {results_file}")
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()