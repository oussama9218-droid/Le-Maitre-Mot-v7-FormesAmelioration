#!/usr/bin/env python3

import requests
import json
import re
import sys
sys.path.append('/app/backend')
from geometry_renderer import geometry_renderer

def debug_geometric_schemas():
    print("🔍 Debugging geometric schema processing...")
    
    # Get the documents to see the actual schema format
    response = requests.get('https://teacherai.preview.emergentagent.com/api/documents?guest_id=test-styles-183236_geom')
    if response.status_code != 200:
        print(f"❌ Request failed: {response.status_code}")
        return
    
    data = response.json()
    documents = data.get('documents', [])
    if not documents:
        print("❌ No documents found")
        return
    
    doc = documents[0]
    exercises = doc.get('exercises', [])
    if not exercises:
        print("❌ No exercises found")
        return
    
    print(f"✅ Found document with {len(exercises)} exercises")
    
    for i, exercise in enumerate(exercises):
        enonce = exercise.get('enonce', '')
        print(f"\n📝 Exercise {i+1}:")
        print(f"   Enonce length: {len(enonce)}")
        print(f"   Contains 'schema_geometrique': {'schema_geometrique' in enonce}")
        
        if 'schema_geometrique' in enonce:
            print(f"   Raw enonce (first 300 chars): {enonce[:300]}")
            
            # Test the regex pattern
            pattern = r'\{\s*"type"\s*:\s*"schema_geometrique"[^}]*\}'
            matches = re.findall(pattern, enonce)
            print(f"   Regex matches found: {len(matches)}")
            
            for j, match in enumerate(matches):
                print(f"   Match {j+1}: {match}")
                try:
                    schema_data = json.loads(match)
                    print(f"   ✅ Valid JSON: {schema_data}")
                    
                    # Test Base64 rendering
                    base64_result = geometry_renderer.render_geometry_to_base64(schema_data)
                    print(f"   Base64 result length: {len(base64_result)}")
                    
                    # Test web processing
                    processed = geometry_renderer.process_geometric_schemas_for_web(match)
                    print(f"   Processed result length: {len(processed)}")
                    print(f"   Contains Base64 image: {'data:image/png;base64,' in processed}")
                    
                except Exception as e:
                    print(f"   ❌ JSON parse error: {e}")
            
            # Test the full processing function
            print(f"\n   🔧 Testing full processing function...")
            processed_enonce = geometry_renderer.process_geometric_schemas_for_web(enonce)
            print(f"   Original length: {len(enonce)}")
            print(f"   Processed length: {len(processed_enonce)}")
            print(f"   Contains Base64: {'data:image/png;base64,' in processed_enonce}")
            print(f"   Still contains raw schema: {'schema_geometrique' in processed_enonce and 'data:image/png;base64,' not in processed_enonce}")
            
            if processed_enonce != enonce:
                print(f"   ✅ Processing changed the content")
            else:
                print(f"   ❌ Processing did not change the content")

if __name__ == "__main__":
    debug_geometric_schemas()