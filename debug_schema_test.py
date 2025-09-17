#!/usr/bin/env python3
"""
Debug Schema Processing Test
"""

import requests
import json
from datetime import datetime

def debug_schema_processing():
    base_url = "https://lemaitremot.preview.emergentagent.com"
    api_url = f"{base_url}/api"
    guest_id = f"debug-{datetime.now().strftime('%H%M%S')}"
    
    print("🔍 Debugging Schema Processing")
    print("="*50)
    
    # Generate a geometry document
    test_data = {
        "matiere": "Mathématiques",
        "niveau": "4e",
        "chapitre": "Théorème de Pythagore",
        "type_doc": "exercices",
        "difficulte": "moyen",
        "nb_exercices": 2,
        "versions": ["A"],
        "guest_id": guest_id
    }
    
    try:
        response = requests.post(f"{api_url}/generate", json=test_data, timeout=90)
        
        if response.status_code == 200:
            data = response.json()
            document = data.get('document')
            
            if document:
                exercises = document.get('exercises', [])
                print(f"Generated {len(exercises)} exercises")
                
                for i, exercise in enumerate(exercises):
                    enonce = exercise.get('enonce', '')
                    print(f"\n--- Exercise {i+1} ---")
                    print(f"Length: {len(enonce)} characters")
                    
                    # Look for schema patterns
                    if '"schéma":' in enonce:
                        print("✅ Found 'schéma' key")
                        # Extract the schema part
                        start = enonce.find('"schéma":')
                        if start != -1:
                            # Find the end of the schema JSON
                            brace_count = 0
                            schema_start = enonce.find('{', start)
                            if schema_start != -1:
                                for j, char in enumerate(enonce[schema_start:], schema_start):
                                    if char == '{':
                                        brace_count += 1
                                    elif char == '}':
                                        brace_count -= 1
                                        if brace_count == 0:
                                            schema_json = enonce[schema_start:j+1]
                                            print(f"Schema JSON: {schema_json[:200]}...")
                                            break
                    
                    if 'data:image/png;base64,' in enonce:
                        print("✅ Found Base64 image")
                        base64_start = enonce.find('data:image/png;base64,')
                        if base64_start != -1:
                            base64_end = enonce.find('"', base64_start)
                            if base64_end != -1:
                                base64_length = base64_end - base64_start - 22  # Length of "data:image/png;base64,"
                                print(f"Base64 length: {base64_length} characters")
                    
                    # Show first 300 characters of enonce
                    print(f"Content preview: {enonce[:300]}...")
                    
                    if '"type":"schema_geometrique"' in enonce:
                        print("⚠️  Found raw schema_geometrique - not processed to Base64")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_schema_processing()