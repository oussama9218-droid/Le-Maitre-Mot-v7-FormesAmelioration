#!/usr/bin/env python3
"""
Simple Two-Pass AI Test - Focus on core functionality
"""

import requests
import json
from datetime import datetime

def test_two_pass_ai():
    base_url = "https://lemaitremot.preview.emergentagent.com"
    api_url = f"{base_url}/api"
    guest_id = f"test-simple-{datetime.now().strftime('%H%M%S')}"
    
    print("🔺 Testing Two-Pass AI Geometric Schema Generation")
    print("="*60)
    
    # Test 1: Generate geometry document
    print("\n1. Testing Geometry Document Generation...")
    test_data = {
        "matiere": "Mathématiques",
        "niveau": "4e",
        "chapitre": "Théorème de Pythagore",
        "type_doc": "exercices",
        "difficulte": "moyen",
        "nb_exercices": 3,
        "versions": ["A"],
        "guest_id": guest_id
    }
    
    try:
        response = requests.post(f"{api_url}/generate", json=test_data, timeout=90)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            document = data.get('document')
            
            if document:
                exercises = document.get('exercises', [])
                print(f"   ✅ Generated {len(exercises)} exercises")
                
                # Check for geometric schemas
                schemas_found = 0
                base64_found = 0
                
                for i, exercise in enumerate(exercises):
                    enonce = exercise.get('enonce', '')
                    
                    # Check for schema references
                    if '"schéma":' in enonce or '"type":"schema_geometrique"' in enonce:
                        schemas_found += 1
                        print(f"   📐 Exercise {i+1}: Contains geometric schema")
                    
                    # Check for Base64 images (processed schemas)
                    if 'data:image/png;base64,' in enonce:
                        base64_found += 1
                        print(f"   🖼️  Exercise {i+1}: Contains Base64 image")
                
                print(f"   Summary: {schemas_found} schema references, {base64_found} Base64 images")
                
                # Test 2: PDF Export
                print("\n2. Testing PDF Export...")
                doc_id = document.get('id')
                
                if doc_id:
                    export_data = {
                        "document_id": doc_id,
                        "export_type": "sujet",
                        "guest_id": guest_id
                    }
                    
                    export_response = requests.post(f"{api_url}/export", json=export_data, timeout=30)
                    print(f"   Export Status: {export_response.status_code}")
                    
                    if export_response.status_code == 200:
                        print("   ✅ PDF export successful")
                    else:
                        print(f"   ❌ PDF export failed: {export_response.text[:200]}")
                
                # Test 3: Check backend logs for two-pass indicators
                print("\n3. Checking Backend Logs...")
                try:
                    import subprocess
                    result = subprocess.run(['tail', '-n', '50', '/var/log/supervisor/backend.err.log'], 
                                          capture_output=True, text=True, timeout=5)
                    log_content = result.stdout
                    
                    indicators = [
                        "🔺 Generating geometric schema for exercise with keywords",
                        "✅ Geometric schema successfully added to exercise",
                        "✅ Successfully generated"
                    ]
                    
                    found_logs = []
                    for indicator in indicators:
                        if indicator in log_content:
                            found_logs.append(indicator)
                    
                    if found_logs:
                        print(f"   ✅ Found {len(found_logs)} two-pass AI log indicators")
                        for log in found_logs:
                            print(f"      - {log}")
                    else:
                        print("   ⚠️  No two-pass AI indicators found in recent logs")
                        
                except Exception as e:
                    print(f"   ⚠️  Could not check logs: {e}")
                
                # Final assessment
                print("\n" + "="*60)
                print("📊 ASSESSMENT SUMMARY")
                print("="*60)
                
                if schemas_found > 0:
                    print("✅ Two-pass AI approach is generating geometric schemas")
                else:
                    print("⚠️  No geometric schemas detected in exercises")
                
                if base64_found > 0:
                    print("✅ Geometric schemas are being processed to Base64 images")
                elif schemas_found > 0:
                    print("⚠️  Schemas generated but not processed to Base64 (check web display processing)")
                
                if found_logs:
                    print("✅ Two-pass AI logging is working correctly")
                else:
                    print("⚠️  Two-pass AI logging may need verification")
                
                success_rate = (int(schemas_found > 0) + int(base64_found > 0) + int(len(found_logs) > 0)) / 3
                print(f"\n🎯 Overall Success Rate: {success_rate*100:.0f}%")
                
                if success_rate >= 0.67:
                    print("🎉 Two-pass AI system appears to be working correctly!")
                else:
                    print("⚠️  Two-pass AI system may need further investigation")
                
            else:
                print("   ❌ No document in response")
        else:
            print(f"   ❌ Generation failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Test failed with error: {e}")

if __name__ == "__main__":
    test_two_pass_ai()