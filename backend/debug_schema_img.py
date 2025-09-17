#!/usr/bin/env python3
"""
Debug script to test schema_img pipeline step by step
"""

import asyncio
import json
from server import generate_exercises_with_ai, process_schema_to_base64

async def test_schema_img_pipeline():
    """Test the complete schema_img pipeline"""
    print("🔍 DEBUGGING SCHEMA_IMG PIPELINE")
    print("=" * 50)
    
    # Step 1: Generate exercises with AI
    print("\n📝 Step 1: Generate exercises with AI")
    try:
        exercises = await generate_exercises_with_ai(
            matiere="Mathématiques",
            niveau="4e", 
            chapitre="Théorème de Pythagore",
            type_doc="exercices",
            difficulte="moyen",
            nb_exercices=2
        )
        
        print(f"✅ Generated {len(exercises)} exercises")
        
        for i, exercise in enumerate(exercises):
            print(f"\n🔍 Exercise {i+1}:")
            print(f"   Type: {exercise.type}")
            print(f"   Has schema field: {'schema' in exercise.__dict__}")
            print(f"   Has schema_img field: {'schema_img' in exercise.__dict__}")
            print(f"   Has donnees field: {'donnees' in exercise.__dict__}")
            
            if hasattr(exercise, 'schema') and exercise.schema:
                print(f"   Schema type: {exercise.schema.get('type', 'unknown')}")
            
            if hasattr(exercise, 'schema_img') and exercise.schema_img:
                print(f"   Schema_img length: {len(exercise.schema_img)}")
                print(f"   Schema_img starts with: {exercise.schema_img[:50]}...")
            else:
                print(f"   Schema_img: {getattr(exercise, 'schema_img', 'NOT_FOUND')}")
            
            if hasattr(exercise, 'donnees') and exercise.donnees:
                schema_in_donnees = exercise.donnees.get('schema') if isinstance(exercise.donnees, dict) else None
                if schema_in_donnees:
                    print(f"   Donnees schema type: {schema_in_donnees.get('type', 'unknown')}")
    
    except Exception as e:
        print(f"❌ Error in generation: {e}")
        import traceback
        traceback.print_exc()

    # Step 2: Test schema processing directly
    print("\n🎨 Step 2: Test schema processing directly")
    test_schema = {
        "type": "triangle",
        "points": ["A", "B", "C"],
        "segments": [["A", "B", {"longueur": 5}], ["B", "C", {"longueur": 3}]]
    }
    
    try:
        base64_result = process_schema_to_base64(test_schema)
        if base64_result:
            print(f"✅ Schema processing successful, Base64 length: {len(base64_result)}")
            print(f"   Starts with: {base64_result[:50]}...")
        else:
            print("❌ Schema processing returned None")
    except Exception as e:
        print(f"❌ Error in schema processing: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 50)

if __name__ == "__main__":
    asyncio.run(test_schema_img_pipeline())