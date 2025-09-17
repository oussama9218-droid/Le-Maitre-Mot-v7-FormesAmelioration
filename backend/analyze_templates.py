#!/usr/bin/env python3
"""
Analyze templates to identify which ones properly display schema_svg
"""

import os
from pathlib import Path

def analyze_template(template_path):
    """Analyze a template for schema_svg display"""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if template has HTML structure
        has_html_structure = '<body>' in content and '</body>' in content
        
        # Check if template has exercise loop
        has_exercise_loop = 'for exercise in' in content or 'for exercice in' in content
        
        # Check if template displays schema_svg
        has_schema_display = '{{ exercise.schema_svg|safe }}' in content or '{{ exercice.schema_svg|safe }}' in content
        
        # Check if template has conditional schema_svg
        has_conditional_schema = ('{% if exercise.schema_svg %}' in content or 
                                '{% if exercice.schema_svg %}' in content)
        
        return {
            'name': template_path.name,
            'has_html_structure': has_html_structure,
            'has_exercise_loop': has_exercise_loop,
            'has_schema_display': has_schema_display,
            'has_conditional_schema': has_conditional_schema,
            'is_complete': has_html_structure and has_exercise_loop,
            'schema_ready': has_schema_display and has_conditional_schema
        }
        
    except Exception as e:
        return {
            'name': template_path.name,
            'error': str(e)
        }

def main():
    """Analyze all templates"""
    templates_dir = Path(__file__).parent / 'templates'
    
    print("🔍 ANALYZING TEMPLATES FOR SCHEMA_SVG DISPLAY")
    print("=" * 60)
    
    template_files = list(templates_dir.glob('*.html'))
    
    complete_templates = []
    incomplete_templates = []
    schema_ready_templates = []
    needs_schema_code = []
    
    for template_path in sorted(template_files):
        result = analyze_template(template_path)
        
        if 'error' in result:
            print(f"❌ {result['name']}: ERROR - {result['error']}")
            continue
            
        status = []
        if result['is_complete']:
            complete_templates.append(result['name'])
            if result['schema_ready']:
                schema_ready_templates.append(result['name'])
                status.append("✅ SCHEMA READY")
            else:
                needs_schema_code.append(result['name'])
                status.append("⚠️ NEEDS SCHEMA CODE")
        else:
            incomplete_templates.append(result['name'])
            status.append("❌ INCOMPLETE")
        
        if result['has_html_structure']:
            status.append("HTML")
        if result['has_exercise_loop']:
            status.append("LOOP")
        if result['has_schema_display']:
            status.append("DISPLAY")
        if result['has_conditional_schema']:
            status.append("CONDITIONAL")
            
        print(f"{result['name']:30} {' | '.join(status)}")
    
    print("\n" + "📊 SUMMARY")
    print("=" * 40)
    print(f"Total templates: {len(template_files)}")
    print(f"Complete templates: {len(complete_templates)}")
    print(f"Schema ready: {len(schema_ready_templates)}")
    print(f"Need schema code: {len(needs_schema_code)}")
    print(f"Incomplete templates: {len(incomplete_templates)}")
    
    if needs_schema_code:
        print(f"\n🔧 TEMPLATES NEEDING SCHEMA CODE:")
        for template in needs_schema_code:
            print(f"   - {template}")
    
    if incomplete_templates:
        print(f"\n❌ INCOMPLETE TEMPLATES (no HTML structure):")
        for template in incomplete_templates:
            print(f"   - {template}")

if __name__ == "__main__":
    main()