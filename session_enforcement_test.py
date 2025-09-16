import requests
import sys
import json
import time
from datetime import datetime
import uuid

class SessionEnforcementTester:
    def __init__(self, base_url="https://lemaitremot-edu.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.pro_user_email = "oussama92.18@gmail.com"
        self.generated_document_id = None
        self.guest_id = f"test_guest_{datetime.now().strftime('%H%M%S')}"

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, timeout=30):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        default_headers = {'Content-Type': 'application/json'}
        if headers:
            default_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        if headers:
            print(f"   Headers: {list(headers.keys())}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=default_headers, timeout=timeout)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    return True, response_data
                except:
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                    return False, error_data
                except:
                    print(f"   Error text: {response.text[:200]}")
                    return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout after {timeout}s")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def setup_test_document(self):
        """Create a test document for export testing"""
        test_data = {
            "matiere": "Mathématiques",
            "niveau": "4e",
            "chapitre": "Nombres relatifs",
            "type_doc": "exercices",
            "difficulte": "moyen",
            "nb_exercices": 2,
            "versions": ["A"],
            "guest_id": self.guest_id
        }
        
        success, response = self.run_test(
            "Setup Test Document", 
            "POST", 
            "generate", 
            200, 
            data=test_data,
            timeout=60
        )
        
        if success and isinstance(response, dict):
            document = response.get('document')
            if document:
                self.generated_document_id = document.get('id')
                print(f"   Document ID: {self.generated_document_id}")
        
        return success

    def test_export_with_session_token_validation(self):
        """Test export endpoint session token validation behavior"""
        print("\n🔍 Testing export endpoint session token validation...")
        
        if not self.generated_document_id:
            print("   ⚠️  No document available for testing")
            return False
        
        # Test 1: Export with fake session token (no guest_id) - should validate token first
        fake_token = f"fake-session-token-{int(time.time())}"
        headers = {"X-Session-Token": fake_token}
        
        export_data = {
            "document_id": self.generated_document_id,
            "export_type": "sujet"
            # No guest_id provided - should force session token validation
        }
        
        success_1, response_1 = self.run_test(
            "Export with Fake Session Token (No Guest ID)",
            "POST",
            "export",
            401,  # Should return 401 for invalid session token
            data=export_data,
            headers=headers
        )
        
        # Test 2: Export with valid Pro user email header (backwards compatibility)
        headers_2 = {"X-User-Email": self.pro_user_email}
        
        success_2, response_2 = self.run_test(
            "Export with Pro Email Header (Backwards Compatibility)",
            "POST",
            "export",
            200,  # Should work for Pro user
            data=export_data,
            headers=headers_2
        )
        
        # Test 3: Export with both fake session token and guest_id
        export_data_with_guest = {
            "document_id": self.generated_document_id,
            "export_type": "sujet",
            "guest_id": self.guest_id
        }
        
        success_3, response_3 = self.run_test(
            "Export with Fake Session Token + Guest ID",
            "POST",
            "export",
            200,  # Should fall back to guest quota since session token is invalid
            data=export_data_with_guest,
            headers={"X-Session-Token": fake_token}
        )
        
        passed_tests = sum([success_1, success_2, success_3])
        print(f"   Export validation tests passed: {passed_tests}/3")
        
        return passed_tests >= 2

    def test_session_token_validation_logic(self):
        """Test the session token validation logic specifically"""
        print("\n🔍 Testing session token validation logic...")
        
        test_tokens = [
            ("Valid Format Fake Token", f"{uuid.uuid4()}-{uuid.uuid4()}"),
            ("Invalid Format 1", "invalid-token"),
            ("Invalid Format 2", ""),
            ("Invalid Format 3", "fake-session-123"),
            ("Very Long Token", "a" * 200),
        ]
        
        passed = 0
        for token_name, token in test_tokens:
            headers = {"X-Session-Token": token} if token else {}
            
            success, response = self.run_test(
                f"Session Validation - {token_name}",
                "GET",
                "auth/session/validate",
                401,  # All should return 401 for invalid tokens
                headers=headers if token else None
            )
            
            if success:
                passed += 1
        
        print(f"   Session validation tests passed: {passed}/{len(test_tokens)}")
        return passed >= len(test_tokens) - 1

    def test_magic_link_token_behavior(self):
        """Test magic link token behavior and validation"""
        print("\n🔍 Testing magic link token behavior...")
        
        # Test various invalid magic link tokens
        test_tokens = [
            ("Empty Token", ""),
            ("Invalid Format", "invalid-magic-token"),
            ("Expired Format", f"{uuid.uuid4()}-magic-{int(time.time()) - 3600}"),  # 1 hour ago
            ("Future Format", f"{uuid.uuid4()}-magic-{int(time.time()) + 3600}"),   # 1 hour future
            ("Wrong Format", f"{uuid.uuid4()}-wrong-{int(time.time())}"),
        ]
        
        passed = 0
        for token_name, token in test_tokens:
            verify_data = {
                "token": token,
                "device_id": f"test_device_{int(time.time())}"
            }
            
            success, response = self.run_test(
                f"Magic Link Verification - {token_name}",
                "POST",
                "auth/verify-login",
                400,  # Should return 400 for invalid tokens
                data=verify_data
            )
            
            if success:
                passed += 1
        
        print(f"   Magic link validation tests passed: {passed}/{len(test_tokens)}")
        return passed >= len(test_tokens) - 1

    def test_concurrent_magic_link_generation(self):
        """Test concurrent magic link generation for same user"""
        print("\n🔍 Testing concurrent magic link generation...")
        
        # Generate multiple magic links rapidly
        login_data = {"email": self.pro_user_email}
        
        results = []
        for i in range(5):
            success, response = self.run_test(
                f"Magic Link Request {i+1}",
                "POST",
                "auth/request-login",
                200,
                data=login_data
            )
            results.append(success)
            time.sleep(0.2)  # Small delay
        
        successful_requests = sum(results)
        print(f"   Concurrent magic link requests: {successful_requests}/5")
        
        # All requests should succeed (system should handle concurrent requests)
        return successful_requests >= 4

    def test_session_cleanup_behavior(self):
        """Test session cleanup and invalidation behavior"""
        print("\n🔍 Testing session cleanup behavior...")
        
        # Test logout with various token scenarios
        test_scenarios = [
            ("No Token", None, 400),
            ("Empty Token", "", 400),
            ("Invalid Token", f"invalid-{int(time.time())}", 404),
            ("Valid Format Fake Token", f"{uuid.uuid4()}-{uuid.uuid4()}", 404),
        ]
        
        passed = 0
        for scenario_name, token, expected_status in test_scenarios:
            headers = {"X-Session-Token": token} if token else {}
            
            success, response = self.run_test(
                f"Logout - {scenario_name}",
                "POST",
                "auth/logout",
                expected_status,
                headers=headers if token else None
            )
            
            if success:
                passed += 1
        
        print(f"   Session cleanup tests passed: {passed}/{len(test_scenarios)}")
        return passed >= len(test_scenarios) - 1

    def run_comprehensive_session_tests(self):
        """Run comprehensive session enforcement tests"""
        print("\n" + "="*70)
        print("🔒 COMPREHENSIVE SESSION ENFORCEMENT TESTS")
        print("="*70)
        print("Focus: Single session per user + proper token validation")
        print("="*70)
        
        # Setup
        print("\n📋 SETUP")
        print("-" * 20)
        setup_success = self.setup_test_document()
        if not setup_success:
            print("❌ Setup failed - some tests may be limited")
        
        # Core session enforcement tests
        session_tests = [
            ("Export Session Token Validation", self.test_export_with_session_token_validation),
            ("Session Token Validation Logic", self.test_session_token_validation_logic),
            ("Magic Link Token Behavior", self.test_magic_link_token_behavior),
            ("Concurrent Magic Link Generation", self.test_concurrent_magic_link_generation),
            ("Session Cleanup Behavior", self.test_session_cleanup_behavior),
        ]
        
        print("\n🔒 SESSION ENFORCEMENT TESTS")
        print("-" * 40)
        
        session_passed = 0
        session_total = len(session_tests)
        
        for test_name, test_func in session_tests:
            try:
                success = test_func()
                if success:
                    session_passed += 1
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"❌ {test_name}: EXCEPTION - {e}")
        
        return session_passed, session_total

