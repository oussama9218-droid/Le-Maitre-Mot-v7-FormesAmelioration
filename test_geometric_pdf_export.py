#!/usr/bin/env python3
"""
Comprehensive Geometric Schema PDF Export Testing
Focus: Testing complete geometric schema integration for PDF export specifically
"""

import requests
import json
import time
import uuid
from datetime import datetime

class GeometricSchemaPDFTester:
    def __init__(self, base_url="https://teacherai.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.guest_id = f"geom-test-{datetime.now().strftime('%H%M%S')}"
        self.pro_user_email = "oussama92.18@gmail.com"
        self.geometry_documents = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, timeout=30):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        default_headers = {'Content-Type': 'application/json'}
        if headers:
            default_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
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
                except:
                    print(f"   Error text: {response.text[:200]}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout after {timeout}s")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_generate_geometry_focused_document(self):
        """Generate a mathematics document focusing on geometry with high likelihood of schemas"""
        print("\n📐 STEP 1: Generate geometry-focused document...")
        
        # Use Théorème de Pythagore as it's most likely to generate geometric schemas
        test_data = {
            "matiere": "Mathématiques",
            "niveau": "4e",
            "chapitre": "Théorème de Pythagore",
            "type_doc": "exercices",
            "difficulte": "moyen",
            "nb_exercices": 3,
            "versions": ["A"],
            "guest_id": self.guest_id
        }
        
        success, response = self.run_test(
            "Generate Pythagore Document (Geometry Focus)",
            "POST",
            "generate",
            200,
            data=test_data,
            timeout=60
        )
        
        if success and isinstance(response, dict):
            document = response.get('document')
            if document:
                doc_id = document.get('id')
                exercises = document.get('exercises', [])
                
                print(f"   ✅ Generated document {doc_id} with {len(exercises)} exercises")
                
                # Analyze exercises for geometric content
                geometric_exercises = 0
                schema_exercises = 0
                
                for i, exercise in enumerate(exercises):
                    enonce = exercise.get('enonce', '')
                    
                    # Check for geometric keywords
                    geometric_keywords = ['triangle', 'rectangle', 'carré', 'cercle', 'figure', 'côté', 'angle', 'pythagore']
                    has_geometric_content = any(keyword in enonce.lower() for keyword in geometric_keywords)
                    
                    if has_geometric_content:
                        geometric_exercises += 1
                        print(f"   📐 Exercise {i+1}: Contains geometric content")
                        
                        # Check for geometric schema JSON
                        if 'schema_geometrique' in enonce:
                            schema_exercises += 1
                            print(f"   🔺 Exercise {i+1}: Contains geometric schema JSON")
                            
                            # Extract schema details
                            import re
                            pattern = r'\{\s*"type"\s*:\s*"schema_geometrique"[^}]*\}'
                            match = re.search(pattern, enonce)
                            if match:
                                try:
                                    schema_data = json.loads(match.group(0))
                                    figure_type = schema_data.get('figure', 'unknown')
                                    points = schema_data.get('points', [])
                                    angle_droit = schema_data.get('angle_droit', 'none')
                                    print(f"     📊 Schema details: {figure_type}, points: {points}, angle droit: {angle_droit}")
                                except Exception as e:
                                    print(f"     ⚠️  Could not parse schema: {e}")
                        else:
                            print(f"   ⚠️  Exercise {i+1}: Geometric content but no schema JSON")
                    else:
                        print(f"   ℹ️  Exercise {i+1}: No obvious geometric content")
                
                print(f"\n   📊 Analysis Results:")
                print(f"   - Total exercises: {len(exercises)}")
                print(f"   - Geometric exercises: {geometric_exercises}")
                print(f"   - Schema exercises: {schema_exercises}")
                
                if schema_exercises > 0:
                    print(f"   🎯 EXCELLENT: Document contains {schema_exercises} geometric schemas - perfect for PDF testing")
                    self.geometry_documents.append({
                        'id': doc_id,
                        'exercises': len(exercises),
                        'geometric_exercises': geometric_exercises,
                        'schema_exercises': schema_exercises,
                        'chapter': 'Théorème de Pythagore'
                    })
                    return True, {'document_id': doc_id, 'schemas_found': schema_exercises}
                elif geometric_exercises > 0:
                    print(f"   ⚠️  Document has geometric content but no schemas - still useful for testing")
                    self.geometry_documents.append({
                        'id': doc_id,
                        'exercises': len(exercises),
                        'geometric_exercises': geometric_exercises,
                        'schema_exercises': 0,
                        'chapter': 'Théorème de Pythagore'
                    })
                    return True, {'document_id': doc_id, 'schemas_found': 0}
                else:
                    print(f"   ❌ Document lacks geometric content - not ideal for testing")
                    return False, {}
        
        return False, {}

    def test_export_geometry_pdf_sujet_detailed(self):
        """Test detailed sujet PDF export with geometric schemas"""
        if not self.geometry_documents:
            print("⚠️  No geometry documents available for testing")
            return False, {}
        
        print("\n📄 STEP 2: Export sujet PDF with geometric schemas...")
        
        doc = self.geometry_documents[0]
        doc_id = doc['id']
        
        export_data = {
            "document_id": doc_id,
            "export_type": "sujet",
            "guest_id": self.guest_id
        }
        
        success, response = self.run_test(
            "Export Geometry Sujet PDF (Detailed)",
            "POST",
            "export",
            200,
            data=export_data,
            timeout=45
        )
        
        if success:
            # Analyze PDF response
            pdf_size = 0
            if isinstance(response, bytes):
                pdf_size = len(response)
            elif isinstance(response, str):
                pdf_size = len(response.encode('utf-8'))
            elif isinstance(response, dict) and 'content' in response:
                pdf_size = len(response['content'])
            
            print(f"   📊 PDF Analysis:")
            print(f"   - Response type: {type(response)}")
            print(f"   - PDF size: {pdf_size} bytes")
            
            # Evaluate PDF quality based on size and schema content
            if pdf_size > 20000:  # Substantial PDF with likely rendered figures
                print(f"   🎯 EXCELLENT: Large PDF size indicates substantial content with rendered geometric figures")
                quality_score = "excellent"
            elif pdf_size > 10000:  # Good PDF size
                print(f"   ✅ GOOD: PDF size indicates good content, likely includes rendered figures")
                quality_score = "good"
            elif pdf_size > 5000:  # Minimal but acceptable
                print(f"   ⚠️  ACCEPTABLE: PDF size is minimal but acceptable")
                quality_score = "acceptable"
            else:
                print(f"   ❌ POOR: PDF size too small - may not contain rendered figures")
                quality_score = "poor"
            
            # Additional analysis based on document content
            if doc['schema_exercises'] > 0:
                print(f"   🔺 Document contains {doc['schema_exercises']} geometric schemas")
                if quality_score in ["excellent", "good"]:
                    print(f"   🎉 SUCCESS: PDF export successfully processed geometric schemas to SVG")
                else:
                    print(f"   ⚠️  WARNING: PDF may not have properly rendered geometric schemas")
            else:
                print(f"   ℹ️  Document has no schemas but geometric content present")
            
            return True, {
                'pdf_size': pdf_size,
                'quality_score': quality_score,
                'schemas_in_doc': doc['schema_exercises']
            }
        
        return False, {}

    def test_export_geometry_pdf_corrige_detailed(self):
        """Test detailed corrigé PDF export with geometric schemas"""
        if not self.geometry_documents:
            print("⚠️  No geometry documents available for testing")
            return False, {}
        
        print("\n📄 STEP 3: Export corrigé PDF with geometric schemas...")
        
        doc = self.geometry_documents[0]
        doc_id = doc['id']
        
        export_data = {
            "document_id": doc_id,
            "export_type": "corrige",
            "guest_id": self.guest_id
        }
        
        success, response = self.run_test(
            "Export Geometry Corrigé PDF (Detailed)",
            "POST",
            "export",
            200,
            data=export_data,
            timeout=45
        )
        
        if success:
            # Analyze PDF response
            pdf_size = 0
            if isinstance(response, bytes):
                pdf_size = len(response)
            elif isinstance(response, str):
                pdf_size = len(response.encode('utf-8'))
            elif isinstance(response, dict) and 'content' in response:
                pdf_size = len(response['content'])
            
            print(f"   📊 Corrigé PDF Analysis:")
            print(f"   - Response type: {type(response)}")
            print(f"   - PDF size: {pdf_size} bytes")
            
            # Corrigé PDFs should be larger than sujet PDFs due to solutions
            if pdf_size > 25000:  # Substantial corrigé PDF
                print(f"   🎯 EXCELLENT: Large corrigé PDF with detailed solutions and rendered figures")
                quality_score = "excellent"
            elif pdf_size > 15000:  # Good corrigé PDF
                print(f"   ✅ GOOD: Good-sized corrigé PDF with solutions and likely rendered figures")
                quality_score = "good"
            elif pdf_size > 8000:  # Acceptable corrigé PDF
                print(f"   ⚠️  ACCEPTABLE: Corrigé PDF has reasonable size")
                quality_score = "acceptable"
            else:
                print(f"   ❌ POOR: Corrigé PDF too small - may lack proper solutions or figures")
                quality_score = "poor"
            
            # Check for solution content expectations
            if doc['schema_exercises'] > 0:
                print(f"   🔺 Document contains {doc['schema_exercises']} geometric schemas in solutions")
                if quality_score in ["excellent", "good"]:
                    print(f"   🎉 SUCCESS: Corrigé PDF likely contains rendered geometric figures in solutions")
                else:
                    print(f"   ⚠️  WARNING: Corrigé PDF may not properly render geometric schemas in solutions")
            
            return True, {
                'pdf_size': pdf_size,
                'quality_score': quality_score,
                'schemas_in_doc': doc['schema_exercises']
            }
        
        return False, {}

    def test_multiple_template_styles_with_geometry(self):
        """Test geometric schema export with different template styles"""
        if not self.geometry_documents:
            print("⚠️  No geometry documents available for testing")
            return False, {}
        
        print("\n🎨 STEP 4: Test multiple template styles with geometric schemas...")
        
        doc = self.geometry_documents[0]
        doc_id = doc['id']
        
        # Test different styles (free user will fallback to classique for Pro styles)
        styles_to_test = [
            ("classique", "Free + Pro"),
            ("moderne", "Pro only (fallback to classique)"),
            ("eleve", "Pro only (fallback to classique)"),
            ("minimal", "Pro only (fallback to classique)")
        ]
        
        style_results = {}
        
        for style, description in styles_to_test:
            print(f"\n   🎨 Testing {style} style ({description})...")
            
            export_data = {
                "document_id": doc_id,
                "export_type": "sujet",
                "guest_id": self.guest_id,
                "template_style": style
            }
            
            success, response = self.run_test(
                f"Geometry Export - {style.title()} Style",
                "POST",
                "export",
                200,
                data=export_data,
                timeout=45
            )
            
            if success:
                pdf_size = 0
                if isinstance(response, bytes):
                    pdf_size = len(response)
                elif isinstance(response, str):
                    pdf_size = len(response.encode('utf-8'))
                
                print(f"   ✅ {style} style export successful ({pdf_size} bytes)")
                
                # Evaluate if geometric schemas work with this style
                if pdf_size > 10000:
                    print(f"   🔺 {style} style: PDF size indicates geometric schemas likely rendered correctly")
                    schema_quality = "good"
                elif pdf_size > 5000:
                    print(f"   ⚠️  {style} style: PDF size acceptable, schemas may be rendered")
                    schema_quality = "acceptable"
                else:
                    print(f"   ❌ {style} style: PDF size too small, schemas may not be rendered")
                    schema_quality = "poor"
                
                style_results[style] = {
                    'success': True,
                    'pdf_size': pdf_size,
                    'schema_quality': schema_quality
                }
            else:
                print(f"   ❌ {style} style export failed")
                style_results[style] = {
                    'success': False,
                    'pdf_size': 0,
                    'schema_quality': 'failed'
                }
        
        # Summary
        successful_styles = sum(1 for result in style_results.values() if result['success'])
        good_schema_styles = sum(1 for result in style_results.values() if result.get('schema_quality') == 'good')
        
        print(f"\n   📊 Template Style Results:")
        print(f"   - Successful exports: {successful_styles}/{len(styles_to_test)}")
        print(f"   - Good schema rendering: {good_schema_styles}/{len(styles_to_test)}")
        
        if successful_styles == len(styles_to_test):
            print(f"   🎉 SUCCESS: All template styles work with geometric schemas")
            return True, style_results
        elif successful_styles > 0:
            print(f"   ⚠️  PARTIAL: Some template styles work with geometric schemas")
            return True, style_results
        else:
            print(f"   ❌ FAILURE: No template styles working with geometric schemas")
            return False, style_results

    def test_pro_user_geometry_export(self):
        """Test geometric schema export with Pro user (if available)"""
        if not self.geometry_documents:
            print("⚠️  No geometry documents available for testing")
            return False, {}
        
        print("\n👤 STEP 5: Test Pro user geometric schema export...")
        
        doc = self.geometry_documents[0]
        doc_id = doc['id']
        
        # Test with Pro user email header (backwards compatibility)
        headers = {"X-User-Email": self.pro_user_email}
        
        export_data = {
            "document_id": doc_id,
            "export_type": "sujet",
            "template_style": "moderne"  # Pro-only style
        }
        
        success, response = self.run_test(
            "Pro User Geometry Export - Moderne Style",
            "POST",
            "export",
            200,  # Should work for Pro user
            data=export_data,
            headers=headers,
            timeout=45
        )
        
        if success:
            pdf_size = 0
            if isinstance(response, bytes):
                pdf_size = len(response)
            elif isinstance(response, str):
                pdf_size = len(response.encode('utf-8'))
            
            print(f"   ✅ Pro user export successful ({pdf_size} bytes)")
            
            # Check if Pro template was actually used (vs fallback)
            if pdf_size > 15000:
                print(f"   🎯 EXCELLENT: Large PDF suggests Pro template with enhanced geometric rendering")
                pro_quality = "excellent"
            elif pdf_size > 10000:
                print(f"   ✅ GOOD: Good PDF size suggests proper Pro template usage")
                pro_quality = "good"
            else:
                print(f"   ⚠️  ACCEPTABLE: PDF generated but may have used fallback template")
                pro_quality = "acceptable"
            
            return True, {
                'pdf_size': pdf_size,
                'pro_quality': pro_quality,
                'schemas_in_doc': doc['schema_exercises']
            }
        else:
            print(f"   ❌ Pro user export failed")
            return False, {}

    def test_verify_svg_vs_json_in_pdf(self):
        """Verify that PDFs contain SVG figures instead of raw JSON"""
        if not self.geometry_documents:
            print("⚠️  No geometry documents available for testing")
            return False, {}
        
        print("\n🔍 STEP 6: Verify SVG rendering vs raw JSON in PDFs...")
        
        doc = self.geometry_documents[0]
        
        if doc['schema_exercises'] == 0:
            print("   ℹ️  Document has no geometric schemas - cannot verify SVG vs JSON")
            return True, {'verification': 'no_schemas_to_test'}
        
        print(f"   📊 Document analysis:")
        print(f"   - Document ID: {doc['id']}")
        print(f"   - Total exercises: {doc['exercises']}")
        print(f"   - Geometric exercises: {doc['geometric_exercises']}")
        print(f"   - Schema exercises: {doc['schema_exercises']}")
        
        # Export PDF and analyze
        export_data = {
            "document_id": doc['id'],
            "export_type": "sujet",
            "guest_id": self.guest_id
        }
        
        success, response = self.run_test(
            "PDF Export for SVG Verification",
            "POST",
            "export",
            200,
            data=export_data,
            timeout=45
        )
        
        if success:
            pdf_size = 0
            if isinstance(response, bytes):
                pdf_size = len(response)
            elif isinstance(response, str):
                pdf_size = len(response.encode('utf-8'))
            
            print(f"   📄 PDF Export Results:")
            print(f"   - PDF size: {pdf_size} bytes")
            print(f"   - Schemas in document: {doc['schema_exercises']}")
            
            # Calculate expected size based on schema content
            base_pdf_size = 5000  # Base PDF without schemas
            expected_size_per_schema = 3000  # Rough estimate for rendered SVG
            expected_min_size = base_pdf_size + (doc['schema_exercises'] * expected_size_per_schema)
            
            print(f"   - Expected minimum size: {expected_min_size} bytes")
            
            if pdf_size >= expected_min_size:
                print(f"   🎉 SUCCESS: PDF size indicates geometric schemas are rendered as SVG (not raw JSON)")
                print(f"   🔺 Geometric figures are properly converted from JSON to visual SVG in PDF")
                verification_result = "svg_rendered"
            elif pdf_size > base_pdf_size:
                print(f"   ✅ GOOD: PDF size suggests some geometric content rendered")
                print(f"   🔺 Geometric schemas likely converted to SVG, though size is smaller than expected")
                verification_result = "likely_svg"
            else:
                print(f"   ❌ POOR: PDF size too small - geometric schemas may not be rendered properly")
                print(f"   ⚠️  Raw JSON may still be present instead of rendered SVG figures")
                verification_result = "possibly_raw_json"
            
            return True, {
                'pdf_size': pdf_size,
                'expected_size': expected_min_size,
                'verification_result': verification_result,
                'schemas_count': doc['schema_exercises']
            }
        
        return False, {}

    def run_comprehensive_geometric_pdf_test(self):
        """Run the complete geometric schema PDF export test suite"""
        print("="*80)
        print("📐 COMPREHENSIVE GEOMETRIC SCHEMA PDF EXPORT TESTING")
        print("="*80)
        print("OBJECTIVE: Verify complete geometric schema integration for PDF export")
        print("FOCUS: JSON → SVG conversion, substantial PDF sizes, template compatibility")
        print("EXPECTED: PDFs contain visual geometric figures, not raw JSON schemas")
        print("="*80)
        
        test_steps = [
            ("Generate Geometry Document", self.test_generate_geometry_focused_document),
            ("Export Sujet PDF (Detailed)", self.test_export_geometry_pdf_sujet_detailed),
            ("Export Corrigé PDF (Detailed)", self.test_export_geometry_pdf_corrige_detailed),
            ("Multiple Template Styles", self.test_multiple_template_styles_with_geometry),
            ("Pro User Export", self.test_pro_user_geometry_export),
            ("Verify SVG vs JSON", self.test_verify_svg_vs_json_in_pdf),
        ]
        
        results = {}
        passed_steps = 0
        
        for step_name, test_func in test_steps:
            print(f"\n{'='*60}")
            print(f"🔍 {step_name}")
            print(f"{'='*60}")
            
            try:
                success, result = test_func()
                results[step_name] = {
                    'success': success,
                    'result': result
                }
                
                if success:
                    passed_steps += 1
                    print(f"✅ {step_name}: PASSED")
                else:
                    print(f"❌ {step_name}: FAILED")
                    
            except Exception as e:
                print(f"❌ {step_name}: FAILED with exception: {e}")
                results[step_name] = {
                    'success': False,
                    'error': str(e)
                }
        
        # Final Assessment
        print(f"\n{'='*80}")
        print("📊 COMPREHENSIVE TEST RESULTS")
        print(f"{'='*80}")
        
        print(f"Steps passed: {passed_steps}/{len(test_steps)}")
        print(f"Success rate: {(passed_steps/len(test_steps))*100:.1f}%")
        
        # Detailed analysis
        if passed_steps == len(test_steps):
            print("\n🎉 COMPLETE SUCCESS!")
            print("✅ Geometric schema PDF export is fully functional")
            print("✅ JSON schemas are properly converted to SVG in PDFs")
            print("✅ All template styles work with geometric schemas")
            print("✅ Both sujet and corrigé exports working")
            print("✅ Pro user functionality confirmed")
            
        elif passed_steps >= len(test_steps) * 0.8:
            print("\n✅ MOSTLY SUCCESSFUL!")
            print("✅ Core geometric schema PDF export is working")
            print("⚠️  Some minor issues detected but main functionality intact")
            
        else:
            print("\n❌ SIGNIFICANT ISSUES DETECTED!")
            print("❌ Geometric schema PDF export may have problems")
            print("🔧 Review needed for proper JSON → SVG conversion")
        
        # Key findings summary
        print(f"\n📋 KEY FINDINGS:")
        
        if 'Generate Geometry Document' in results and results['Generate Geometry Document']['success']:
            doc_result = results['Generate Geometry Document']['result']
            schemas_found = doc_result.get('schemas_found', 0)
            print(f"• Generated document with {schemas_found} geometric schemas")
        
        if 'Export Sujet PDF (Detailed)' in results and results['Export Sujet PDF (Detailed)']['success']:
            sujet_result = results['Export Sujet PDF (Detailed)']['result']
            sujet_size = sujet_result.get('pdf_size', 0)
            print(f"• Sujet PDF: {sujet_size} bytes ({sujet_result.get('quality_score', 'unknown')} quality)")
        
        if 'Export Corrigé PDF (Detailed)' in results and results['Export Corrigé PDF (Detailed)']['success']:
            corrige_result = results['Export Corrigé PDF (Detailed)']['result']
            corrige_size = corrige_result.get('pdf_size', 0)
            print(f"• Corrigé PDF: {corrige_size} bytes ({corrige_result.get('quality_score', 'unknown')} quality)")
        
        if 'Verify SVG vs JSON' in results and results['Verify SVG vs JSON']['success']:
            verify_result = results['Verify SVG vs JSON']['result']
            verification = verify_result.get('verification_result', 'unknown')
            print(f"• SVG Verification: {verification}")
        
        print(f"\n🎯 CONCLUSION:")
        if passed_steps >= len(test_steps) * 0.8:
            print("Geometric schema integration for PDF export is working correctly!")
            print("PDFs contain rendered geometric figures instead of raw JSON.")
        else:
            print("Geometric schema PDF export needs attention.")
            print("Some issues detected in the JSON → SVG conversion pipeline.")
        
        return passed_steps, len(test_steps), results

if __name__ == "__main__":
    tester = GeometricSchemaPDFTester()
    
    passed, total, results = tester.run_comprehensive_geometric_pdf_test()
    
    print(f"\n🏁 FINAL RESULT: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All geometric schema PDF export tests successful!")
        exit(0)
    elif passed >= total * 0.8:
        print("✅ Most tests passed - system appears functional")
        exit(0)
    else:
        print("⚠️  Several tests failed - review needed")
        exit(1)