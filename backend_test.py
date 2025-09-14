import requests
import sys
import json
from datetime import datetime

class LeMaitreMotAPITester:
    def __init__(self, base_url="https://lessonsmith.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.generated_document_id = None
        self.guest_id = f"test_guest_{datetime.now().strftime('%H%M%S')}"
        self.initial_quota = None

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

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

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test("Root API", "GET", "", 200)

    def test_catalog_endpoint(self):
        """Test the catalog endpoint"""
        success, response = self.run_test("Catalog", "GET", "catalog", 200)
        if success and isinstance(response, dict):
            catalog = response.get('catalog', [])
            if catalog:
                print(f"   Found {len(catalog)} subjects")
                for subject in catalog:
                    if subject.get('name') == 'Mathématiques':
                        levels = subject.get('levels', [])
                        print(f"   Mathématiques has {len(levels)} levels")
                        for level in levels:
                            chapters = level.get('chapters', [])
                            print(f"     {level.get('name')}: {len(chapters)} chapters")
        return success, response

    def test_generate_document(self):
        """Test document generation with French mathematics curriculum"""
        test_data = {
            "matiere": "Mathématiques",
            "niveau": "4e",
            "chapitre": "Nombres relatifs",
            "type_doc": "exercices",
            "difficulte": "moyen",
            "nb_exercices": 4,
            "versions": ["A"],
            "guest_id": self.guest_id
        }
        
        print(f"   Generating document with: {test_data}")
        success, response = self.run_test(
            "Generate Document", 
            "POST", 
            "generate", 
            200, 
            data=test_data,
            timeout=60  # AI generation can take time
        )
        
        if success and isinstance(response, dict):
            document = response.get('document')
            if document:
                self.generated_document_id = document.get('id')
                exercises = document.get('exercises', [])
                print(f"   Generated document with {len(exercises)} exercises")
                print(f"   Document ID: {self.generated_document_id}")
                
                # Check if exercises are in French
                for i, exercise in enumerate(exercises[:2]):  # Check first 2 exercises
                    enonce = exercise.get('enonce', '')
                    if enonce:
                        print(f"   Exercise {i+1} preview: {enonce[:100]}...")
                        # Check for French mathematical terms
                        french_terms = ['exercice', 'calculer', 'résoudre', 'nombre', 'relatif']
                        has_french = any(term in enonce.lower() for term in french_terms)
                        if has_french:
                            print(f"   ✅ Exercise {i+1} appears to be in French")
                        else:
                            print(f"   ⚠️  Exercise {i+1} may not be in French")
        
        return success, response

    def test_get_documents(self):
        """Test getting user documents"""
        return self.run_test("Get Documents", "GET", f"documents?guest_id={self.guest_id}", 200)

    def test_quota_check(self):
        """Test quota checking for guest users"""
        success, response = self.run_test("Quota Check", "GET", f"quota/check?guest_id={self.guest_id}", 200)
        
        if success and isinstance(response, dict):
            exports_remaining = response.get('exports_remaining', 0)
            max_exports = response.get('max_exports', 0)
            quota_exceeded = response.get('quota_exceeded', False)
            print(f"   Quota status: {exports_remaining}/{max_exports} remaining, exceeded: {quota_exceeded}")
        
        return success, response

    def test_export_pdf_sujet(self):
        """Test PDF export for sujet"""
        if not self.generated_document_id:
            print("⚠️  Skipping PDF export test - no document generated")
            return False, {}
        
        export_data = {
            "document_id": self.generated_document_id,
            "export_type": "sujet",
            "guest_id": self.guest_id
        }
        
        print(f"   Exporting sujet PDF for document: {self.generated_document_id}")
        success, response = self.run_test(
            "Export Sujet PDF",
            "POST",
            "export",
            200,
            data=export_data,
            timeout=30
        )
        
        return success, response

    def test_export_pdf_corrige(self):
        """Test PDF export for corrigé"""
        if not self.generated_document_id:
            print("⚠️  Skipping PDF export test - no document generated")
            return False, {}
        
        export_data = {
            "document_id": self.generated_document_id,
            "export_type": "corrige",
            "guest_id": self.guest_id
        }
        
        print(f"   Exporting corrigé PDF for document: {self.generated_document_id}")
        success, response = self.run_test(
            "Export Corrigé PDF",
            "POST",
            "export",
            200,
            data=export_data,
            timeout=30
        )
        
        return success, response

    def test_signup_request(self):
        """Test signup request functionality"""
        signup_data = {
            "email": f"test_{self.guest_id}@example.com",
            "nom": "Test User",
            "etablissement": "Test School"
        }
        
        success, response = self.run_test(
            "Signup Request",
            "POST",
            "auth/signup",
            200,
            data=signup_data
        )
        
        if success and isinstance(response, dict):
            message = response.get('message', '')
            email = response.get('email', '')
            print(f"   Signup response: {message}")
            print(f"   Email: {email}")
        
        return success, response

    def test_vary_exercise(self):
        """Test exercise variation functionality"""
        if not self.generated_document_id:
            print("⚠️  Skipping exercise variation test - no document generated")
            return False, {}
        
        success, response = self.run_test(
            "Vary Exercise",
            "POST",
            f"documents/{self.generated_document_id}/vary/0",
            200,
            timeout=60
        )
        
        if success and isinstance(response, dict):
            exercise = response.get('exercise')
            if exercise:
                enonce = exercise.get('enonce', '')
                print(f"   Varied exercise preview: {enonce[:100]}...")
        
        return success, response

    def test_invalid_requests(self):
        """Test error handling with invalid requests"""
        print("\n🔍 Testing error handling...")
        
        # Test invalid subject
        invalid_data = {
            "matiere": "InvalidSubject",
            "niveau": "4e",
            "chapitre": "Test",
            "type_doc": "exercices",
            "difficulte": "moyen",
            "nb_exercices": 3
        }
        
        success, _ = self.run_test(
            "Invalid Subject",
            "POST",
            "generate",
            400,  # Expecting error
            data=invalid_data
        )
        
        # For error cases, success means we got the expected error status
        return success

def main():
    print("🚀 Starting LessonSmith API Tests")
    print("=" * 50)
    
    tester = LessonSmithAPITester()
    
    # Test sequence
    tests = [
        ("Root API", tester.test_root_endpoint),
        ("Catalog", tester.test_catalog_endpoint),
        ("Generate Document", tester.test_generate_document),
        ("Get Documents", tester.test_get_documents),
        ("Quota Check", tester.test_quota_check),
        ("Export Sujet PDF", tester.test_export_pdf_sujet),
        ("Export Corrigé PDF", tester.test_export_pdf_corrige),
        ("Vary Exercise", tester.test_vary_exercise),
        ("Signup Request", tester.test_signup_request),
        ("Error Handling", tester.test_invalid_requests)
    ]
    
    for test_name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed - check backend logs")
        return 1

if __name__ == "__main__":
    sys.exit(main())