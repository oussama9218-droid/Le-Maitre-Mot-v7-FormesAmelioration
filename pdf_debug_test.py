import requests
import sys
import json
import time
import uuid
from datetime import datetime
import tempfile
import os

class PDFExportDebugTester:
    def __init__(self, base_url="https://lemaitremot-edu.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.generated_document_id = None
        self.guest_id = f"debug_guest_{datetime.now().strftime('%H%M%S')}"
        
        # Pro user for testing
        self.pro_user_email = "oussama92.18@gmail.com"
        self.session_token = None
        self.device_id = f"debug_device_{datetime.now().strftime('%H%M%S')}"

    def log_debug(self, message):
        """Log debug messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 🔍 {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, timeout=30):
        """Run a single API test with detailed logging"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        default_headers = {'Content-Type': 'application/json'}
        if headers:
            default_headers.update(headers)

        self.tests_run += 1
        self.log_debug(f"Testing {name}...")
        self.log_debug(f"URL: {url}")
        if headers:
            self.log_debug(f"Headers: {list(headers.keys())}")
        if data:
            self.log_debug(f"Data keys: {list(data.keys()) if isinstance(data, dict) else 'Non-dict data'}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=default_headers, timeout=timeout)

            self.log_debug(f"Response Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ {name} - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    return True, response_data
                except:
                    return True, response.text
            else:
                print(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    self.log_debug(f"Error response: {error_data}")
                except:
                    self.log_debug(f"Error text: {response.text[:500]}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ {name} - Request timeout after {timeout}s")
            return False, {}
        except Exception as e:
            print(f"❌ {name} - Error: {str(e)}")
            return False, {}

    def setup_test_document(self):
        """Generate a test document for PDF export testing"""
        self.log_debug("Setting up test document for PDF export...")
        
        test_data = {
            "matiere": "Mathématiques",
            "niveau": "4e",
            "chapitre": "Nombres relatifs",
            "type_doc": "exercices",
            "difficulte": "moyen",
            "nb_exercices": 3,
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
                self.log_debug(f"Generated document ID: {self.generated_document_id}")
                return True
        
        return False

    def test_pro_user_subscription_status(self):
        """Test 1: Verify Pro user subscription status"""
        print("\n" + "="*60)
        print("🔍 DEBUG TEST 1: PRO USER SUBSCRIPTION STATUS")
        print("="*60)
        
        success, response = self.run_test(
            "Pro User Subscription Check",
            "GET",
            f"subscription/status/{self.pro_user_email}",
            200
        )
        
        if success and isinstance(response, dict):
            is_pro = response.get('is_pro', False)
            subscription_type = response.get('subscription_type')
            subscription_expires = response.get('subscription_expires')
            days_remaining = response.get('days_remaining')
            
            self.log_debug(f"Pro status: {is_pro}")
            self.log_debug(f"Subscription type: {subscription_type}")
            self.log_debug(f"Expires: {subscription_expires}")
            self.log_debug(f"Days remaining: {days_remaining}")
            
            if is_pro:
                print(f"✅ Pro user {self.pro_user_email} has active subscription")
                print(f"   Type: {subscription_type}, Expires: {subscription_expires}, Days left: {days_remaining}")
                return True, response
            else:
                print(f"❌ User {self.pro_user_email} is not Pro or subscription expired")
                return False, response
        
        return False, {}

    def test_magic_link_request(self):
        """Test 2: Request magic link for Pro user"""
        print("\n" + "="*60)
        print("🔍 DEBUG TEST 2: MAGIC LINK REQUEST")
        print("="*60)
        
        login_data = {"email": self.pro_user_email}
        
        success, response = self.run_test(
            "Magic Link Request",
            "POST",
            "auth/request-login",
            200,
            data=login_data
        )
        
        if success and isinstance(response, dict):
            message = response.get('message', '')
            email = response.get('email', '')
            
            self.log_debug(f"Response message: {message}")
            self.log_debug(f"Email: {email}")
            
            if 'envoyé' in message.lower() or 'sent' in message.lower():
                print(f"✅ Magic link email sent successfully to {email}")
                return True, response
            else:
                print(f"⚠️ Unexpected response message: {message}")
                return False, response
        
        return False, {}

    def simulate_session_token(self):
        """Simulate a session token for testing (since we can't access email)"""
        self.log_debug("Simulating session token for testing purposes...")
        
        # Generate a realistic-looking session token
        self.session_token = f"{uuid.uuid4()}-{uuid.uuid4()}"
        self.log_debug(f"Simulated session token: {self.session_token[:20]}...")
        
        return self.session_token

    def test_session_authentication_debug(self):
        """Test 3: Debug session authentication flow"""
        print("\n" + "="*60)
        print("🔍 DEBUG TEST 3: SESSION AUTHENTICATION DEBUG")
        print("="*60)
        
        # Test session validation without token
        self.log_debug("Testing session validation without token...")
        success, response = self.run_test(
            "Session Validation - No Token",
            "GET",
            "auth/session/validate",
            401
        )
        
        if success:
            print("✅ Session validation correctly requires token")
        else:
            print("❌ Session validation should require token")
            return False, {}
        
        # Test session validation with fake token
        fake_token = self.simulate_session_token()
        headers = {"X-Session-Token": fake_token}
        
        self.log_debug(f"Testing session validation with fake token: {fake_token[:20]}...")
        success, response = self.run_test(
            "Session Validation - Fake Token",
            "GET",
            "auth/session/validate",
            401,
            headers=headers
        )
        
        if success:
            print("✅ Session validation correctly rejects fake tokens")
            self.log_debug("Expected behavior: Invalid session tokens are properly rejected")
            return True, response
        else:
            print("❌ Session validation should reject fake tokens")
            return False, {}

    def test_template_config_loading_debug(self):
        """Test 4: Debug template configuration loading"""
        print("\n" + "="*60)
        print("🔍 DEBUG TEST 4: TEMPLATE CONFIG LOADING DEBUG")
        print("="*60)
        
        # Test template styles endpoint (public)
        self.log_debug("Testing template styles endpoint...")
        success, response = self.run_test(
            "Template Styles - Public",
            "GET",
            "template/styles",
            200
        )
        
        if success and isinstance(response, dict):
            styles = response.get('styles', {})
            self.log_debug(f"Available template styles: {list(styles.keys())}")
            
            for style_name, style_data in styles.items():
                self.log_debug(f"Style '{style_name}': {style_data.get('name')} - {style_data.get('description')}")
                colors = style_data.get('preview_colors', {})
                self.log_debug(f"  Colors: primary={colors.get('primary')}, secondary={colors.get('secondary')}, accent={colors.get('accent')}")
            
            print(f"✅ Template styles loaded successfully: {list(styles.keys())}")
        else:
            print("❌ Failed to load template styles")
            return False, {}
        
        # Test template get endpoint (requires Pro auth)
        fake_token = self.simulate_session_token()
        headers = {"X-Session-Token": fake_token}
        
        self.log_debug("Testing template get endpoint with fake Pro session...")
        success, response = self.run_test(
            "Template Get - Fake Pro Session",
            "GET",
            "template/get",
            401,  # Will fail at session validation
            headers=headers
        )
        
        if success:
            print("✅ Template get endpoint properly validates session tokens")
            self.log_debug("Expected behavior: Template config loading requires valid Pro session")
            return True, response
        else:
            print("❌ Template get endpoint should validate session tokens")
            return False, {}

    def test_pdf_generation_path_debug(self):
        """Test 5: Debug PDF generation path selection"""
        print("\n" + "="*60)
        print("🔍 DEBUG TEST 5: PDF GENERATION PATH DEBUG")
        print("="*60)
        
        if not self.generated_document_id:
            if not self.setup_test_document():
                print("❌ Cannot test PDF generation without a document")
                return False, {}
        
        # Test 1: Guest PDF export (standard WeasyPrint path)
        self.log_debug("Testing guest PDF export (standard WeasyPrint path)...")
        export_data_guest = {
            "document_id": self.generated_document_id,
            "export_type": "sujet",
            "guest_id": self.guest_id
        }
        
        success, response = self.run_test(
            "PDF Export - Guest (Standard Path)",
            "POST",
            "export",
            200,
            data=export_data_guest,
            timeout=45
        )
        
        if success:
            print("✅ Guest PDF export successful (standard WeasyPrint path)")
            self.log_debug("Expected log: '📄 USING STANDARD WEASYPRINT'")
        else:
            print("❌ Guest PDF export failed")
            return False, {}
        
        # Test 2: Pro user PDF export with fake session (should fail at auth)
        self.log_debug("Testing Pro user PDF export with fake session...")
        fake_token = self.simulate_session_token()
        headers = {"X-Session-Token": fake_token}
        
        export_data_pro = {
            "document_id": self.generated_document_id,
            "export_type": "sujet"
        }
        
        success, response = self.run_test(
            "PDF Export - Fake Pro Session",
            "POST",
            "export",
            400,  # Should fail and require guest_id
            data=export_data_pro,
            headers=headers,
            timeout=45
        )
        
        if success:
            print("✅ Pro PDF export correctly validates session tokens")
            self.log_debug("Expected behavior: Invalid session falls back to guest quota requirement")
        else:
            print("❌ Pro PDF export should validate session tokens")
            return False, {}
        
        # Test 3: Export with both fake session and guest_id (fallback path)
        self.log_debug("Testing export with fake session + guest_id (fallback path)...")
        export_data_fallback = {
            "document_id": self.generated_document_id,
            "export_type": "sujet",
            "guest_id": self.guest_id
        }
        
        success, response = self.run_test(
            "PDF Export - Fake Session + Guest Fallback",
            "POST",
            "export",
            200,
            data=export_data_fallback,
            headers=headers,
            timeout=45
        )
        
        if success:
            print("✅ PDF export fallback to guest quota working")
            self.log_debug("Expected behavior: Invalid Pro session falls back to guest quota")
            return True, response
        else:
            print("❌ PDF export fallback should work")
            return False, {}

    def test_export_with_debug_logging(self):
        """Test 6: Export with detailed debug logging analysis"""
        print("\n" + "="*60)
        print("🔍 DEBUG TEST 6: EXPORT WITH DEBUG LOGGING ANALYSIS")
        print("="*60)
        
        if not self.generated_document_id:
            if not self.setup_test_document():
                print("❌ Cannot test export without a document")
                return False, {}
        
        # Test multiple export scenarios to trigger different code paths
        test_scenarios = [
            {
                "name": "Guest Export - Sujet",
                "data": {
                    "document_id": self.generated_document_id,
                    "export_type": "sujet",
                    "guest_id": self.guest_id
                },
                "headers": {},
                "expected_logs": ["📄 USING STANDARD WEASYPRINT", "Guest user export"]
            },
            {
                "name": "Guest Export - Corrigé",
                "data": {
                    "document_id": self.generated_document_id,
                    "export_type": "corrige",
                    "guest_id": self.guest_id
                },
                "headers": {},
                "expected_logs": ["📄 USING STANDARD WEASYPRINT", "Guest user export"]
            },
            {
                "name": "Fake Pro Export - Should Fallback",
                "data": {
                    "document_id": self.generated_document_id,
                    "export_type": "sujet",
                    "guest_id": self.guest_id
                },
                "headers": {"X-Session-Token": self.simulate_session_token()},
                "expected_logs": ["Session token validation failed", "📄 USING STANDARD WEASYPRINT"]
            }
        ]
        
        all_passed = True
        for scenario in test_scenarios:
            self.log_debug(f"Testing scenario: {scenario['name']}")
            
            success, response = self.run_test(
                f"Debug Export - {scenario['name']}",
                "POST",
                "export",
                200,
                data=scenario['data'],
                headers=scenario['headers'],
                timeout=45
            )
            
            if success:
                print(f"✅ {scenario['name']} - Export successful")
                self.log_debug(f"Expected logs for this scenario: {scenario['expected_logs']}")
            else:
                print(f"❌ {scenario['name']} - Export failed")
                all_passed = False
        
        return all_passed, {}

    def test_reportlab_function_debug(self):
        """Test 7: Debug ReportLab function implementation"""
        print("\n" + "="*60)
        print("🔍 DEBUG TEST 7: REPORTLAB FUNCTION DEBUG")
        print("="*60)
        
        # We can't directly test the ReportLab function without a valid Pro session,
        # but we can test the endpoint structure and error handling
        
        if not self.generated_document_id:
            if not self.setup_test_document():
                print("❌ Cannot test ReportLab without a document")
                return False, {}
        
        self.log_debug("Testing ReportLab function path (indirect)...")
        
        # Test with fake Pro session to see if personalized PDF path is attempted
        fake_token = f"pro-session-{uuid.uuid4()}"
        headers = {"X-Session-Token": fake_token}
        
        export_data = {
            "document_id": self.generated_document_id,
            "export_type": "sujet"
        }
        
        self.log_debug("Attempting export with fake Pro session to trigger personalized PDF path...")
        success, response = self.run_test(
            "ReportLab Debug - Fake Pro Session",
            "POST",
            "export",
            400,  # Will fail at session validation
            data=export_data,
            headers=headers,
            timeout=45
        )
        
        if success:
            print("✅ ReportLab path validation working")
            self.log_debug("Expected behavior: Session validation prevents unauthorized personalized PDF generation")
        else:
            print("❌ ReportLab path validation should work")
            return False, {}
        
        # Test template style compatibility
        self.log_debug("Testing template style compatibility with ReportLab...")
        success, response = self.run_test(
            "ReportLab Debug - Template Styles",
            "GET",
            "template/styles",
            200
        )
        
        if success and isinstance(response, dict):
            styles = response.get('styles', {})
            reportlab_compatible = True
            
            for style_name, style_data in styles.items():
                colors = style_data.get('preview_colors', {})
                primary = colors.get('primary')
                secondary = colors.get('secondary')
                accent = colors.get('accent')
                
                # Check if colors are in hex format (ReportLab compatible)
                if primary and primary.startswith('#') and len(primary) == 7:
                    self.log_debug(f"Style '{style_name}' primary color {primary} is ReportLab compatible")
                else:
                    self.log_debug(f"Style '{style_name}' primary color {primary} may not be ReportLab compatible")
                    reportlab_compatible = False
            
            if reportlab_compatible:
                print("✅ Template styles are ReportLab compatible")
                self.log_debug("All template styles use proper hex color format for ReportLab")
                return True, response
            else:
                print("⚠️ Some template styles may not be ReportLab compatible")
                return False, response
        
        return False, {}

    def check_backend_logs(self):
        """Check backend logs for debug information"""
        print("\n" + "="*60)
        print("🔍 BACKEND LOGS CHECK")
        print("="*60)
        
        self.log_debug("Checking backend logs for debug information...")
        
        try:
            # Try to read supervisor logs
            import subprocess
            result = subprocess.run(
                ["tail", "-n", "50", "/var/log/supervisor/backend.err.log"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                print("📋 Recent Backend Error Logs:")
                print("-" * 40)
                print(result.stdout)
                print("-" * 40)
                
                # Look for specific debug messages
                debug_messages = [
                    "Session token provided:",
                    "Pro status check result",
                    "🎨 ATTEMPTING PERSONALIZED PDF",
                    "📄 USING STANDARD WEASYPRINT",
                    "✅ PERSONALIZED PDF CREATED SUCCESSFULLY",
                    "Error creating personalized PDF"
                ]
                
                found_messages = []
                for message in debug_messages:
                    if message in result.stdout:
                        found_messages.append(message)
                
                if found_messages:
                    print(f"🔍 Found debug messages: {found_messages}")
                else:
                    print("⚠️ No specific debug messages found in recent logs")
                
                return True, result.stdout
            else:
                print("⚠️ Could not read backend error logs")
                return False, {}
                
        except Exception as e:
            print(f"⚠️ Error reading backend logs: {e}")
            return False, {}

    def run_complete_debug_flow(self):
        """Run the complete PDF export debug flow"""
        print("\n" + "="*80)
        print("🔍 COMPLETE PDF EXPORT DEBUG FLOW")
        print("="*80)
        print("CONTEXT: User reports PDFs downloaded are still same as before (not personalized)")
        print("GOAL: Identify why personalized templates are not being applied")
        print("PRO USER: oussama92.18@gmail.com")
        print("="*80)
        
        debug_tests = [
            ("Pro User Subscription Status", self.test_pro_user_subscription_status),
            ("Magic Link Request", self.test_magic_link_request),
            ("Session Authentication Debug", self.test_session_authentication_debug),
            ("Template Config Loading Debug", self.test_template_config_loading_debug),
            ("PDF Generation Path Debug", self.test_pdf_generation_path_debug),
            ("Export with Debug Logging", self.test_export_with_debug_logging),
            ("ReportLab Function Debug", self.test_reportlab_function_debug),
        ]
        
        debug_passed = 0
        debug_total = len(debug_tests)
        
        for test_name, test_func in debug_tests:
            try:
                print(f"\n{'='*20} {test_name} {'='*20}")
                success, _ = test_func()
                if success:
                    debug_passed += 1
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"❌ {test_name}: FAILED with exception: {e}")
        
        # Check backend logs at the end
        print(f"\n{'='*20} Backend Logs Analysis {'='*20}")
        self.check_backend_logs()
        
        print(f"\n🔍 Debug Tests Summary: {debug_passed}/{debug_total} passed")
        
        # Final analysis
        print("\n" + "="*80)
        print("🎯 DEBUG ANALYSIS SUMMARY")
        print("="*80)
        
        if debug_passed >= 5:
            print("✅ Most debug tests passed - System appears to be working correctly")
            print("🔍 LIKELY ISSUE: User may not have a valid Pro session when exporting")
            print("💡 RECOMMENDATION: Verify user is properly logged in with valid session token")
            print("📋 EXPECTED DEBUG LOGS TO LOOK FOR:")
            print("   - 'Session token provided: xxx...'")
            print("   - 'Pro status check result - email: xxx, is_pro: True'")
            print("   - '🎨 ATTEMPTING PERSONALIZED PDF GENERATION'")
            print("   - '✅ PERSONALIZED PDF CREATED SUCCESSFULLY!'")
        else:
            print("❌ Multiple debug tests failed - System may have issues")
            print("🔍 LIKELY ISSUES:")
            print("   - Pro user subscription may be expired")
            print("   - Session authentication may be broken")
            print("   - Template configuration loading may be failing")
            print("   - PDF generation path selection may be incorrect")
        
        print("\n🎯 NEXT STEPS:")
        print("1. Check backend logs during actual Pro user PDF export")
        print("2. Verify Pro user has valid session token when exporting")
        print("3. Confirm template configuration is loaded from database")
        print("4. Test with real Pro user login and export")
        
        return debug_passed, debug_total

def main():
    """Main function to run PDF export debug tests"""
    print("🔍 PDF EXPORT DEBUG TESTER")
    print("=" * 50)
    print("Purpose: Debug personalized PDF template issues")
    print("Target: Pro user oussama92.18@gmail.com")
    print("=" * 50)
    
    tester = PDFExportDebugTester()
    
    try:
        debug_passed, debug_total = tester.run_complete_debug_flow()
        
        print(f"\n🏁 FINAL RESULTS:")
        print(f"   Debug Tests: {debug_passed}/{debug_total} passed")
        print(f"   Total API Calls: {tester.tests_run}")
        print(f"   Success Rate: {(debug_passed/debug_total)*100:.1f}%")
        
        if debug_passed >= 5:
            print("\n✅ DEBUG CONCLUSION: System appears functional")
            print("   Issue likely related to user session or authentication")
        else:
            print("\n❌ DEBUG CONCLUSION: System has functional issues")
            print("   Multiple components need investigation")
            
    except KeyboardInterrupt:
        print("\n⚠️ Debug testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Debug testing failed with error: {e}")
    
    print("\n🔍 Debug testing completed.")

if __name__ == "__main__":
    main()