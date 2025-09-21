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

if __name__ == "__main__":
    tester = BackendTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)