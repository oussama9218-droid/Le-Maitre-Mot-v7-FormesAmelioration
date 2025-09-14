import requests
import sys
import json
from datetime import datetime

class AuthenticationTester:
    def __init__(self, base_url="https://lessonsmith.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.magic_token = "df43f9ee-649d-495b-9c9c-6bac1ce27097"
        self.auth_token = None
        self.user_info = None
        self.tests_run = 0
        self.tests_passed = 0
        self.generated_document_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, timeout=30):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        request_headers = {'Content-Type': 'application/json'}
        if headers:
            request_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        if headers:
            print(f"   Headers: {headers}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=request_headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=request_headers, timeout=timeout)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 500:
                        print(f"   Response keys: {list(response_data.keys())}")
                    return True, response_data
                except:
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error text: {response.text[:200]}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout after {timeout}s")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_magic_link_verification(self):
        """Test magic link verification with the provided token"""
        print(f"   Using magic token: {self.magic_token}")
        
        success, response = self.run_test(
            "Magic Link Verification",
            "GET",
            f"auth/verify?token={self.magic_token}",
            200
        )
        
        if success and isinstance(response, dict):
            self.auth_token = response.get('token')
            self.user_info = response.get('user')
            print(f"   Auth token received: {self.auth_token}")
            print(f"   User info: {self.user_info}")
            
            if self.user_info:
                print(f"   User email: {self.user_info.get('email')}")
                print(f"   Account type: {self.user_info.get('account_type')}")
        
        return success, response

    def test_authenticated_document_generation(self):
        """Test document generation with authentication"""
        if not self.auth_token:
            print("⚠️  Skipping authenticated generation - no auth token")
            return False, {}
        
        test_data = {
            "matiere": "Mathématiques",
            "niveau": "6e",
            "chapitre": "Nombres entiers et décimaux",
            "type_doc": "exercices",
            "difficulte": "moyen",
            "nb_exercices": 3,
            "versions": ["A"]
        }
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        print(f"   Generating document with auth token")
        success, response = self.run_test(
            "Authenticated Document Generation",
            "POST",
            "generate",
            200,
            data=test_data,
            headers=headers,
            timeout=60
        )
        
        if success and isinstance(response, dict):
            document = response.get('document')
            if document:
                self.generated_document_id = document.get('id')
                exercises = document.get('exercises', [])
                print(f"   Generated document with {len(exercises)} exercises")
                print(f"   Document ID: {self.generated_document_id}")
                
                # Check exercises content
                for i, exercise in enumerate(exercises):
                    enonce = exercise.get('enonce', '')
                    if enonce:
                        print(f"   Exercise {i+1}: {enonce[:80]}...")
        
        return success, response

    def test_authenticated_export_sujet(self):
        """Test authenticated PDF export for sujet"""
        if not self.auth_token or not self.generated_document_id:
            print("⚠️  Skipping authenticated export - missing auth token or document")
            return False, {}
        
        export_data = {
            "document_id": self.generated_document_id,
            "export_type": "sujet"
        }
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        print(f"   Exporting sujet PDF with authentication")
        print(f"   Document ID: {self.generated_document_id}")
        print(f"   Auth token: {self.auth_token}")
        
        success, response = self.run_test(
            "Authenticated Export Sujet PDF",
            "POST",
            "export",
            200,
            data=export_data,
            headers=headers,
            timeout=30
        )
        
        return success, response

    def test_authenticated_export_corrige(self):
        """Test authenticated PDF export for corrigé"""
        if not self.auth_token or not self.generated_document_id:
            print("⚠️  Skipping authenticated export - missing auth token or document")
            return False, {}
        
        export_data = {
            "document_id": self.generated_document_id,
            "export_type": "corrige"
        }
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        print(f"   Exporting corrigé PDF with authentication")
        
        success, response = self.run_test(
            "Authenticated Export Corrigé PDF",
            "POST",
            "export",
            200,
            data=export_data,
            headers=headers,
            timeout=30
        )
        
        return success, response

    def test_quota_unlimited_for_authenticated_user(self):
        """Verify that authenticated users have unlimited exports"""
        if not self.auth_token:
            print("⚠️  Skipping quota test - no auth token")
            return False, {}
        
        # For authenticated users, we should be able to export multiple times without quota issues
        # Let's try exporting the same document multiple times
        if not self.generated_document_id:
            print("⚠️  Skipping quota test - no document generated")
            return False, {}
        
        export_data = {
            "document_id": self.generated_document_id,
            "export_type": "sujet"
        }
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Try multiple exports to verify unlimited quota
        for i in range(3):
            print(f"   Attempting export #{i+1} to verify unlimited quota...")
            success, response = self.run_test(
                f"Unlimited Quota Test #{i+1}",
                "POST",
                "export",
                200,
                data=export_data,
                headers=headers,
                timeout=30
            )
            
            if not success:
                print(f"❌ Export #{i+1} failed - quota may not be unlimited")
                return False, {}
        
        print("✅ Multiple exports successful - unlimited quota confirmed")
        return True, {}

def main():
    print("🔐 Starting Authentication & Export Tests")
    print("=" * 60)
    
    tester = AuthenticationTester()
    
    # Test sequence focusing on authentication and export
    tests = [
        ("Magic Link Verification", tester.test_magic_link_verification),
        ("Authenticated Document Generation", tester.test_authenticated_document_generation),
        ("Authenticated Export Sujet", tester.test_authenticated_export_sujet),
        ("Authenticated Export Corrigé", tester.test_authenticated_export_corrige),
        ("Unlimited Quota Verification", tester.test_quota_unlimited_for_authenticated_user)
    ]
    
    for test_name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 Authentication Test Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All authentication tests passed!")
        print("✅ Magic link authentication working")
        print("✅ Authenticated PDF exports working")
        print("✅ Unlimited quota for authenticated users confirmed")
        return 0
    else:
        print("⚠️  Some authentication tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())