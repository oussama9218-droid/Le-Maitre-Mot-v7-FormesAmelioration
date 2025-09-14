import requests
import sys
import json
from datetime import datetime

class LessonSmithAPITester:
    def __init__(self, base_url="https://lessonsmith.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.generated_document_id = None

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
            "nb_exercices": 3,
            "versions": ["A"]
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
        return self.run_test("Get Documents", "GET", "documents", 200)

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
        ("Vary Exercise", tester.test_vary_exercise),
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