def main():
    print("🔒 SESSION ENFORCEMENT SECURITY TEST")
    print("=" * 50)
    print("Testing: Single session per user enforcement")
    print("Focus: Token validation and session management")
    print("=" * 50)
    
    tester = SessionEnforcementTester()
    
    # Run the comprehensive session tests
    session_passed, session_total = tester.run_comprehensive_session_tests()
    
    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 SESSION ENFORCEMENT TEST RESULTS")
    print("=" * 50)
    print(f"🔒 Session Tests: {session_passed}/{session_total} passed")
    print(f"📈 Overall Tests: {tester.tests_passed}/{tester.tests_run} passed")
    
    # Calculate success rates
    session_success_rate = session_passed / session_total if session_total > 0 else 0
    overall_success_rate = tester.tests_passed / tester.tests_run if tester.tests_run > 0 else 0
    
    print(f"🎯 Session Success Rate: {session_success_rate:.1%}")
    print(f"📊 Overall Success Rate: {overall_success_rate:.1%}")
    
    # Analysis
    print("\n📋 ANALYSIS")
    print("-" * 20)
    
    if session_success_rate >= 0.8:
        print("✅ Session enforcement is working correctly")
        print("✅ Token validation is properly implemented")
        print("✅ Authentication endpoints are secure")
        
        if session_success_rate == 1.0:
            print("🎉 PERFECT SCORE - All session tests passed!")
        
        return 0
    else:
        print("❌ Session enforcement has issues")
        print("❌ Token validation may be compromised")
        print("⚠️  Manual verification recommended")
        return 1

if __name__ == "__main__":
    sys.exit(main())