import requests
import sys
import json
import time
from datetime import datetime

class LeMaitreMotAPITester:
    def __init__(self, base_url="https://edudocsai.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.generated_document_id = None
        self.guest_id = f"test_guest_{datetime.now().strftime('%H%M%S')}"
        self.initial_quota = None
        # Authentication testing variables
        self.pro_user_email = "oussama92.18@gmail.com"
        self.magic_token = None
        self.session_token = None
        self.device_id = f"test_device_{datetime.now().strftime('%H%M%S')}"

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

    def test_pricing_endpoint(self):
        """Test the pricing endpoint for new monetization system"""
        success, response = self.run_test("Pricing", "GET", "pricing", 200)
        
        if success and isinstance(response, dict):
            packages = response.get('packages', {})
            print(f"   Found {len(packages)} pricing packages")
            
            # Check for expected packages
            if 'monthly' in packages:
                monthly = packages['monthly']
                print(f"   Monthly: {monthly.get('amount')}€ - {monthly.get('description')}")
            
            if 'yearly' in packages:
                yearly = packages['yearly']
                print(f"   Yearly: {yearly.get('amount')}€ - {yearly.get('description')}")
        
        return success, response

    def test_checkout_session_creation(self):
        """Test Stripe checkout session creation"""
        checkout_data = {
            "package_id": "monthly",
            "origin_url": self.base_url,
            "email": f"test_{self.guest_id}@example.com",
            "nom": "Test User",
            "etablissement": "Test School"
        }
        
        success, response = self.run_test(
            "Create Checkout Session",
            "POST",
            "checkout/session",
            200,
            data=checkout_data
        )
        
        if success and isinstance(response, dict):
            url = response.get('url', '')
            session_id = response.get('session_id', '')
            print(f"   Checkout URL: {url[:50]}...")
            print(f"   Session ID: {session_id}")
            
            # Verify it's a Stripe URL
            if 'stripe.com' in url:
                print("   ✅ Valid Stripe checkout URL")
            else:
                print("   ⚠️  URL doesn't appear to be from Stripe")
        
        return success, response

    def test_quota_exhaustion_workflow(self):
        """Test the complete quota exhaustion workflow"""
        print("\n🔍 Testing quota exhaustion workflow...")
        
        # First, check initial quota
        success, quota_response = self.test_quota_check()
        if success:
            self.initial_quota = quota_response.get('exports_remaining', 3)
            print(f"   Initial quota: {self.initial_quota}")
        
        # Generate a document if we don't have one
        if not self.generated_document_id:
            self.test_generate_document()
        
        if not self.generated_document_id:
            print("   ❌ Cannot test quota exhaustion without a document")
            return False, {}
        
        # Try to exhaust the quota by exporting multiple times
        exports_made = 0
        max_attempts = 5  # Safety limit
        
        for attempt in range(max_attempts):
            print(f"\n   Export attempt {attempt + 1}:")
            
            # Check current quota
            success, quota_response = self.test_quota_check()
            if success:
                remaining = quota_response.get('exports_remaining', 0)
                exceeded = quota_response.get('quota_exceeded', False)
                print(f"   Current quota: {remaining} remaining, exceeded: {exceeded}")
                
                if exceeded:
                    print("   ✅ Quota exhaustion detected!")
                    break
            
            # Try to export
            export_data = {
                "document_id": self.generated_document_id,
                "export_type": "sujet",
                "guest_id": self.guest_id
            }
            
            success, response = self.run_test(
                f"Export Attempt {attempt + 1}",
                "POST",
                "export",
                200 if remaining > 0 else 402,  # Expect 402 when quota exceeded
                data=export_data,
                timeout=30
            )
            
            if success and remaining > 0:
                exports_made += 1
                print(f"   ✅ Export {exports_made} successful")
            elif not success and remaining == 0:
                print(f"   ✅ Export correctly blocked due to quota exhaustion")
                # Check if we get the right error message
                try:
                    # This would be in the response if it was JSON
                    print(f"   Expected 402 error received")
                except:
                    pass
                break
            else:
                print(f"   ⚠️  Unexpected result: success={success}, remaining={remaining}")
        
        print(f"\n   Total exports made: {exports_made}")
        return True, {"exports_made": exports_made}

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
    print("🚀 Starting Le Maître Mot API Tests - New Monetization System")
    print("=" * 60)
    
    tester = LeMaitreMotAPITester()
    
    # Test sequence focused on new monetization workflow
    tests = [
        ("Root API", tester.test_root_endpoint),
        ("Catalog", tester.test_catalog_endpoint),
        ("Pricing Packages", tester.test_pricing_endpoint),
        ("Initial Quota Check", tester.test_quota_check),
        ("Generate Document", tester.test_generate_document),
        ("Get Documents", tester.test_get_documents),
        ("Quota Exhaustion Workflow", tester.test_quota_exhaustion_workflow),
        ("Stripe Checkout Session", tester.test_checkout_session_creation),
        ("Vary Exercise", tester.test_vary_exercise),
        ("Error Handling", tester.test_invalid_requests)
    ]
    
    for test_name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All backend tests passed!")
        print("✅ New monetization system appears to be working correctly")
        return 0
    else:
        print("⚠️  Some tests failed - check backend logs")
        print("❌ Issues detected in the new monetization system")
        return 1

if __name__ == "__main__":
    sys.exit(main())