#!/usr/bin/env python3
"""
Test script for render_schema.py fixes
"""

from render_schema import schema_renderer
import json

def test_render_fixes():
    """Test the render_schema fixes"""
    print("🔧 TESTING RENDER_SCHEMA FIXES")
    print("=" * 50)
    
    # Test cases that were causing KeyError
    test_cases = [
        {
            "name": "Triangle Rectangle with 4 points (was causing KeyError)",
            "schema": {
                "type": "triangle_rectangle",
                "points": ["A", "B", "C", "D"],  # This was causing KeyError: 'D'
                "segments": [
                    ["A", "B", {"longueur": 5}],
                    ["B", "C", {"longueur": 3}]
                ],
                "angles": [
                    ["B", {"angle_droit": True}]
                ]
            }
        },
        {
            "name": "Triangle with labels",
            "schema": {
                "type": "triangle",
                "points": ["A", "B", "C"],
                "labels": {"A": "(0,4)", "B": "(0,0)", "C": "(3,0)"},
                "segments": [
                    ["A", "B", {"longueur": 4}],
                    ["B", "C", {"longueur": 3}]
                ]
            }
        },
        {
            "name": "Rectangle",
            "schema": {
                "type": "rectangle",
                "longueur": 6,
                "largeur": 4
            }
        },
        {
            "name": "Triangle Rectangle (simple)",
            "schema": {
                "type": "triangle_rectangle",
                "points": ["A", "B", "C"],
                "labels": {"A": "(0,8)", "B": "(0,0)", "C": "(6,0)"}
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        schema = test_case['schema']
        
        try:
            svg_result = schema_renderer.render_to_svg(schema)
            
            if svg_result and len(svg_result) > 100:
                print(f"   ✅ SUCCESS: SVG generated ({len(svg_result)} chars)")
                print(f"   📊 Schema type: {schema.get('type')}")
                print(f"   📊 Points: {schema.get('points', 'N/A')}")
                
                # Check for common SVG elements
                if '<svg' in svg_result and '</svg>' in svg_result:
                    print("   ✅ Valid SVG structure")
                else:
                    print("   ⚠️  Potentially invalid SVG structure")
                    
            elif svg_result == "":
                print("   ❌ FAILED: Empty SVG returned")
            else:
                print(f"   ⚠️  PARTIAL: SVG too short ({len(svg_result)} chars)")
                print(f"   Content preview: {svg_result[:100]}...")
                
        except Exception as e:
            print(f"   ❌ ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n🎯 TESTING COMPLETED")
    print("=" * 50)

if __name__ == "__main__":
    test_render_fixes()