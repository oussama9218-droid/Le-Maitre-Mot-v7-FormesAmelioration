#!/usr/bin/env python3

import requests
import json

def test_export_styles():
    """Test the export styles endpoint"""
    
    print("Testing export/styles endpoint...")
    
    # Test 1: Free user (no session token)
    print("\n1. Testing as free user (no session token):")
    response = requests.get('https://teacherai.preview.emergentagent.com/api/export/styles')
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Styles count: {len(data.get('styles', {}))}")
    print(f"User is pro: {data.get('user_is_pro', False)}")
    for style_id, style in data.get('styles', {}).items():
        print(f"  - {style_id}: {style.get('name')} (pro_only: {style.get('pro_only', 'N/A')})")
    
    # Test 2: With fake Pro session token
    print("\n2. Testing with fake Pro session token:")
    headers = {'X-Session-Token': 'fake-pro-token-12345'}
    response = requests.get('https://teacherai.preview.emergentagent.com/api/export/styles', headers=headers)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Styles count: {len(data.get('styles', {}))}")
    print(f"User is pro: {data.get('user_is_pro', False)}")
    for style_id, style in data.get('styles', {}).items():
        print(f"  - {style_id}: {style.get('name')} (pro_only: {style.get('pro_only', 'N/A')})")
    
    # Test 3: Test export with different styles
    print("\n3. Testing export with different styles:")
    
    # First generate a document
    print("Generating test document...")
    doc_data = {
        "matiere": "Mathématiques",
        "niveau": "6e", 
        "chapitre": "Nombres entiers et décimaux",
        "type_doc": "exercices",
        "difficulte": "moyen",
        "nb_exercices": 2,
        "guest_id": "test-styles-debug"
    }
    
    doc_response = requests.post('https://teacherai.preview.emergentagent.com/api/generate', json=doc_data)
    if doc_response.status_code == 200:
        doc_id = doc_response.json()['document']['id']
        print(f"Document generated: {doc_id}")
        
        # Test export with classique style
        export_data = {
            "document_id": doc_id,
            "export_type": "sujet",
            "guest_id": "test-styles-debug",
            "template_style": "classique"
        }
        
        export_response = requests.post('https://teacherai.preview.emergentagent.com/api/export', json=export_data)
        print(f"Export with classique: {export_response.status_code}")
        
        # Test export with moderne style (should fallback to classique for free user)
        export_data["template_style"] = "moderne"
        export_response = requests.post('https://teacherai.preview.emergentagent.com/api/export', json=export_data)
        print(f"Export with moderne: {export_response.status_code}")
        
    else:
        print(f"Failed to generate document: {doc_response.status_code}")

if __name__ == "__main__":
    test_export_styles()