"""
Math Renderer - Convert LaTeX formulas to HTML/CSS for PDF generation
"""

import re
import html
from typing import Dict, Any


class MathRenderer:
    """Converts LaTeX math expressions to HTML/CSS for WeasyPrint PDF generation"""
    
    def __init__(self):
        # Common math patterns and their HTML/CSS replacements
        self.patterns = [
            # Fractions: \frac{numerator}{denominator}
            (r'\\frac\{([^}]+)\}\{([^}]+)\}', self._render_fraction),
            
            # Superscripts: ^{content} or ^content
            (r'\^(\{[^}]+\}|[^\s\(\)\[\]\\]+)', self._render_superscript),
            
            # Subscripts: _{content} or _content  
            (r'_(\{[^}]+\}|[^\s\(\)\[\]\\]+)', self._render_subscript),
            
            # Square roots: \sqrt{content}
            (r'\\sqrt\{([^}]+)\}', self._render_sqrt),
            
            # Basic operations and symbols
            (r'\\times', '×'),
            (r'\\div', '÷'),
            (r'\\pm', '±'),
            (r'\\mp', '∓'),
            (r'\\leq', '≤'),
            (r'\\geq', '≥'),
            (r'\\neq', '≠'),
            (r'\\approx', '≈'),
            (r'\\infty', '∞'),
            (r'\\pi', 'π'),
            (r'\\alpha', 'α'),
            (r'\\beta', 'β'),
            (r'\\gamma', 'γ'),
            (r'\\delta', 'δ'),
            (r'\\theta', 'θ'),
            (r'\\lambda', 'λ'),
            (r'\\mu', 'μ'),
            (r'\\sigma', 'σ'),
            
            # Parentheses sizing
            (r'\\left\(', '('),
            (r'\\right\)', ')'),
            (r'\\left\[', '['),
            (r'\\right\]', ']'),
        ]
    
    def _clean_braces(self, text: str) -> str:
        """Remove outer braces if present"""
        if text.startswith('{') and text.endswith('}'):
            return text[1:-1]
        return text
    
    def _render_fraction(self, match) -> str:
        """Convert \frac{num}{den} to HTML fraction"""
        numerator = self._clean_braces(match.group(1))
        denominator = self._clean_braces(match.group(2))
        
        # Recursively process numerator and denominator
        numerator = self._process_math_content(numerator)
        denominator = self._process_math_content(denominator)
        
        return f'''<span class="math-fraction">
            <span class="math-numerator">{numerator}</span>
            <span class="math-denominator">{denominator}</span>
        </span>'''
    
    def _render_superscript(self, match) -> str:
        """Convert ^{content} to HTML superscript"""
        content = self._clean_braces(match.group(1))
        content = self._process_math_content(content)
        return f'<sup class="math-superscript">{content}</sup>'
    
    def _render_subscript(self, match) -> str:
        """Convert _{content} to HTML subscript"""
        content = self._clean_braces(match.group(1))
        content = self._process_math_content(content)
        return f'<sub class="math-subscript">{content}</sub>'
    
    def _render_sqrt(self, match) -> str:
        """Convert \sqrt{content} to HTML square root"""
        content = self._clean_braces(match.group(1))
        content = self._process_math_content(content)
        return f'<span class="math-sqrt">√<span class="math-sqrt-content">{content}</span></span>'
    
    def _process_math_content(self, text: str) -> str:
        """Process mathematical content with pattern replacements"""
        result = text
        
        # Process patterns in the right order (most complex first)
        for pattern, replacement in self.patterns:
            if callable(replacement):
                # For complex patterns with functions
                result = re.sub(pattern, replacement, result)
            else:
                # For simple string replacements
                result = re.sub(pattern, replacement, result)
        
        return result
    
    def render_math_expressions(self, text: str) -> str:
        """
        Convert LaTeX math expressions in text to HTML/CSS
        Handles both inline \( ... \) and display $$ ... $$ math
        """
        if not text:
            return text
        
        # Process inline math: \( ... \)
        def replace_inline_math(match):
            math_content = match.group(1)
            processed = self._process_math_content(math_content)
            return f'<span class="math-inline">{processed}</span>'
        
        # Process display math: $$ ... $$
        def replace_display_math(match):
            math_content = match.group(1)
            processed = self._process_math_content(math_content)
            return f'<div class="math-display">{processed}</div>'
        
        # Process single $ math: $ ... $
        def replace_dollar_math(match):
            math_content = match.group(1)
            processed = self._process_math_content(math_content)
            return f'<span class="math-inline">{processed}</span>'
        
        result = text
        
        # Replace display math first ($$...$$)
        result = re.sub(r'\$\$([^$]+)\$\$', replace_display_math, result)
        
        # Replace inline math \(...\)
        result = re.sub(r'\\\(\s*([^)]+?)\s*\\\)', replace_inline_math, result)
        
        # Replace single dollar math $...$  (but not $$)
        result = re.sub(r'(?<!\$)\$([^$\n]+)\$(?!\$)', replace_dollar_math, result)
        
        return result
    
    def get_math_css(self) -> str:
        """Return CSS styles for math rendering"""
        return """
        /* Math Rendering Styles */
        .math-inline {
            display: inline-block;
            vertical-align: middle;
            font-family: "Times New Roman", serif;
            font-style: normal;
        }
        
        .math-display {
            display: block;
            text-align: center;
            margin: 12px 0;
            font-family: "Times New Roman", serif;
            font-style: normal;
        }
        
        .math-fraction {
            display: inline-block;
            vertical-align: middle;
            text-align: center;
            margin: 0 2px;
        }
        
        .math-numerator {
            display: block;
            border-bottom: 1px solid #000;
            padding: 0 4px 1px 4px;
            font-size: 0.9em;
            line-height: 1.1;
        }
        
        .math-denominator {
            display: block;
            padding: 1px 4px 0 4px;
            font-size: 0.9em;
            line-height: 1.1;
        }
        
        .math-superscript {
            font-size: 0.75em;
            vertical-align: super;
            line-height: 0;
        }
        
        .math-subscript {
            font-size: 0.75em;
            vertical-align: sub;
            line-height: 0;
        }
        
        .math-sqrt {
            display: inline-block;
            vertical-align: middle;
            font-size: 1.1em;
        }
        
        .math-sqrt .math-sqrt-content {
            border-top: 1px solid #000;
            padding-top: 1px;
            margin-left: 2px;
        }
        
        /* Ensure math elements don't break line spacing */
        .math-inline, .math-fraction, .math-sqrt {
            vertical-align: middle;
        }
        """


# Global instance for easy use
math_renderer = MathRenderer()