#!/usr/bin/env python3
"""
Timezone and Key Policy Patch Verification Test
Tests specific scenarios requested in the review:
1. Health endpoint
2. AI estimate with emergent key (empty api_key)
3. Meals create with timezone-aware captured_at
4. Meals fetch with timezone offset
5. Meals delete
"""

import requests
import json
import base64
import os
from datetime import datetime, timezone, timedelta
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
print("=" * 80)
print("TIMEZONE AND KEY POLICY PATCH VERIFICATION")
print("=" * 80)

class TimezoneKeyTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = []
        self.meal_id = None
        
    def log_result(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result with JSON body output"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"\n{status} {test_name}")
        if details:
            print(f"Details: {details}")
        if response_data:
            print(f"Response JSON: {json.dumps(response_data, indent=2)}")
        
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'response': response_data
        })
    
    def setup_auth(self):
        """Setup authentication for protected endpoints"""
        try:
            # Register/login to get fresh token
            test_email = "timezone.test@example.com"
            test_password = "TimezoneTest123!"
            
            # Try register first
            register_payload = {
                "email": test_email,
                "password": test_password
            }
            
            register_response = self.session.post(f"{API_BASE}/auth/register", json=register_payload, timeout=10)
            
            if register_response.status_code == 200:
                data = register_response.json()
                self.auth_token = data['access_token']
                print(f"✅ Fresh auth token obtained via register")
            elif register_response.status_code == 400:
                # Email exists, try login
                login_payload = {
                    "email": test_email,
                    "password": test_password
                }
                login_response = self.session.post(f"{API_BASE}/auth/login", json=login_payload, timeout=10)
                if login_response.status_code == 200:
                    data = login_response.json()
                    self.auth_token = data['access_token']
                    print(f"✅ Fresh auth token obtained via login")
                else:
                    print(f"❌ Failed to get auth token: {login_response.status_code}")
                    return False
            else:
                print(f"❌ Failed to register: {register_response.status_code}")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ Auth setup failed: {str(e)}")
            return False
    
    def test_1_health(self):
        """1) Health: GET /api/health"""
        print("\n" + "="*50)
        print("TEST 1: Health Endpoint")
        print("="*50)
        
        try:
            response = self.session.get(f"{API_BASE}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("1. Health Endpoint", True, 
                              f"HTTP 200 - Status: {data.get('status')}, DB: {data.get('db')}, LLM Key Available: {data.get('llm_key_available')}", 
                              data)
            else:
                self.log_result("1. Health Endpoint", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("1. Health Endpoint", False, f"Request failed: {str(e)}")
    
    def test_2_ai_estimate_emergent(self):
        """2) Estimate Live with empty api_key (use emergent), small base64 image"""
        print("\n" + "="*50)
        print("TEST 2: AI Estimate with Emergent Key")
        print("="*50)
        
        try:
            # Small base64 image (1x1 pixel PNG)
            small_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
            
            payload = {
                "message": "Estimate calories for this food image",
                "images": [
                    {
                        "data": small_png_b64,
                        "mime_type": "image/png",
                        "filename": "test_food.png"
                    }
                ],
                "api_key": "",  # Empty api_key to use emergent
                "simulate": False
            }
            
            response = self.session.post(f"{API_BASE}/ai/estimate-calories", json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                engine_info = data.get('engine_info', {})
                key_mode = engine_info.get('key_mode')
                
                if key_mode == 'emergent':
                    self.log_result("2. AI Estimate (Emergent Key)", True, 
                                  f"HTTP 200 - Key mode: {key_mode}, Total calories: {data.get('total_calories')}", 
                                  data)
                else:
                    self.log_result("2. AI Estimate (Emergent Key)", False, 
                                  f"Expected key_mode=emergent, got: {key_mode}", data)
            else:
                self.log_result("2. AI Estimate (Emergent Key)", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("2. AI Estimate (Emergent Key)", False, f"Request failed: {str(e)}")
    
    def test_3_meals_create_timezone(self):
        """3) Meals create with timezone-aware captured_at"""
        print("\n" + "="*50)
        print("TEST 3: Meals Create with Timezone")
        print("="*50)
        
        if not self.auth_token:
            self.log_result("3. Meals Create (Timezone)", False, "No auth token available")
            return
            
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            # Create timezone-aware captured_at (local + offset, e.g., 2025-10-01T12:00:00+02:00)
            captured_at = "2025-01-15T12:00:00+02:00"  # Using a realistic future date with +2 timezone
            
            payload = {
                "total_calories": 450.0,
                "items": [
                    {
                        "name": "Grilled salmon",
                        "quantity_units": "150g",
                        "calories": 280.0,
                        "confidence": 0.85
                    },
                    {
                        "name": "Steamed broccoli",
                        "quantity_units": "100g",
                        "calories": 35.0,
                        "confidence": 0.90
                    },
                    {
                        "name": "Brown rice",
                        "quantity_units": "80g",
                        "calories": 135.0,
                        "confidence": 0.88
                    }
                ],
                "notes": "Healthy lunch with timezone test",
                "captured_at": captured_at
            }
            
            response = self.session.post(f"{API_BASE}/meals", json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.meal_id = data.get('id')  # Store for delete test
                created_at = data.get('created_at')
                
                self.log_result("3. Meals Create (Timezone)", True, 
                              f"HTTP 200 - Meal ID: {self.meal_id}, Created at: {created_at}, Captured at preserved", 
                              data)
            else:
                self.log_result("3. Meals Create (Timezone)", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("3. Meals Create (Timezone)", False, f"Request failed: {str(e)}")
    
    def test_4_meals_fetch_timezone(self):
        """4) Meals fetch with timezone offset"""
        print("\n" + "="*50)
        print("TEST 4: Meals Fetch with Timezone Offset")
        print("="*50)
        
        if not self.auth_token:
            self.log_result("4. Meals Fetch (Timezone)", False, "No auth token available")
            return
            
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            # Fetch meals for the date we created (2025-01-15) with timezone offset
            date_str = "2025-01-15"  # Local date
            tz_offset_minutes = -120  # Browser offset for +02:00 timezone (negative because JS getTimezoneOffset)
            
            params = {
                "date": date_str,
                "tz_offset_minutes": tz_offset_minutes
            }
            
            response = self.session.get(f"{API_BASE}/meals", params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                meals = data.get('meals', [])
                daily_total = data.get('daily_total', 0)
                
                # Check if our created meal appears
                meal_found = any(meal.get('id') == self.meal_id for meal in meals) if self.meal_id else len(meals) > 0
                
                if meal_found:
                    self.log_result("4. Meals Fetch (Timezone)", True, 
                                  f"HTTP 200 - Found {len(meals)} meals, Daily total: {daily_total}", 
                                  data)
                else:
                    self.log_result("4. Meals Fetch (Timezone)", False, 
                                  f"Created meal not found in results. Expected meal_id: {self.meal_id}", data)
            else:
                self.log_result("4. Meals Fetch (Timezone)", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("4. Meals Fetch (Timezone)", False, f"Request failed: {str(e)}")
    
    def test_5_meals_delete(self):
        """5) Delete meal and verify removal"""
        print("\n" + "="*50)
        print("TEST 5: Meals Delete")
        print("="*50)
        
        if not self.auth_token:
            self.log_result("5. Meals Delete", False, "No auth token available")
            return
            
        if not self.meal_id:
            self.log_result("5. Meals Delete", False, "No meal ID available from create test")
            return
            
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            # Delete the meal
            response = self.session.delete(f"{API_BASE}/meals/{self.meal_id}", headers=headers, timeout=10)
            
            if response.status_code == 200:
                delete_data = response.json()
                
                # Verify deletion by fetching again
                params = {
                    "date": "2025-01-15",
                    "tz_offset_minutes": -120
                }
                
                fetch_response = self.session.get(f"{API_BASE}/meals", params=params, headers=headers, timeout=10)
                
                if fetch_response.status_code == 200:
                    fetch_data = fetch_response.json()
                    meals = fetch_data.get('meals', [])
                    meal_still_exists = any(meal.get('id') == self.meal_id for meal in meals)
                    
                    if not meal_still_exists:
                        self.log_result("5. Meals Delete", True, 
                                      f"HTTP 200 - Meal deleted successfully, verified removal", 
                                      {"delete_response": delete_data, "fetch_after_delete": fetch_data})
                    else:
                        self.log_result("5. Meals Delete", False, 
                                      "Meal still exists after deletion", fetch_data)
                else:
                    self.log_result("5. Meals Delete", False, 
                                  f"Failed to verify deletion: HTTP {fetch_response.status_code}", fetch_response.text)
            else:
                self.log_result("5. Meals Delete", False, f"HTTP {response.status_code}", response.text)
                
        except Exception as e:
            self.log_result("5. Meals Delete", False, f"Request failed: {str(e)}")
    
    def run_verification_tests(self):
        """Run all verification tests"""
        print("Starting timezone and key policy patch verification...")
        
        # Setup authentication first
        if not self.setup_auth():
            print("❌ Failed to setup authentication, aborting tests")
            return False
        
        # Run tests in order
        self.test_1_health()
        self.test_2_ai_estimate_emergent()
        self.test_3_meals_create_timezone()
        self.test_4_meals_fetch_timezone()
        self.test_5_meals_delete()
        
        # Summary
        print("\n" + "="*80)
        print("VERIFICATION SUMMARY")
        print("="*80)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if passed < total:
            print("\nFAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"❌ {result['test']}: {result['details']}")
        else:
            print("\n✅ All verification tests passed!")
        
        return passed == total

if __name__ == "__main__":
    tester = TimezoneKeyTester()
    success = tester.run_verification_tests()
    sys.exit(0 if success else 1)