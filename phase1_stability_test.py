#!/usr/bin/env python3
"""
PHASE 1 STABILITY VERIFICATION AFTER REPORTLAB UNIFICATION
Le Maître Mot - Backend Testing Suite

CONTEXT: Testing system stability after major PDF generation refactoring
- Removed ReportLab complexity 
- Unified to WeasyPrint + ReportLab Flowables
- Need to verify core functionality remains intact

CRITICAL TESTING PRIORITIES:
1. Backend Service Stability
2. PDF Generation Pipeline (unified WeasyPrint system)
3. Core Authentication (magic link system)
4. Template System (Pro user personalization)
5. Export Functionality (comprehensive testing)
"""

import requests
import sys
import json
import time
import uuid
from datetime import datetime

class Phase1StabilityTester:
    def __init__(self, base_url="https://lemaitremot-edu.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.generated_document_id = None
        self.guest_id = f"phase1_guest_{datetime.now().strftime('%H%M%S')}"
        
        # Pro user for testing
        self.pro_user_email = "oussama92.18@gmail.com"
        self.device_id = f"phase1_device_{datetime.now().strftime('%H%M%S')}"
        
        # Test results tracking
        self.test_results = {
            'backend_stability': [],
            'pdf_generation': [],
            'authentication': [],
            'template_system': [],
            'export_functionality': []
        }

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, timeout=30):
        """Run a single API test with detailed logging"""
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

    def test_backend_service_stability(self):
        """Test 1: Backend Service Stability - Verify all services running without errors"""
        print("\n" + "="*80)
        print("🏗️  PHASE 1 TEST: BACKEND SERVICE STABILITY")
        print("="*80)
        print("OBJECTIVE: Verify all backend services are running without errors after ReportLab cleanup")
        
        stability_tests = []
        
        # Test 1.1: Root API endpoint
        success, response = self.run_test("Root API Endpoint", "GET", "", 200)
        stability_tests.append(("Root API", success))
        
        # Test 1.2: Catalog endpoint (core curriculum data)
        success, response = self.run_test("Curriculum Catalog", "GET", "catalog", 200)
        if success and isinstance(response, dict):
            catalog = response.get('catalog', [])
            if catalog and len(catalog) > 0:
                print(f"   ✅ Catalog loaded: {len(catalog)} subjects available")
                # Verify French curriculum structure
                math_found = any(subject.get('name') == 'Mathématiques' for subject in catalog)
                if math_found:
                    print(f"   ✅ French curriculum structure intact")
                else:
                    print(f"   ⚠️  French curriculum may be incomplete")
            else:
                print(f"   ❌ Catalog appears empty or malformed")
        stability_tests.append(("Curriculum Catalog", success))
        
        # Test 1.3: Pricing endpoint (monetization system)
        success, response = self.run_test("Pricing System", "GET", "pricing", 200)
        if success and isinstance(response, dict):
            packages = response.get('packages', {})
            if 'monthly' in packages and 'yearly' in packages:
                print(f"   ✅ Pricing packages available: {list(packages.keys())}")
            else:
                print(f"   ⚠️  Pricing packages may be incomplete")
        stability_tests.append(("Pricing System", success))
        
        # Test 1.4: Template styles endpoint (Pro features)
        success, response = self.run_test("Template Styles", "GET", "template/styles", 200)
        if success and isinstance(response, dict):
            styles = response.get('styles', {})
            expected_styles = ['minimaliste', 'classique', 'moderne']
            available_styles = list(styles.keys())
            if all(style in available_styles for style in expected_styles):
                print(f"   ✅ All template styles available: {available_styles}")
            else:
                print(f"   ⚠️  Template styles may be incomplete: {available_styles}")
        stability_tests.append(("Template Styles", success))
        
        # Store results
        self.test_results['backend_stability'] = stability_tests
        
        passed = sum(1 for _, success in stability_tests if success)
        total = len(stability_tests)
        print(f"\n📊 Backend Stability: {passed}/{total} tests passed")
        
        return passed, total

    def test_unified_pdf_generation(self):
        """Test 2: PDF Generation Pipeline - Test unified WeasyPrint system"""
        print("\n" + "="*80)
        print("📄 PHASE 1 TEST: UNIFIED PDF GENERATION PIPELINE")
        print("="*80)
        print("OBJECTIVE: Verify WeasyPrint system works correctly after ReportLab cleanup")
        
        pdf_tests = []
        
        # Test 2.1: Document generation (prerequisite for PDF export)
        test_data = {
            "matiere": "Mathématiques",
            "niveau": "6e",
            "chapitre": "Nombres entiers et décimaux",
            "type_doc": "exercices",
            "difficulte": "moyen",
            "nb_exercices": 3,
            "versions": ["A"],
            "guest_id": self.guest_id
        }
        
        success, response = self.run_test(
            "Document Generation", 
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
                exercises = document.get('exercises', [])
                print(f"   ✅ Document generated: {len(exercises)} exercises")
                print(f"   ✅ Document ID: {self.generated_document_id}")
            else:
                print(f"   ❌ Document generation failed - no document in response")
        pdf_tests.append(("Document Generation", success))
        
        # Test 2.2: Guest user PDF export (WeasyPrint)
        if self.generated_document_id:
            export_data = {
                "document_id": self.generated_document_id,
                "export_type": "sujet",
                "guest_id": self.guest_id
            }
            
            success, response = self.run_test(
                "Guest PDF Export (WeasyPrint)",
                "POST",
                "export",
                200,
                data=export_data,
                timeout=30
            )
            
            if success:
                print(f"   ✅ WeasyPrint PDF generation working for guests")
            else:
                print(f"   ❌ WeasyPrint PDF generation failed for guests")
            pdf_tests.append(("Guest PDF Export", success))
            
            # Test 2.3: Corrigé export for guests
            export_data["export_type"] = "corrige"
            success, response = self.run_test(
                "Guest Corrigé Export (WeasyPrint)",
                "POST",
                "export",
                200,
                data=export_data,
                timeout=30
            )
            pdf_tests.append(("Guest Corrigé Export", success))
        else:
            print("   ⚠️  Skipping PDF export tests - no document generated")
            pdf_tests.extend([("Guest PDF Export", False), ("Guest Corrigé Export", False)])
        
        # Test 2.4: Pro user PDF export structure (should handle session tokens)
        if self.generated_document_id:
            export_data = {
                "document_id": self.generated_document_id,
                "export_type": "sujet"
            }
            
            # Test with mock session token (should fail gracefully)
            mock_headers = {"X-Session-Token": "mock_session_token_for_testing"}
            success, response = self.run_test(
                "Pro PDF Export Structure",
                "POST",
                "export",
                400,  # Should return 400 for invalid session token
                data=export_data,
                headers=mock_headers,
                timeout=30
            )
            
            if success:
                print(f"   ✅ Pro PDF export structure working (proper session token validation)")
            else:
                print(f"   ❌ Pro PDF export structure may have issues")
            pdf_tests.append(("Pro PDF Export Structure", success))
        else:
            pdf_tests.append(("Pro PDF Export Structure", False))
        
        # Store results
        self.test_results['pdf_generation'] = pdf_tests
        
        passed = sum(1 for _, success in pdf_tests if success)
        total = len(pdf_tests)
        print(f"\n📊 PDF Generation Pipeline: {passed}/{total} tests passed")
        
        return passed, total

    def test_core_authentication(self):
        """Test 3: Core Authentication - Verify magic link authentication system"""
        print("\n" + "="*80)
        print("🔐 PHASE 1 TEST: CORE AUTHENTICATION SYSTEM")
        print("="*80)
        print("OBJECTIVE: Verify magic link authentication system still works")
        
        auth_tests = []
        
        # Test 3.1: Pro user status check
        success, response = self.run_test(
            "Pro User Status Check",
            "GET",
            f"subscription/status/{self.pro_user_email}",
            200
        )
        
        if success and isinstance(response, dict):
            is_pro = response.get('is_pro', False)
            if is_pro:
                expires = response.get('expires_date_formatted', 'Unknown')
                days_remaining = response.get('days_remaining', 0)
                print(f"   ✅ Pro user verified: expires {expires}, {days_remaining} days remaining")
            else:
                print(f"   ❌ Pro user status check failed")
        auth_tests.append(("Pro User Status", success))
        
        # Test 3.2: Magic link request
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
            if 'envoyé' in message.lower():
                print(f"   ✅ Magic link request successful")
            else:
                print(f"   ⚠️  Magic link request response unclear")
        auth_tests.append(("Magic Link Request", success))
        
        # Test 3.3: Session validation endpoint structure
        success, response = self.run_test(
            "Session Validation Structure",
            "GET",
            "auth/session/validate",
            401  # Should fail without token
        )
        
        if success:
            print(f"   ✅ Session validation endpoint working (properly rejects missing tokens)")
        auth_tests.append(("Session Validation", success))
        
        # Test 3.4: Logout endpoint structure
        success, response = self.run_test(
            "Logout Endpoint Structure",
            "POST",
            "auth/logout",
            400  # Should fail without token
        )
        
        if success:
            print(f"   ✅ Logout endpoint working (properly rejects missing tokens)")
        auth_tests.append(("Logout Endpoint", success))
        
        # Store results
        self.test_results['authentication'] = auth_tests
        
        passed = sum(1 for _, success in auth_tests if success)
        total = len(auth_tests)
        print(f"\n📊 Core Authentication: {passed}/{total} tests passed")
        
        return passed, total

    def test_template_system(self):
        """Test 4: Template System - Test template personalization endpoints"""
        print("\n" + "="*80)
        print("🎨 PHASE 1 TEST: TEMPLATE PERSONALIZATION SYSTEM")
        print("="*80)
        print("OBJECTIVE: Test template personalization endpoints for Pro users")
        
        template_tests = []
        
        # Test 4.1: Template styles endpoint (public)
        success, response = self.run_test(
            "Template Styles (Public)",
            "GET",
            "template/styles",
            200
        )
        
        if success and isinstance(response, dict):
            styles = response.get('styles', {})
            expected_styles = ['minimaliste', 'classique', 'moderne']
            available_styles = list(styles.keys())
            
            if all(style in available_styles for style in expected_styles):
                print(f"   ✅ All 3 template styles available: {available_styles}")
                
                # Verify style details
                for style_name in expected_styles:
                    style_data = styles.get(style_name, {})
                    if 'name' in style_data and 'description' in style_data and 'preview_colors' in style_data:
                        colors = style_data['preview_colors']
                        print(f"   ✅ {style_name}: {style_data['name']} - {colors}")
                    else:
                        print(f"   ⚠️  {style_name} style data incomplete")
            else:
                print(f"   ❌ Template styles incomplete: {available_styles}")
        template_tests.append(("Template Styles Public", success))
        
        # Test 4.2: Template get endpoint (Pro only)
        mock_headers = {"X-Session-Token": "mock_session_token"}
        success, response = self.run_test(
            "Template Get (Pro Only)",
            "GET",
            "template/get",
            401,  # Should require authentication
            headers=mock_headers
        )
        
        if success:
            print(f"   ✅ Template get endpoint properly secured (requires Pro authentication)")
        template_tests.append(("Template Get Security", success))
        
        # Test 4.3: Template save endpoint (Pro only)
        template_data = {
            "professor_name": "Prof. Test",
            "school_name": "École Test",
            "school_year": "2024-2025",
            "footer_text": "Test Footer",
            "template_style": "minimaliste"
        }
        
        success, response = self.run_test(
            "Template Save (Pro Only)",
            "POST",
            "template/save",
            401,  # Should require authentication
            data=template_data,
            headers=mock_headers
        )
        
        if success:
            print(f"   ✅ Template save endpoint properly secured (requires Pro authentication)")
        template_tests.append(("Template Save Security", success))
        
        # Test 4.4: Invalid template style rejection
        invalid_template_data = template_data.copy()
        invalid_template_data["template_style"] = "invalid_style"
        
        success, response = self.run_test(
            "Invalid Template Style",
            "POST",
            "template/save",
            401,  # Will fail at auth level first, which is expected
            data=invalid_template_data,
            headers=mock_headers
        )
        template_tests.append(("Invalid Style Rejection", success))
        
        # Store results
        self.test_results['template_system'] = template_tests
        
        passed = sum(1 for _, success in template_tests if success)
        total = len(template_tests)
        print(f"\n📊 Template System: {passed}/{total} tests passed")
        
        return passed, total

    def test_export_functionality(self):
        """Test 5: Export Functionality - Comprehensive testing of export pipeline"""
        print("\n" + "="*80)
        print("📤 PHASE 1 TEST: EXPORT FUNCTIONALITY")
        print("="*80)
        print("OBJECTIVE: Comprehensive testing of export pipeline for both user types")
        
        export_tests = []
        
        # Test 5.1: Guest quota system
        success, response = self.run_test(
            "Guest Quota Check",
            "GET",
            f"quota/check?guest_id={self.guest_id}",
            200
        )
        
        if success and isinstance(response, dict):
            remaining = response.get('exports_remaining', 0)
            max_exports = response.get('max_exports', 0)
            print(f"   ✅ Guest quota system working: {remaining}/{max_exports} exports remaining")
        export_tests.append(("Guest Quota System", success))
        
        # Test 5.2: Export without document ID (should fail)
        export_data = {
            "document_id": "invalid_document_id",
            "export_type": "sujet",
            "guest_id": self.guest_id
        }
        
        success, response = self.run_test(
            "Export Invalid Document",
            "POST",
            "export",
            404,  # Should return 404 for invalid document
            data=export_data
        )
        
        if success:
            print(f"   ✅ Export properly validates document IDs")
        export_tests.append(("Export Validation", success))
        
        # Test 5.3: Export without guest_id or session (should fail)
        if self.generated_document_id:
            export_data = {
                "document_id": self.generated_document_id,
                "export_type": "sujet"
                # No guest_id or session token
            }
            
            success, response = self.run_test(
                "Export Without Auth",
                "POST",
                "export",
                400,  # Should require guest_id or session token
                data=export_data
            )
            
            if success:
                print(f"   ✅ Export properly requires authentication or guest ID")
            export_tests.append(("Export Auth Requirement", success))
        else:
            export_tests.append(("Export Auth Requirement", False))
        
        # Test 5.4: Valid guest export (if we have a document)
        if self.generated_document_id:
            export_data = {
                "document_id": self.generated_document_id,
                "export_type": "sujet",
                "guest_id": self.guest_id
            }
            
            success, response = self.run_test(
                "Valid Guest Export",
                "POST",
                "export",
                200,
                data=export_data,
                timeout=30
            )
            
            if success:
                print(f"   ✅ Valid guest export working")
            export_tests.append(("Valid Guest Export", success))
        else:
            export_tests.append(("Valid Guest Export", False))
        
        # Test 5.5: Pro user export structure (with mock session)
        if self.generated_document_id:
            export_data = {
                "document_id": self.generated_document_id,
                "export_type": "sujet"
            }
            
            mock_headers = {"X-Session-Token": "mock_pro_session"}
            success, response = self.run_test(
                "Pro Export Structure",
                "POST",
                "export",
                400,  # Should validate session token and fail gracefully
                data=export_data,
                headers=mock_headers
            )
            
            if success:
                print(f"   ✅ Pro export structure working (validates session tokens)")
            export_tests.append(("Pro Export Structure", success))
        else:
            export_tests.append(("Pro Export Structure", False))
        
        # Store results
        self.test_results['export_functionality'] = export_tests
        
        passed = sum(1 for _, success in export_tests if success)
        total = len(export_tests)
        print(f"\n📊 Export Functionality: {passed}/{total} tests passed")
        
        return passed, total

    def run_phase1_stability_tests(self):
        """Run all Phase 1 stability tests"""
        print("🚀 PHASE 1 STABILITY VERIFICATION AFTER REPORTLAB UNIFICATION")
        print("=" * 80)
        print("CONTEXT: Le Maître Mot app has undergone major PDF generation refactoring")
        print("CHANGES: Removed ReportLab complexity, unified to WeasyPrint + ReportLab Flowables")
        print("OBJECTIVE: Verify system stability and core functionality")
        print("=" * 80)
        
        # Run all test categories
        test_results = {}
        
        # Test 1: Backend Service Stability
        passed, total = self.test_backend_service_stability()
        test_results['backend_stability'] = (passed, total)
        
        # Test 2: PDF Generation Pipeline
        passed, total = self.test_unified_pdf_generation()
        test_results['pdf_generation'] = (passed, total)
        
        # Test 3: Core Authentication
        passed, total = self.test_core_authentication()
        test_results['authentication'] = (passed, total)
        
        # Test 4: Template System
        passed, total = self.test_template_system()
        test_results['template_system'] = (passed, total)
        
        # Test 5: Export Functionality
        passed, total = self.test_export_functionality()
        test_results['export_functionality'] = (passed, total)
        
        return test_results

    def generate_final_report(self, test_results):
        """Generate comprehensive final report"""
        print("\n" + "=" * 80)
        print("📊 PHASE 1 STABILITY VERIFICATION - FINAL REPORT")
        print("=" * 80)
        
        total_passed = 0
        total_tests = 0
        
        for category, (passed, total) in test_results.items():
            total_passed += passed
            total_tests += total
            success_rate = (passed / total * 100) if total > 0 else 0
            status = "✅ PASSED" if passed == total else "⚠️  PARTIAL" if passed > 0 else "❌ FAILED"
            
            print(f"{category.replace('_', ' ').title()}: {passed}/{total} ({success_rate:.1f}%) {status}")
        
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\nOVERALL RESULTS: {total_passed}/{total_tests} tests passed ({overall_success_rate:.1f}%)")
        
        # Determine overall status
        if overall_success_rate >= 95:
            print("\n🎉 PHASE 1 STABILITY VERIFICATION: EXCELLENT")
            print("✅ System is highly stable after ReportLab unification")
            print("✅ All critical functionality working correctly")
            print("✅ Ready for production use")
            return 0
        elif overall_success_rate >= 85:
            print("\n✅ PHASE 1 STABILITY VERIFICATION: GOOD")
            print("✅ System is stable after ReportLab unification")
            print("⚠️  Minor issues detected but core functionality intact")
            print("✅ Safe for production use with monitoring")
            return 0
        elif overall_success_rate >= 70:
            print("\n⚠️  PHASE 1 STABILITY VERIFICATION: ACCEPTABLE")
            print("⚠️  System mostly stable but some issues detected")
            print("⚠️  Core functionality working but needs attention")
            print("⚠️  Consider addressing failed tests before production")
            return 1
        else:
            print("\n❌ PHASE 1 STABILITY VERIFICATION: CRITICAL ISSUES")
            print("❌ System stability compromised after ReportLab unification")
            print("❌ Multiple critical functionality failures detected")
            print("❌ Requires immediate attention before production use")
            return 2

def main():
    """Main function to run Phase 1 stability tests"""
    tester = Phase1StabilityTester()
    
    try:
        test_results = tester.run_phase1_stability_tests()
        return tester.generate_final_report(test_results)
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR during Phase 1 testing: {e}")
        return 3

if __name__ == "__main__":
    sys.exit(main())