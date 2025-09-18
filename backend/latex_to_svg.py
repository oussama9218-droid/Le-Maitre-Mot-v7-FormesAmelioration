"""
LaTeX to SVG Renderer - Convert LaTeX formulas to high-quality SVG images
"""

import re
import base64
import hashlib
from typing import Dict, Any
import matplotlib.pyplot as plt
import matplotlib.mathtext as mathtext
from io import BytesIO
from backend.logger import get_logger

logger = get_logger(__name__)


class LaTeXToSVGRenderer:
    """Converts LaTeX math expressions to SVG images for PDF generation"""
    
    def __init__(self, cache_dir: str = "/tmp/latex_cache"):
        self.cache_dir = cache_dir
        self.svg_cache = {}  # In-memory cache for this session
        
        # Configure matplotlib for high-quality math rendering
        plt.rcParams.update({
            'font.size': 14,
            'mathtext.fontset': 'cm',  # Computer Modern fonts (LaTeX standard)
            'mathtext.default': 'regular'
        })
    
    def _clean_latex(self, latex_code: str) -> str:
        """Clean and prepare LaTeX code for rendering"""
        # Remove outer \( \) or $ $ delimiters
        latex_code = latex_code.strip()
        if latex_code.startswith('\\(') and latex_code.endswith('\\)'):
            latex_code = latex_code[2:-2]
        elif latex_code.startswith('$') and latex_code.endswith('$'):
            latex_code = latex_code[1:-1]
        
        return latex_code.strip()
    
    def _latex_to_svg(self, latex_code: str) -> str:
        """Convert LaTeX code to SVG string"""
        try:
            # Create a figure with transparent background
            fig, ax = plt.subplots(figsize=(0.1, 0.1))
            ax.axis('off')
            fig.patch.set_alpha(0)
            
            # Render the LaTeX expression
            text = f"${latex_code}$"
            rendered = ax.text(0.5, 0.5, text, 
                             transform=ax.transAxes, 
                             fontsize=14,
                             ha='center', 
                             va='center',
                             math_fontfamily='cm')
            
            # Get the bounding box and adjust figure size
            fig.canvas.draw()
            bbox = rendered.get_window_extent(renderer=fig.canvas.get_renderer())
            bbox_inches = bbox.transformed(fig.dpi_scale_trans.inverted())
            
            # Set tight layout
            fig.set_size_inches(bbox_inches.width + 0.1, bbox_inches.height + 0.1)
            
            # Save to SVG
            svg_buffer = BytesIO()
            plt.savefig(svg_buffer, format='svg', 
                       bbox_inches='tight', 
                       pad_inches=0.02,
                       transparent=True,
                       dpi=300)
            
            plt.close(fig)
            
            # Get SVG content
            svg_content = svg_buffer.getvalue().decode('utf-8')
            
            # Clean up SVG content (remove XML declaration for inline use)
            svg_content = re.sub(r'<\?xml[^>]*\?>', '', svg_content)
            svg_content = re.sub(r'<!DOCTYPE[^>]*>', '', svg_content)
            
            return svg_content.strip()
            
        except Exception as e:
            logger.error(f"Error rendering LaTeX '{latex_code}': {e}")
            # Fallback to text representation
            return f'<span style="font-style: italic;">[{latex_code}]</span>'
    
    def _get_cache_key(self, latex_code: str) -> str:
        """Generate cache key for LaTeX code"""
        return hashlib.md5(latex_code.encode()).hexdigest()
    
    def render_latex_expression(self, latex_code: str) -> str:
        """Render a single LaTeX expression to SVG"""
        cleaned_latex = self._clean_latex(latex_code)
        cache_key = self._get_cache_key(cleaned_latex)
        
        # Check cache first
        if cache_key in self.svg_cache:
            return self.svg_cache[cache_key]
        
        # Render to SVG
        svg_content = self._latex_to_svg(cleaned_latex)
        
        # Cache the result
        self.svg_cache[cache_key] = svg_content
        
        return svg_content
    
    def convert_latex_to_svg(self, text: str) -> str:
        """Alias for convert_text_with_latex for compatibility"""
        return self.convert_text_with_latex(text)
    
    def convert_text_with_latex(self, text: str) -> str:
        """
        Convert text containing LaTeX expressions to HTML with embedded SVG
        Handles both inline \( ... \) and display $$ ... $$ math
        """
        if not text:
            return text
        
        # Process display math first ($$...$$)
        def replace_display_math(match):
            latex_code = match.group(1)
            svg_content = self.render_latex_expression(latex_code)
            return f'<div class="math-display" style="text-align: center; margin: 12px 0;">{svg_content}</div>'
        
        # Process inline math \(...\)
        def replace_inline_math(match):
            latex_code = match.group(1)
            svg_content = self.render_latex_expression(latex_code)
            return f'<span class="math-inline" style="display: inline-block; vertical-align: middle;">{svg_content}</span>'
        
        # Process single dollar math $...$
        def replace_dollar_math(match):
            latex_code = match.group(1)
            svg_content = self.render_latex_expression(latex_code)
            return f'<span class="math-inline" style="display: inline-block; vertical-align: middle;">{svg_content}</span>'
        
        result = text
        
        # Replace display math first ($$...$$)
        result = re.sub(r'\$\$([^$]+)\$\$', replace_display_math, result)
        
        # Replace inline math \(...\)
        result = re.sub(r'\\\(\s*([^)]+?)\s*\\\)', replace_inline_math, result)
        
        # Replace single dollar math $...$  (but not $$)
        result = re.sub(r'(?<!\$)\$([^$\n]+)\$(?!\$)', replace_dollar_math, result)
        
        return result
    
    def process_document_exercises(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process all exercises in a document to convert LaTeX expressions"""
        if not hasattr(document_data, 'exercises') or not document_data.exercises:
            return document_data
        
        # Process each exercise
        for exercise in document_data.exercises:
            # Process exercise statement
            if hasattr(exercise, 'enonce') and exercise.enonce:
                exercise.enonce = self.convert_text_with_latex(exercise.enonce)
            
            # Process QCM options if they exist
            if (hasattr(exercise, 'type') and exercise.type == 'qcm' and 
                hasattr(exercise, 'donnees') and exercise.donnees and 
                hasattr(exercise.donnees, 'options')):
                exercise.donnees.options = [
                    self.convert_text_with_latex(option) for option in exercise.donnees.options
                ]
            
            # Process solution if it exists
            if hasattr(exercise, 'solution') and exercise.solution:
                if hasattr(exercise.solution, 'etapes') and exercise.solution.etapes:
                    exercise.solution.etapes = [
                        self.convert_text_with_latex(step) for step in exercise.solution.etapes
                    ]
                if hasattr(exercise.solution, 'resultat') and exercise.solution.resultat:
                    exercise.solution.resultat = self.convert_text_with_latex(exercise.solution.resultat)
        
        return document_data


# Global instance for easy use
latex_renderer = LaTeXToSVGRenderer()