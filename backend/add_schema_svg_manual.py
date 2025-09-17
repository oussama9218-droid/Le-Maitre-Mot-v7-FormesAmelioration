#!/usr/bin/env python3
"""
Script to manually add schema_svg code to missing templates
"""

import os
import re
from pathlib import Path

def add_schema_svg_to_template(template_path):
    """Add schema_svg code to a template if missing"""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip if already has schema_svg
        if 'schema_svg' in content:
            print(f"   ✅ {template_path.name}: Already has schema_svg")
            return False
        
        original_content = content
        
        # Pattern to find where to insert schema_svg code
        patterns_to_try = [
            # Pattern 1: After {{ exercise.enonce or '' }}
            (
                r'(\{\{ exercise\.enonce(?:\s*or\s*\'\')?[ \}]*\}\})',
                r'\1\n    \n    <!-- NEW: Render geometric schema SVG if generated -->\n    {% if exercise.schema_svg %}\n        <div class="geometric-schema">\n            {{ exercise.schema_svg|safe }}\n        </div>\n    {% endif %}'
            ),
            # Pattern 2: After {{ exercice.enonce }}
            (
                r'(\{\{ exercice\.enonce \}\})',
                r'\1\n            \n            <!-- NEW: Render geometric schema SVG if generated -->\n            {% if exercice.schema_svg %}\n                <div class="geometric-schema">\n                    {{ exercice.schema_svg|safe }}\n                </div>\n            {% endif %}'
            ),
            # Pattern 3: After any enonce display
            (
                r'(<div[^>]*class="[^"]*exercise-text[^"]*"[^>]*>.*?\}\}</div>)',
                r'\1\n    \n    <!-- NEW: Render geometric schema SVG if generated -->\n    {% if exercise.schema_svg %}\n        <div class="geometric-schema">\n            {{ exercise.schema_svg|safe }}\n        </div>\n    {% endif %}'
            )
        ]
        
        # Try each pattern
        updated = False
        for pattern, replacement in patterns_to_try:
            if re.search(pattern, content, re.DOTALL):
                new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                if new_content != content:
                    content = new_content
                    updated = True
                    print(f"   ✅ {template_path.name}: Added schema_svg code")
                    break
        
        # Add CSS styles if not present
        css_pattern = r'\.geometric-schema\s*\{'
        if not re.search(css_pattern, content):
            # Find a good place to insert CSS (before closing </style>)
            style_insert_pattern = r'(\s*)(</style>)'
            css_to_add = '''
        /* NEW: Style for geometric schemas */
        .geometric-schema {
            text-align: center;
            margin: 20px 0;
            padding: 15px;
            border: 2px solid #333;
            background-color: #fafafa;
            border-radius: 8px;
        }
        
        .geometric-schema svg {
            max-width: 100%;
            height: auto;
        }
'''
            
            if re.search(style_insert_pattern, content):
                content = re.sub(style_insert_pattern, f'{css_to_add}\\1\\2', content)
                updated = True
                print(f"   ✅ {template_path.name}: Added CSS styles")
        
        # Write back if updated
        if updated and content != original_content:
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   💾 {template_path.name}: Saved changes")
            return True
        else:
            print(f"   ⚠️  {template_path.name}: Could not find suitable insertion point")
            return False
            
    except Exception as e:
        print(f"   ❌ {template_path.name}: Error - {e}")
        return False

def main():
    """Add schema_svg to all templates"""
    templates_dir = Path(__file__).parent / 'templates'
    
    print("🔧 Adding schema_svg code to missing templates...")
    print("=" * 60)
    
    # Templates that we know are missing schema_svg
    missing_templates = [
        'corrige_classique.html',
        'corrige_detaille.html', 
        'corrige_eleve.html',
        'corrige_minimal.html',
        'corrige_pro.html',
        'sujet_academique.html',
        'sujet_eleve.html',
        'sujet_minimal.html'
    ]
    
    updated_count = 0
    
    for template_name in missing_templates:
        template_path = templates_dir / template_name
        if template_path.exists():
            print(f"\n📄 Processing {template_name}...")
            if add_schema_svg_to_template(template_path):
                updated_count += 1
        else:
            print(f"\n❌ {template_name}: File not found")
    
    print(f"\n📊 Summary: Updated {updated_count}/{len(missing_templates)} templates")
    print("✅ Schema SVG code addition completed")

if __name__ == "__main__":
    main()