#!/usr/bin/env python3
"""
Additional GroVELLOWS Backend Tests - Edge Cases and Security
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "https://constructbid-6.preview.emergentagent.com/api"

DIRECTOR_CREDENTIALS = {
    "email": "director@grovellows.de",
    "password": "Director123"
}

def test_rate_limiting():
    """Test rate limiting on scrape endpoint"""
    print("\n=== RATE LIMITING TEST ===")
    
    # Login as director
    login_response = requests.post(f"{BASE_URL}/auth/login", json=DIRECTOR_CREDENTIALS)
    if login_response.status_code != 200:
        print("❌ Could not login as director")
        return
        
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # First scrape request
    response1 = requests.post(f"{BASE_URL}/scrape/all", headers=headers)
    print(f"First scrape request: {response1.status_code}")
    
    # Immediate second request (should be rate limited)
    response2 = requests.post(f"{BASE_URL}/scrape/all", headers=headers)
    if response2.status_code == 429:
        print("✅ Rate limiting working correctly - second request blocked")
    else:
        print(f"❌ Rate limiting not working - second request status: {response2.status_code}")

def test_security_features():
    """Test various security features"""
    print("\n=== SECURITY TESTS ===")
    
    # Test unauthorized access
    response = requests.get(f"{BASE_URL}/tenders")
    if response.status_code == 401:
        print("✅ Unauthorized access correctly blocked")
    else:
        print(f"❌ Unauthorized access not blocked: {response.status_code}")
    
    # Test invalid token
    headers = {"Authorization": "Bearer invalid_token"}
    response = requests.get(f"{BASE_URL}/tenders", headers=headers)
    if response.status_code == 401:
        print("✅ Invalid token correctly rejected")
    else:
        print(f"❌ Invalid token not rejected: {response.status_code}")

def test_data_integrity():
    """Test data integrity and validation"""
    print("\n=== DATA INTEGRITY TESTS ===")
    
    # Login as director
    login_response = requests.post(f"{BASE_URL}/auth/login", json=DIRECTOR_CREDENTIALS)
    if login_response.status_code != 200:
        print("❌ Could not login as director")
        return
        
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test invalid tender ID
    response = requests.get(f"{BASE_URL}/tenders/invalid_id", headers=headers)
    if response.status_code == 422 or response.status_code == 400:
        print("✅ Invalid tender ID correctly rejected")
    else:
        print(f"❌ Invalid tender ID not handled properly: {response.status_code}")
    
    # Test invalid application status
    response = requests.get(f"{BASE_URL}/tenders", headers=headers)
    if response.status_code == 200:
        tenders = response.json()
        if tenders:
            tender_id = tenders[0]["id"]
            # Try invalid status
            status_response = requests.put(
                f"{BASE_URL}/tenders/{tender_id}/application-status",
                headers=headers,
                params={"status": "InvalidStatus"}
            )
            if status_response.status_code == 400:
                print("✅ Invalid application status correctly rejected")
            else:
                print(f"❌ Invalid application status not rejected: {status_response.status_code}")

def test_gdpr_data_export():
    """Test GDPR data export contains expected fields"""
    print("\n=== GDPR DATA EXPORT VALIDATION ===")
    
    # Login as director
    login_response = requests.post(f"{BASE_URL}/auth/login", json=DIRECTOR_CREDENTIALS)
    if login_response.status_code != 200:
        print("❌ Could not login as director")
        return
        
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get personal data export
    response = requests.get(f"{BASE_URL}/gdpr/my-data", headers=headers)
    if response.status_code == 200:
        data = response.json()
        expected_fields = ["user_data", "favorites", "applications", "shares_sent", "shares_received"]
        
        missing_fields = [field for field in expected_fields if field not in data]
        if not missing_fields:
            print("✅ GDPR data export contains all expected fields")
        else:
            print(f"❌ GDPR data export missing fields: {missing_fields}")
    else:
        print(f"❌ Could not get GDPR data export: {response.status_code}")

if __name__ == "__main__":
    print("🔒 Running Additional Security and Edge Case Tests")
    print("=" * 60)
    
    test_rate_limiting()
    test_security_features()
    test_data_integrity()
    test_gdpr_data_export()
    
    print("\n✅ Additional tests completed")