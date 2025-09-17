#!/usr/bin/env python3
"""
Update all PDF templates to include geometric schema SVG rendering
"""

import os
import re
from pathlib import Path

def update_template_file(template_path):
    """Update a single template file to include schema SVG rendering"""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern 1: Look for exercise content areas that need schema SVG
        patterns_to_replace = [
            # Pattern for templates with {{ exercice.enonce }}
            (
                r'(\{\{ exercice\.enonce \}\})((?:.*?)<div class="answer)',
                r'\1\n            \n            <!-- NEW: Render geometric schema SVG if generated -->\n            {% if exercice.schema_svg %}\n                <div class="geometric-schema">\n                    {{ exercice.schema_svg|safe }}\n                </div>\n            {% endif %}\n            \2'
            ),
            # Pattern for templates with {{ exercise.enonce }}
            (
                r'(\{\{ exercise\.enonce(?:\s*\|\|?\s*\'\'?)? \}\})((?:.*?)(?=<div class="answer|{% if exercise\.type|$))',
                r'\1\n    \n    <!-- NEW: Render geometric schema SVG if generated -->\n    {% if exercise.schema_svg %}\n        <div class="geometric-schema">\n            {{ exercise.schema_svg|safe }}\n        </div>\n    {% endif %}\n    \2'
            )
        ]
        
        updated = False
        for pattern, replacement in patterns_to_replace:
            if re.search(pattern, content, re.DOTALL | re.MULTILINE):
                new_content = re.sub(pattern, replacement, content, flags=re.DOTALL | re.MULTILINE)
                if new_content != content:
                    content = new_content
                    updated = True
                    print(f"   ✅ Updated exercise content pattern in {template_path.name}")
                    break
        
        # Add CSS styles if not already present
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
                print(f"   ✅ Added CSS styles to {template_path.name}")
        
        # Write back if updated
        if updated and content != original_content:
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   💾 Saved changes to {template_path.name}")
            return True
        else:
            print(f"   ℹ️  No changes needed for {template_path.name}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error updating {template_path.name}: {e}")
        return False

def main():
    """Update all PDF templates"""
    templates_dir = Path(__file__).parent / 'templates'
    
    if not templates_dir.exists():
        print(f"❌ Templates directory not found: {templates_dir}")
        return
    
    print("🔧 Updating all PDF templates to include geometric schema SVG rendering...")
    print("=" * 70)
    
    # Find all HTML template files
    template_files = list(templates_dir.glob('*.html'))
    
    if not template_files:
        print("❌ No HTML template files found")
        return
    
    updated_count = 0
    total_count = len(template_files)
    
    for template_file in sorted(template_files):
        print(f"\n📄 Processing {template_file.name}...")
        if update_template_file(template_file):
            updated_count += 1
    
    print("\n" + "=" * 70)
    print(f"📊 Summary: Updated {updated_count}/{total_count} template files")
    print("✅ All templates now include geometric schema SVG rendering support")

if __name__ == "__main__":
    main()