#!/usr/bin/env python3
"""
Backend API Testing Script for Calorie Counter App
Tests all backend endpoints using the production URL from frontend/.env
"""

import requests
import json
import base64
import os
from typing import Dict, Any, Optional
import sys

# Load frontend .env to get backend URL
def load_frontend_env():
    env_path = "/app/frontend/.env"
    env_vars = {}
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value.strip('"')
    except Exception as e:
        print(f"Error loading frontend .env: {e}")
    return env_vars

# Get backend URL
frontend_env = load_frontend_env()
BACKEND_URL = frontend_env.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API_BASE = f"{BACKEND_URL}/api"

print(f"Testing backend at: {API_BASE}")

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = []
        
    def log_result(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        if response_data and not success:
            print(f"   Response: {response_data}")
        print()
        
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'response': response_data
        })
    
    def test_health_endpoint(self):
        """Test GET /api/health"""
        try:
            response = self.session.get(f"{API_BASE}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = ['status', 'db', 'model', 'llm_key_available', 'time']
                missing_fields = [field for field in expected_fields if field not in data]
                
                if not missing_fields and data.get('status') == 'ok':
                    self.log_result("Health Endpoint", True, f"Status: {data.get('status')}, DB: {data.get('db')}, LLM Key: {data.get('llm_key_available')}")
                else:
                    self.log_result("Health Endpoint", False, f"Missing fields: {missing_fields} or status not 'ok'", data)
            else:
                self.log_result("Health Endpoint", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("Health Endpoint", False, f"Request failed: {str(e)}")
    
    def test_auth_register(self):
        """Test POST /api/auth/register"""
        try:
            # Use realistic test data
            test_email = "sarah.johnson@example.com"
            test_password = "SecurePass123!"
            
            payload = {
                "email": test_email,
                "password": test_password
            }
            
            response = self.session.post(f"{API_BASE}/auth/register", json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'access_token' in data and 'token_type' in data:
                    self.auth_token = data['access_token']
                    self.log_result("Auth Register", True, f"Token received, type: {data.get('token_type')}")
                else:
                    self.log_result("Auth Register", False, "Missing token fields in response", data)
            elif response.status_code == 400:
                # Email might already exist, try login instead
                self.log_result("Auth Register", True, "Email already exists (expected for repeated tests)")
                self.test_auth_login_existing(test_email, test_password)
            else:
                self.log_result("Auth Register", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("Auth Register", False, f"Request failed: {str(e)}")
    
    def test_auth_login_existing(self, email: str, password: str):
        """Test login with existing credentials"""
        try:
            payload = {
                "email": email,
                "password": password
            }
            
            response = self.session.post(f"{API_BASE}/auth/login", json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'access_token' in data:
                    self.auth_token = data['access_token']
                    self.log_result("Auth Login (existing user)", True, f"Token received, type: {data.get('token_type')}")
                else:
                    self.log_result("Auth Login (existing user)", False, "Missing token in response", data)
            else:
                self.log_result("Auth Login (existing user)", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("Auth Login (existing user)", False, f"Request failed: {str(e)}")
    
    def test_auth_login(self):
        """Test POST /api/auth/login with new credentials"""
        try:
            # Test with different credentials for login test
            test_email = "mike.davis@example.com"
            test_password = "TestLogin456!"
            
            # First register this user
            register_payload = {
                "email": test_email,
                "password": test_password
            }
            
            register_response = self.session.post(f"{API_BASE}/auth/register", json=register_payload, timeout=10)
            
            # Now test login
            login_payload = {
                "email": test_email,
                "password": test_password
            }
            
            response = self.session.post(f"{API_BASE}/auth/login", json=login_payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'access_token' in data and 'token_type' in data:
                    self.log_result("Auth Login", True, f"Login successful, token type: {data.get('token_type')}")
                else:
                    self.log_result("Auth Login", False, "Missing token fields in response", data)
            else:
                self.log_result("Auth Login", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("Auth Login", False, f"Request failed: {str(e)}")
    
    def test_profile_update(self):
        """Test PUT /api/profile with JWT authentication"""
        if not self.auth_token:
            self.log_result("Profile Update", False, "No auth token available")
            return
            
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            # Realistic profile data
            payload = {
                "height_cm": 170.0,
                "weight_kg": 68.5,
                "age": 28,
                "gender": "female",
                "activity_level": "moderate",
                "goal": "lose",
                "goal_intensity": "moderate",
                "goal_weight_kg": 63.0
            }
            
            response = self.session.put(f"{API_BASE}/profile", json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = ['id', 'email', 'profile']
                missing_fields = [field for field in expected_fields if field not in data]
                
                if not missing_fields and data.get('profile'):
                    profile = data['profile']
                    if 'recommended_daily_calories' in profile:
                        calories = profile['recommended_daily_calories']
                        self.log_result("Profile Update", True, f"Profile updated, recommended calories: {calories}")
                    else:
                        self.log_result("Profile Update", False, "Missing recommended_daily_calories in profile", data)
                else:
                    self.log_result("Profile Update", False, f"Missing fields: {missing_fields} or no profile data", data)
            else:
                self.log_result("Profile Update", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("Profile Update", False, f"Request failed: {str(e)}")
    
    def test_ai_estimate_simulate(self):
        """Test POST /api/ai/estimate-calories with simulate=true"""
        try:
            # Create a simple base64 image (1x1 pixel PNG)
            simple_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
            
            payload = {
                "message": "Please estimate calories for this meal",
                "images": [
                    {
                        "data": simple_png_b64,
                        "mime_type": "image/png",
                        "filename": "test_meal.png"
                    }
                ],
                "simulate": True
            }
            
            response = self.session.post(f"{API_BASE}/ai/estimate-calories", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = ['total_calories', 'items', 'confidence', 'notes']
                missing_fields = [field for field in expected_fields if field not in data]
                
                if not missing_fields:
                    total_cal = data.get('total_calories', 0)
                    items_count = len(data.get('items', []))
                    confidence = data.get('confidence', 0)
                    self.log_result("AI Estimate (Simulate)", True, 
                                  f"Total calories: {total_cal}, Items: {items_count}, Confidence: {confidence}")
                else:
                    self.log_result("AI Estimate (Simulate)", False, f"Missing fields: {missing_fields}", data)
            else:
                self.log_result("AI Estimate (Simulate)", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("AI Estimate (Simulate)", False, f"Request failed: {str(e)}")
    
    def test_end_to_end_auth_save_flow(self):
        """
        End-to-end validation of auth + save flow using curl-like requests:
        1) Register and login to get token
        2) Create a meal with captured_at including timezone offset
        3) Fetch meals for that local date with tz_offset_minutes; confirm the created meal is returned and daily_total reflects it
        4) Delete the meal and confirm removal
        """
        print("=" * 60)
        print("END-TO-END AUTH + SAVE FLOW VALIDATION")
        print("=" * 60)
        
        # Step 1: Register and login to get token
        print("Step 1: Register and login to get token")
        print("-" * 40)
        
        test_email = "endtoend.test@example.com"
        test_password = "EndToEndTest123!"
        
        # Register
        register_payload = {
            "email": test_email,
            "password": test_password
        }
        
        try:
            register_response = self.session.post(f"{API_BASE}/auth/register", json=register_payload, timeout=10)
            print(f"Register Request: POST {API_BASE}/auth/register")
            print(f"Register Payload: {json.dumps(register_payload, indent=2)}")
            print(f"Register Response Code: {register_response.status_code}")
            
            if register_response.status_code == 200:
                register_data = register_response.json()
                print(f"Register Response: {json.dumps(register_data, indent=2)}")
                token = register_data.get('access_token')
                print(f"✅ Registration successful, token obtained")
            elif register_response.status_code == 400:
                # User might already exist, try login
                print("User already exists, attempting login...")
                login_payload = {
                    "email": test_email,
                    "password": test_password
                }
                
                login_response = self.session.post(f"{API_BASE}/auth/login", json=login_payload, timeout=10)
                print(f"Login Request: POST {API_BASE}/auth/login")
                print(f"Login Payload: {json.dumps(login_payload, indent=2)}")
                print(f"Login Response Code: {login_response.status_code}")
                
                if login_response.status_code == 200:
                    login_data = login_response.json()
                    print(f"Login Response: {json.dumps(login_data, indent=2)}")
                    token = login_data.get('access_token')
                    print(f"✅ Login successful, token obtained")
                else:
                    print(f"❌ Login failed: {login_response.text}")
                    return
            else:
                print(f"❌ Registration failed: {register_response.text}")
                return
                
        except Exception as e:
            print(f"❌ Auth step failed: {str(e)}")
            return
        
        print()
        
        # Step 2: Create a meal with captured_at including timezone offset
        print("Step 2: Create a meal with captured_at including timezone offset")
        print("-" * 40)
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Create meal with timezone-aware captured_at (Berlin time: UTC+1 in winter, UTC+2 in summer)
        # Using +02:00 offset (summer time)
        meal_payload = {
            "total_calories": 450.0,
            "items": [
                {
                    "name": "Grilled salmon",
                    "quantity_units": "150g",
                    "calories": 280.0,
                    "confidence": 0.85
                },
                {
                    "name": "Quinoa salad",
                    "quantity_units": "1 cup",
                    "calories": 170.0,
                    "confidence": 0.80
                }
            ],
            "notes": "Healthy lunch with timezone test",
            "captured_at": "2025-01-15T12:00:00+02:00"  # Berlin time with +2 offset
        }
        
        try:
            meal_response = self.session.post(f"{API_BASE}/meals", json=meal_payload, headers=headers, timeout=10)
            print(f"Create Meal Request: POST {API_BASE}/meals")
            print(f"Create Meal Headers: {json.dumps(dict(headers), indent=2)}")
            print(f"Create Meal Payload: {json.dumps(meal_payload, indent=2)}")
            print(f"Create Meal Response Code: {meal_response.status_code}")
            
            if meal_response.status_code == 200:
                meal_data = meal_response.json()
                print(f"Create Meal Response: {json.dumps(meal_data, indent=2)}")
                meal_id = meal_data.get('id')
                print(f"✅ Meal created successfully, ID: {meal_id}")
            else:
                print(f"❌ Meal creation failed: {meal_response.text}")
                return
                
        except Exception as e:
            print(f"❌ Meal creation failed: {str(e)}")
            return
        
        print()
        
        # Step 3: Fetch meals for that local date with tz_offset_minutes
        print("Step 3: Fetch meals for that local date with tz_offset_minutes")
        print("-" * 40)
        
        # For Berlin time (+02:00), the offset in minutes is -120 (JS getTimezoneOffset returns negative for ahead of UTC)
        tz_offset_minutes = -120  # Berlin summer time offset
        local_date = "2025-01-15"  # The date in local time
        
        try:
            fetch_url = f"{API_BASE}/meals?date={local_date}&tz_offset_minutes={tz_offset_minutes}"
            fetch_response = self.session.get(fetch_url, headers=headers, timeout=10)
            print(f"Fetch Meals Request: GET {fetch_url}")
            print(f"Fetch Meals Headers: {json.dumps(dict(headers), indent=2)}")
            print(f"Fetch Meals Response Code: {fetch_response.status_code}")
            
            if fetch_response.status_code == 200:
                fetch_data = fetch_response.json()
                print(f"Fetch Meals Response: {json.dumps(fetch_data, indent=2)}")
                
                meals = fetch_data.get('meals', [])
                daily_total = fetch_data.get('daily_total', 0)
                
                # Verify the created meal is returned
                meal_found = any(meal.get('id') == meal_id for meal in meals)
                
                if meal_found and daily_total == 450.0:
                    print(f"✅ Meal fetch successful: Found {len(meals)} meal(s), daily_total: {daily_total}")
                else:
                    print(f"❌ Meal verification failed: meal_found={meal_found}, daily_total={daily_total} (expected 450.0)")
                    return
            else:
                print(f"❌ Meal fetch failed: {fetch_response.text}")
                return
                
        except Exception as e:
            print(f"❌ Meal fetch failed: {str(e)}")
            return
        
        print()
        
        # Step 4: Delete the meal and confirm removal
        print("Step 4: Delete the meal and confirm removal")
        print("-" * 40)
        
        try:
            delete_response = self.session.delete(f"{API_BASE}/meals/{meal_id}", headers=headers, timeout=10)
            print(f"Delete Meal Request: DELETE {API_BASE}/meals/{meal_id}")
            print(f"Delete Meal Headers: {json.dumps(dict(headers), indent=2)}")
            print(f"Delete Meal Response Code: {delete_response.status_code}")
            
            if delete_response.status_code == 200:
                delete_data = delete_response.json()
                print(f"Delete Meal Response: {json.dumps(delete_data, indent=2)}")
                
                if delete_data.get('deleted'):
                    print(f"✅ Meal deleted successfully")
                else:
                    print(f"❌ Meal deletion response invalid: {delete_data}")
                    return
            else:
                print(f"❌ Meal deletion failed: {delete_response.text}")
                return
                
        except Exception as e:
            print(f"❌ Meal deletion failed: {str(e)}")
            return
        
        print()
        
        # Verify removal by fetching again
        print("Verification: Confirm meal removal")
        print("-" * 40)
        
        try:
            verify_response = self.session.get(fetch_url, headers=headers, timeout=10)
            print(f"Verify Removal Request: GET {fetch_url}")
            print(f"Verify Removal Response Code: {verify_response.status_code}")
            
            if verify_response.status_code == 200:
                verify_data = verify_response.json()
                print(f"Verify Removal Response: {json.dumps(verify_data, indent=2)}")
                
                meals_after = verify_data.get('meals', [])
                daily_total_after = verify_data.get('daily_total', 0)
                
                # Verify the meal is no longer there
                meal_still_exists = any(meal.get('id') == meal_id for meal in meals_after)
                
                if not meal_still_exists and daily_total_after == 0.0:
                    print(f"✅ Meal removal confirmed: {len(meals_after)} meal(s), daily_total: {daily_total_after}")
                else:
                    print(f"❌ Meal removal verification failed: meal_still_exists={meal_still_exists}, daily_total={daily_total_after}")
                    return
            else:
                print(f"❌ Meal removal verification failed: {verify_response.text}")
                return
                
        except Exception as e:
            print(f"❌ Meal removal verification failed: {str(e)}")
            return
        
        print()
        print("🎉 END-TO-END AUTH + SAVE FLOW VALIDATION COMPLETED SUCCESSFULLY!")
        print("All steps passed:")
        print("✅ 1) Register and login to get token")
        print("✅ 2) Create a meal with captured_at including timezone offset")
        print("✅ 3) Fetch meals for that local date with tz_offset_minutes; confirm the created meal is returned and daily_total reflects it")
        print("✅ 4) Delete the meal and confirm removal")
        
        self.log_result("End-to-End Auth + Save Flow", True, "All 4 steps completed successfully with proper HTTP codes and data validation")

    def run_all_tests(self):
        """Run all backend tests"""
        print("=" * 60)
        print("BACKEND API TESTING")
        print("=" * 60)
        
        # Test in logical order
        self.test_health_endpoint()
        self.test_auth_register()
        self.test_auth_login()
        self.test_profile_update()
        self.test_ai_estimate_simulate()
        
        # Summary
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if passed < total:
            print("\nFAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"- {result['test']}: {result['details']}")
        
        return passed == total
    
    def run_end_to_end_test_only(self):
        """Run only the end-to-end auth + save flow test"""
        self.test_end_to_end_auth_save_flow()
        
        # Check if the test passed
        end_to_end_result = next((r for r in self.test_results if r['test'] == "End-to-End Auth + Save Flow"), None)
        return end_to_end_result and end_to_end_result['success']

if __name__ == "__main__":
    tester = BackendTester()
    
    # Check if we should run only the end-to-end test
    if len(sys.argv) > 1 and sys.argv[1] == "--end-to-end":
        success = tester.run_end_to_end_test_only()
    else:
        success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)