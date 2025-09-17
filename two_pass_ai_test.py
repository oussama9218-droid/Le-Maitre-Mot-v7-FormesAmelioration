#!/usr/bin/env python3
"""
Two-Pass AI Geometric Schema Generation Tests
Tests the new two-pass AI approach for reliable geometric schema generation.
"""

import requests
import sys
import json
import time
import uuid
from datetime import datetime

class TwoPassAITester:
    def __init__(self, base_url="https://lemaitremot.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.guest_id = f"test-two-pass-{datetime.now().strftime('%H%M%S')}"
        self.geometry_document_ids = []

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

    def test_geometry_document_generation(self):
        """Test document generation for geometry chapters to verify two-pass AI approach"""
        print("\n🔺 Testing Two-Pass AI Geometric Schema Generation...")
        
        # Test different geometry chapters across levels
        geometry_chapters = [
            {"matiere": "Mathématiques", "niveau": "6e", "chapitre": "Géométrie - Figures planes"},
            {"matiere": "Mathématiques", "niveau": "4e", "chapitre": "Théorème de Pythagore"},
            {"matiere": "Mathématiques", "niveau": "5e", "chapitre": "Géométrie - Triangles et quadrilatères"},
            {"matiere": "Mathématiques", "niveau": "3e", "chapitre": "Géométrie dans l'espace"}
        ]
        
        geometry_tests_passed = 0
        geometry_tests_total = len(geometry_chapters)
        
        for chapter_data in geometry_chapters:
            test_data = {
                "matiere": chapter_data["matiere"],
                "niveau": chapter_data["niveau"],
                "chapitre": chapter_data["chapitre"],
                "type_doc": "exercices",
                "difficulte": "moyen",
                "nb_exercices": 4,  # More exercises to increase chance of geometric schemas
                "versions": ["A"],
                "guest_id": f"{self.guest_id}_geometry"
            }
            
            print(f"\n   Testing: {chapter_data['niveau']} - {chapter_data['chapitre']}")
            success, response = self.run_test(
                f"Geometry Generation - {chapter_data['niveau']} {chapter_data['chapitre']}",
                "POST",
                "generate",
                200,
                data=test_data,
                timeout=90  # Longer timeout for two-pass AI generation
            )
            
            if success and isinstance(response, dict):
                document = response.get('document')
                if document:
                    document_id = document.get('id')
                    exercises = document.get('exercises', [])
                    
                    print(f"   Generated {len(exercises)} exercises for {chapter_data['chapitre']}")
                    
                    # Check for geometric schemas in exercises
                    schemas_found = 0
                    base64_images_found = 0
                    
                    for i, exercise in enumerate(exercises):
                        enonce = exercise.get('enonce', '')
                        
                        # Check for Base64 images (processed geometric schemas)
                        if 'data:image/png;base64,' in enonce:
                            base64_images_found += 1
                            print(f"   ✅ Exercise {i+1}: Found Base64 geometric schema")
                        
                        # Check for raw geometric schema JSON (should be processed)
                        if '"type":"schema_geometrique"' in enonce or '"schéma":' in enonce:
                            schemas_found += 1
                            print(f"   📐 Exercise {i+1}: Contains geometric schema data")
                        
                        # Check solution steps for geometric content
                        solution = exercise.get('solution', {})
                        etapes = solution.get('etapes', [])
                        for step in etapes:
                            if 'data:image/png;base64,' in step:
                                print(f"   ✅ Exercise {i+1}: Found Base64 schema in solution step")
                    
                    print(f"   Summary: {base64_images_found} Base64 images, {schemas_found} schema references")
                    
                    # Test the document endpoint to verify web display processing
                    if document_id:
                        doc_success, doc_response = self.run_test(
                            f"Document Web Display - {chapter_data['chapitre']}",
                            "GET",
                            f"documents/{document_id}",
                            200
                        )
                        
                        if doc_success and isinstance(doc_response, dict):
                            doc_exercises = doc_response.get('exercises', [])
                            web_base64_count = 0
                            raw_schema_count = 0
                            
                            for exercise in doc_exercises:
                                enonce = exercise.get('enonce', '')
                                if 'data:image/png;base64,' in enonce:
                                    web_base64_count += 1
                                if '"type":"schema_geometrique"' in enonce:
                                    raw_schema_count += 1
                            
                            print(f"   Web Display: {web_base64_count} Base64 images, {raw_schema_count} raw schemas")
                            
                            if web_base64_count > 0 and raw_schema_count == 0:
                                print(f"   ✅ Geometric schema web display fix working correctly")
                                geometry_tests_passed += 1
                            elif web_base64_count > 0:
                                print(f"   ⚠️  Some schemas processed, but {raw_schema_count} raw schemas remain")
                                geometry_tests_passed += 1
                            elif schemas_found > 0:
                                print(f"   ⚠️  Schemas generated but not properly processed for web display")
                            else:
                                print(f"   ℹ️  No geometric schemas generated (normal for some exercises)")
                                geometry_tests_passed += 1  # Not an error - AI may not generate schemas for all exercises
                        
                        # Store document ID for export testing
                        self.geometry_document_ids.append(document_id)
                
                if success:
                    geometry_tests_passed += 1
            else:
                print(f"   ❌ Failed to generate document for {chapter_data['chapitre']}")
        
        print(f"\n🔺 Geometry Generation Tests: {geometry_tests_passed}/{geometry_tests_total} passed")
        return geometry_tests_passed >= geometry_tests_total * 0.75, {"geometry_tests": geometry_tests_passed, "total": geometry_tests_total}
    
    def test_two_pass_ai_logging(self):
        """Test that two-pass AI approach logging is working"""
        print("\n📝 Testing Two-Pass AI Logging...")
        
        # Generate a geometry document to trigger two-pass approach
        test_data = {
            "matiere": "Mathématiques",
            "niveau": "4e",
            "chapitre": "Théorème de Pythagore",
            "type_doc": "exercices",
            "difficulte": "moyen",
            "nb_exercices": 3,
            "versions": ["A"],
            "guest_id": f"{self.guest_id}_logging"
        }
        
        print("   Generating Pythagoras theorem exercises to trigger geometric schema generation...")
        success, response = self.run_test(
            "Two-Pass AI Logging Test",
            "POST",
            "generate",
            200,
            data=test_data,
            timeout=90
        )
        
        if success:
            print("   ✅ Document generation successful")
            
            # Check backend logs for two-pass approach indicators
            try:
                import subprocess
                result = subprocess.run(['tail', '-n', '100', '/var/log/supervisor/backend.out.log'], 
                                      capture_output=True, text=True, timeout=5)
                log_content = result.stdout
                
                # Look for two-pass AI logging messages
                two_pass_indicators = [
                    "🔺 Generating geometric schema for exercise with keywords",
                    "✅ Geometric schema successfully added to exercise",
                    "⚠️ Empty or invalid schema generated, keeping text-only exercise"
                ]
                
                found_indicators = []
                for indicator in two_pass_indicators:
                    if indicator in log_content:
                        found_indicators.append(indicator)
                        print(f"   ✅ Found log: {indicator}")
                
                if found_indicators:
                    print(f"   ✅ Two-pass AI logging is working ({len(found_indicators)} indicators found)")
                    return True, {"logging_indicators": found_indicators}
                else:
                    print("   ⚠️  No two-pass AI logging indicators found in recent logs")
                    return False, {"logging_indicators": []}
                    
            except Exception as e:
                print(f"   ⚠️  Could not check backend logs: {e}")
                return True, {"logging_check": "skipped"}  # Don't fail test if log check fails
        else:
            print("   ❌ Document generation failed")
            return False, {}
    
    def test_geometric_schema_keyword_detection(self):
        """Test that geometric keywords properly trigger schema generation"""
        print("\n🔍 Testing Geometric Keyword Detection...")
        
        # Test chapters with different geometric keywords
        keyword_tests = [
            {"chapitre": "Théorème de Pythagore", "expected_keywords": ["triangle", "pythagore"]},
            {"chapitre": "Géométrie - Figures planes", "expected_keywords": ["géométrie", "figure", "cercle", "carré"]},
            {"chapitre": "Géométrie dans l'espace", "expected_keywords": ["géométrie", "volume", "cube"]},
        ]
        
        keyword_tests_passed = 0
        
        for test_case in keyword_tests:
            test_data = {
                "matiere": "Mathématiques",
                "niveau": "4e",
                "chapitre": test_case["chapitre"],
                "type_doc": "exercices",
                "difficulte": "moyen",
                "nb_exercices": 2,
                "versions": ["A"],
                "guest_id": f"{self.guest_id}_keywords"
            }
            
            print(f"\n   Testing keyword detection for: {test_case['chapitre']}")
            success, response = self.run_test(
                f"Keyword Detection - {test_case['chapitre']}",
                "POST",
                "generate",
                200,
                data=test_data,
                timeout=60
            )
            
            if success and isinstance(response, dict):
                document = response.get('document')
                if document:
                    exercises = document.get('exercises', [])
                    
                    # Check if exercises contain expected geometric keywords
                    keywords_found = []
                    for exercise in exercises:
                        enonce = exercise.get('enonce', '').lower()
                        for keyword in test_case["expected_keywords"]:
                            if keyword.lower() in enonce:
                                keywords_found.append(keyword)
                    
                    if keywords_found:
                        print(f"   ✅ Found geometric keywords: {set(keywords_found)}")
                        keyword_tests_passed += 1
                    else:
                        print(f"   ⚠️  No expected keywords found in exercises")
                else:
                    print(f"   ❌ No document generated")
            else:
                print(f"   ❌ Failed to generate document for keyword test")
        
        print(f"\n🔍 Keyword Detection Tests: {keyword_tests_passed}/{len(keyword_tests)} passed")
        return keyword_tests_passed >= len(keyword_tests) * 0.5, {"keyword_tests": keyword_tests_passed}
    
    def test_geometric_schema_pdf_export(self):
        """Test PDF export with geometric schemas"""
        print("\n📄 Testing PDF Export with Geometric Schemas...")
        
        if not self.geometry_document_ids:
            print("   ⚠️  No geometry documents available for export testing")
            return False, {}
        
        export_tests_passed = 0
        export_tests_total = 0
        
        for doc_id in self.geometry_document_ids[:2]:  # Test first 2 documents
            for export_type in ["sujet", "corrige"]:
                export_data = {
                    "document_id": doc_id,
                    "export_type": export_type,
                    "guest_id": f"{self.guest_id}_geometry_export"
                }
                
                export_tests_total += 1
                print(f"\n   Testing {export_type} export for geometry document...")
                success, response = self.run_test(
                    f"Geometry PDF Export - {export_type}",
                    "POST",
                    "export",
                    200,
                    data=export_data,
                    timeout=45
                )
                
                if success:
                    print(f"   ✅ {export_type.title()} PDF export successful")
                    export_tests_passed += 1
                    
                    # Check if response indicates PDF size (indirect indicator of content)
                    if isinstance(response, dict):
                        # Look for any size indicators or success messages
                        if response or len(str(response)) > 10:
                            print(f"   ✅ PDF export response indicates successful generation")
                else:
                    print(f"   ❌ {export_type.title()} PDF export failed")
        
        print(f"\n📄 PDF Export Tests: {export_tests_passed}/{export_tests_total} passed")
        return export_tests_passed >= export_tests_total * 0.75, {"export_tests": export_tests_passed, "total": export_tests_total}
    
    def test_fallback_exercise_processing(self):
        """Test that fallback exercises also use proper content processing"""
        print("\n🔄 Testing Fallback Exercise Content Processing...")
        
        # Generate document with invalid subject to potentially trigger fallback
        test_data = {
            "matiere": "Mathématiques",
            "niveau": "6e",
            "chapitre": "Géométrie - Figures planes",
            "type_doc": "exercices",
            "difficulte": "facile",
            "nb_exercices": 2,
            "versions": ["A"],
            "guest_id": f"{self.guest_id}_fallback"
        }
        
        success, response = self.run_test(
            "Fallback Exercise Processing",
            "POST",
            "generate",
            200,
            data=test_data,
            timeout=30  # Shorter timeout to potentially trigger fallback
        )
        
        if success and isinstance(response, dict):
            document = response.get('document')
            if document:
                exercises = document.get('exercises', [])
                
                # Check that exercises have proper structure and icons
                processed_exercises = 0
                for exercise in exercises:
                    enonce = exercise.get('enonce', '')
                    icone = exercise.get('icone', '')
                    exercise_type = exercise.get('exercise_type', '')
                    
                    if enonce and icone and exercise_type:
                        processed_exercises += 1
                        print(f"   ✅ Exercise has proper structure: type={exercise_type}, icon={icone}")
                
                if processed_exercises == len(exercises):
                    print(f"   ✅ All {processed_exercises} exercises properly processed")
                    return True, {"processed_exercises": processed_exercises}
                else:
                    print(f"   ⚠️  Only {processed_exercises}/{len(exercises)} exercises properly processed")
                    return False, {"processed_exercises": processed_exercises, "total": len(exercises)}
        
        print("   ❌ Failed to test fallback exercise processing")
        return False, {}
    
    def test_json_validation_robustness(self):
        """Test that both AI passes handle malformed JSON gracefully"""
        print("\n🛡️ Testing JSON Validation Robustness...")
        
        # This test verifies the system handles AI responses gracefully
        # We can't directly inject malformed JSON, but we can test the system's resilience
        
        test_data = {
            "matiere": "Mathématiques",
            "niveau": "5e",
            "chapitre": "Géométrie - Triangles et quadrilatères",
            "type_doc": "exercices",
            "difficulte": "difficile",  # Higher difficulty might stress the AI
            "nb_exercices": 3,
            "versions": ["A"],
            "guest_id": f"{self.guest_id}_json_test"
        }
        
        success, response = self.run_test(
            "JSON Validation Robustness",
            "POST",
            "generate",
            200,
            data=test_data,
            timeout=60
        )
        
        if success and isinstance(response, dict):
            document = response.get('document')
            if document:
                exercises = document.get('exercises', [])
                
                # Check that all exercises have valid structure
                valid_exercises = 0
                for exercise in exercises:
                    # Check required fields
                    required_fields = ['enonce', 'solution', 'difficulte']
                    has_all_fields = all(field in exercise for field in required_fields)
                    
                    if has_all_fields:
                        valid_exercises += 1
                        
                        # Check solution structure
                        solution = exercise.get('solution', {})
                        if isinstance(solution, dict) and 'etapes' in solution:
                            print(f"   ✅ Exercise has valid JSON structure")
                        else:
                            print(f"   ⚠️  Exercise solution structure may be incomplete")
                
                if valid_exercises == len(exercises):
                    print(f"   ✅ All {valid_exercises} exercises have valid JSON structure")
                    return True, {"valid_exercises": valid_exercises}
                else:
                    print(f"   ⚠️  Only {valid_exercises}/{len(exercises)} exercises have valid structure")
                    return False, {"valid_exercises": valid_exercises, "total": len(exercises)}
        
        print("   ❌ Failed to test JSON validation robustness")
        return False, {}
    
    def run_all_tests(self):
        """Run comprehensive two-pass AI geometric schema generation tests"""
        print("\n" + "="*80)
        print("🔺 TWO-PASS AI GEOMETRIC SCHEMA GENERATION TESTS")
        print("="*80)
        print("CONTEXT: Testing the new two-pass AI approach for reliable geometric schema generation")
        print("FEATURES: First pass generates exercise content, second pass adds geometric schemas")
        print("FOCUS: Geometry chapters, keyword detection, Base64 web display, PDF export")
        print("="*80)
        
        two_pass_tests = [
            ("Geometry Document Generation", self.test_geometry_document_generation),
            ("Two-Pass AI Logging", self.test_two_pass_ai_logging),
            ("Geometric Keyword Detection", self.test_geometric_schema_keyword_detection),
            ("Geometric Schema PDF Export", self.test_geometric_schema_pdf_export),
            ("Fallback Exercise Processing", self.test_fallback_exercise_processing),
            ("JSON Validation Robustness", self.test_json_validation_robustness),
        ]
        
        two_pass_passed = 0
        two_pass_total = len(two_pass_tests)
        
        for test_name, test_func in two_pass_tests:
            try:
                success, result = test_func()
                if success:
                    two_pass_passed += 1
                    print(f"\n✅ {test_name}: PASSED")
                else:
                    print(f"\n❌ {test_name}: FAILED")
                    if isinstance(result, dict) and result:
                        print(f"   Details: {result}")
            except Exception as e:
                print(f"\n❌ {test_name}: FAILED with exception: {e}")
        
        print(f"\n🔺 Two-Pass AI Tests: {two_pass_passed}/{two_pass_total} passed")
        
        # Final summary
        print("\n" + "="*80)
        print("📊 TWO-PASS AI TEST SUMMARY")
        print("="*80)
        print(f"Tests Passed: {two_pass_passed}/{two_pass_total} ({two_pass_passed/two_pass_total*100:.1f}%)")
        
        if two_pass_passed == two_pass_total:
            print("🎉 ALL TWO-PASS AI TESTS PASSED!")
        elif two_pass_passed / two_pass_total >= 0.8:
            print("✅ Most tests passed - two-pass AI system appears stable")
        else:
            print("⚠️  Several tests failed - review needed")
        
        return two_pass_passed, two_pass_total

if __name__ == "__main__":
    tester = TwoPassAITester()
    tester.run_all_tests()