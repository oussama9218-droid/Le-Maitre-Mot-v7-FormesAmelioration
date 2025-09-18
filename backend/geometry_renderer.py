"""
Geometry Renderer - Generate geometric figures as SVG from structured data
"""

import json
import re
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import numpy as np
from io import StringIO, BytesIO
import base64
from backend.logger import get_logger
from typing import Dict, Any, List, Tuple, Optional

logger = get_logger(__name__)


class GeometryRenderer:
    """Converts structured geometric data to SVG figures"""
    
    def __init__(self):
        # Configure matplotlib for high-quality geometric rendering
        plt.rcParams.update({
            'font.size': 12,
            'font.family': 'serif',
            'mathtext.fontset': 'cm',
            'axes.linewidth': 1.2,
            'lines.linewidth': 1.5
        })
        
        # Standard colors and styles
        self.colors = {
            'line': '#000000',
            'point': '#FF0000',
            'text': '#000000',
            'construction': '#808080',
            'highlight': '#0066CC'
        }
        
        self.figure_renderers = {
            'triangle_rectangle': self._render_right_triangle,
            'triangle': self._render_triangle,
            'carre': self._render_square,
            'rectangle': self._render_rectangle,
            'cercle': self._render_circle,
            'parallelogramme': self._render_parallelogram
        }
    
    def _create_figure(self, width: float = 8, height: float = 6) -> Tuple[plt.Figure, plt.Axes]:
        """Create a clean matplotlib figure for geometric rendering"""
        fig, ax = plt.subplots(figsize=(width, height))
        ax.set_aspect('equal')
        ax.axis('off')
        ax.grid(False)
        
        # Set clean limits
        ax.set_xlim(-1, width)
        ax.set_ylim(-1, height)
        
        return fig, ax
    
    def _add_point(self, ax: plt.Axes, x: float, y: float, label: str, 
                   offset: Tuple[float, float] = (0.2, 0.2)):
        """Add a labeled point to the figure"""
        # Draw point
        ax.plot(x, y, 'o', color=self.colors['point'], markersize=4, zorder=10)
        
        # Add label with offset
        ax.text(x + offset[0], y + offset[1], label, 
                fontsize=12, fontweight='bold', 
                color=self.colors['text'], zorder=11,
                ha='center', va='center')
    
    def _add_right_angle_marker(self, ax: plt.Axes, vertex: Tuple[float, float], 
                               p1: Tuple[float, float], p2: Tuple[float, float], 
                               size: float = 0.3):
        """Add a right angle marker at vertex between p1 and p2"""
        vx, vy = vertex
        
        # Calculate unit vectors
        v1 = np.array([p1[0] - vx, p1[1] - vy])
        v2 = np.array([p2[0] - vx, p2[1] - vy])
        v1 = v1 / np.linalg.norm(v1) * size
        v2 = v2 / np.linalg.norm(v2) * size
        
        # Create square marker
        square_corner = np.array([vx, vy])
        square_p1 = square_corner + v1
        square_p2 = square_corner + v2
        square_p3 = square_corner + v1 + v2
        
        square = plt.Polygon([square_corner, square_p1, square_p3, square_p2], 
                           fill=False, edgecolor=self.colors['line'], 
                           linewidth=1, zorder=5)
        ax.add_patch(square)
    
    def _add_distance_mark(self, ax: plt.Axes, p1: Tuple[float, float], 
                          p2: Tuple[float, float], label: str, 
                          offset: float = 0.2, side: str = 'auto'):
        """Add distance marking between two points"""
        x1, y1 = p1
        x2, y2 = p2
        
        # Calculate midpoint
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        
        # Calculate perpendicular offset
        dx = x2 - x1
        dy = y2 - y1
        length = np.sqrt(dx**2 + dy**2)
        
        if length > 0:
            # Perpendicular unit vector
            perp_x = -dy / length * offset
            perp_y = dx / length * offset
            
            # Add small marks at both ends
            mark_size = 0.1
            ax.plot([x1 + perp_x - mark_size*perp_y, x1 + perp_x + mark_size*perp_y], 
                   [y1 + perp_y + mark_size*perp_x, y1 + perp_y - mark_size*perp_x], 
                   color=self.colors['line'], linewidth=1.5)
            ax.plot([x2 + perp_x - mark_size*perp_y, x2 + perp_x + mark_size*perp_y], 
                   [y2 + perp_y + mark_size*perp_x, y2 + perp_y - mark_size*perp_x], 
                   color=self.colors['line'], linewidth=1.5)
            
            # Add label at midpoint with offset
            ax.text(mid_x + perp_x, mid_y + perp_y, label, 
                   fontsize=10, fontweight='normal',
                   color=self.colors['text'], ha='center', va='center',
                   bbox=dict(boxstyle="round,pad=0.2", facecolor='white', 
                            edgecolor='none', alpha=0.8))
    
    def _render_right_triangle_to_figure(self, fig: plt.Figure, ax: plt.Axes, data: Dict[str, Any]):
        """Render a right triangle with labeled vertices to existing figure"""
        
        # Default coordinates for right triangle
        points = data.get('points', ['A', 'B', 'C'])
        angle_droit = data.get('angle_droit', points[1] if len(points) > 1 else 'B')
        
        # Position coordinates
        coords = {}
        if angle_droit == points[0]:  # A is right angle
            coords = {points[0]: (1, 1), points[1]: (4, 1), points[2]: (1, 3.5)}
        elif angle_droit == points[1]:  # B is right angle  
            coords = {points[0]: (1, 3.5), points[1]: (1, 1), points[2]: (4, 1)}
        else:  # C is right angle
            coords = {points[0]: (1, 1), points[1]: (1, 3.5), points[2]: (4, 1)}
        
        # Draw triangle
        triangle_coords = [coords[p] for p in points] + [coords[points[0]]]
        xs, ys = zip(*triangle_coords)
        ax.plot(xs, ys, color=self.colors['line'], linewidth=2, zorder=1)
        
        # Add points and labels
        for point, coord in coords.items():
            self._add_point(ax, coord[0], coord[1], point)
        
        # Add right angle marker
        right_vertex = coords[angle_droit]
        other_points = [p for p in points if p != angle_droit]
        if len(other_points) >= 2:
            p1_coord = coords[other_points[0]]
            p2_coord = coords[other_points[1]]
            self._add_right_angle_marker(ax, right_vertex, p1_coord, p2_coord)
        
        # Add distance marks if specified
        distance_marks = data.get('marques_distance', [])
        for mark in distance_marks:
            # Parse "AB=5cm" or "AB=BC" format
            if '=' in mark:
                sides_part = mark.split('=')[0]
                label = mark
                
                if len(sides_part) == 2:
                    p1, p2 = sides_part[0], sides_part[1]
                    if p1 in coords and p2 in coords:
                        self._add_distance_mark(ax, coords[p1], coords[p2], label)
    
    def _render_right_triangle(self, data: Dict[str, Any]) -> str:
        """Render a right triangle with labeled vertices"""
        fig, ax = self._create_figure(6, 5)
        self._render_right_triangle_to_figure(fig, ax, data)
        return self._figure_to_svg(fig)
    
    def _render_triangle(self, data: Dict[str, Any]) -> str:
        """Render a general triangle"""
        fig, ax = self._create_figure(6, 5)
        
        points = data.get('points', ['A', 'B', 'C'])
        
        # Default equilateral triangle coordinates
        coords = {
            points[0]: (1.5, 1),
            points[1]: (4.5, 1), 
            points[2]: (3, 3.5)
        }
        
        # Draw triangle
        triangle_coords = [coords[p] for p in points] + [coords[points[0]]]
        xs, ys = zip(*triangle_coords)
        ax.plot(xs, ys, color=self.colors['line'], linewidth=2, zorder=1)
        
        # Add points and labels
        for point, coord in coords.items():
            self._add_point(ax, coord[0], coord[1], point)
        
        return self._figure_to_svg(fig)
    
    def _render_square(self, data: Dict[str, Any]) -> str:
        """Render a square"""
        fig, ax = self._create_figure(5, 5)
        
        points = data.get('points', ['A', 'B', 'C', 'D'])
        
        # Square coordinates
        coords = {
            points[0]: (1, 1),
            points[1]: (3.5, 1),
            points[2]: (3.5, 3.5),
            points[3]: (1, 3.5)
        }
        
        # Draw square
        square_coords = [coords[p] for p in points] + [coords[points[0]]]
        xs, ys = zip(*square_coords)
        ax.plot(xs, ys, color=self.colors['line'], linewidth=2, zorder=1)
        
        # Add points and labels
        for point, coord in coords.items():
            self._add_point(ax, coord[0], coord[1], point)
        
        return self._figure_to_svg(fig)
    
    def _render_rectangle(self, data: Dict[str, Any]) -> str:
        """Render a rectangle"""
        fig, ax = self._create_figure(6, 4)
        
        points = data.get('points', ['A', 'B', 'C', 'D'])
        
        # Rectangle coordinates
        coords = {
            points[0]: (1, 1),
            points[1]: (4.5, 1),
            points[2]: (4.5, 2.5),
            points[3]: (1, 2.5)
        }
        
        # Draw rectangle
        rect_coords = [coords[p] for p in points] + [coords[points[0]]]
        xs, ys = zip(*rect_coords)
        ax.plot(xs, ys, color=self.colors['line'], linewidth=2, zorder=1)
        
        # Add points and labels
        for point, coord in coords.items():
            self._add_point(ax, coord[0], coord[1], point)
        
        return self._figure_to_svg(fig)
    
    def _render_circle(self, data: Dict[str, Any]) -> str:
        """Render a circle with center and radius"""
        fig, ax = self._create_figure(5, 5)
        
        center_label = data.get('centre', 'O')
        rayon = data.get('rayon', 1.5)
        
        # Circle center
        center_coord = (2.5, 2.5)
        
        # Draw circle
        circle = plt.Circle(center_coord, rayon, fill=False, 
                          color=self.colors['line'], linewidth=2)
        ax.add_patch(circle)
        
        # Add center point
        self._add_point(ax, center_coord[0], center_coord[1], center_label)
        
        # Add radius line if specified
        if data.get('montrer_rayon', True):
            radius_end = (center_coord[0] + rayon, center_coord[1])
            ax.plot([center_coord[0], radius_end[0]], 
                   [center_coord[1], radius_end[1]], 
                   color=self.colors['construction'], 
                   linewidth=1.5, linestyle='--')
            
            # Add radius label
            mid_radius = ((center_coord[0] + radius_end[0])/2, 
                         (center_coord[1] + radius_end[1])/2)
            radius_label = data.get('label_rayon', 'r')
            ax.text(mid_radius[0], mid_radius[1] + 0.2, radius_label, 
                   fontsize=10, ha='center', va='center',
                   bbox=dict(boxstyle="round,pad=0.2", facecolor='white', 
                            edgecolor='none', alpha=0.8))
        
        return self._figure_to_svg(fig)
    
    def _render_parallelogram(self, data: Dict[str, Any]) -> str:
        """Render a parallelogram"""
        fig, ax = self._create_figure(6, 4)
        
        points = data.get('points', ['A', 'B', 'C', 'D'])
        
        # Parallelogram coordinates
        coords = {
            points[0]: (1, 1),
            points[1]: (4, 1),
            points[2]: (4.5, 2.5),
            points[3]: (1.5, 2.5)
        }
        
        # Draw parallelogram
        para_coords = [coords[p] for p in points] + [coords[points[0]]]
        xs, ys = zip(*para_coords)
        ax.plot(xs, ys, color=self.colors['line'], linewidth=2, zorder=1)
        
        # Add points and labels
        for point, coord in coords.items():
            self._add_point(ax, coord[0], coord[1], point)
        
        return self._figure_to_svg(fig)
    
    def _figure_to_svg(self, fig: plt.Figure) -> str:
        """Convert matplotlib figure to SVG string"""
        svg_buffer = StringIO()
        fig.savefig(svg_buffer, format='svg', bbox_inches='tight', 
                   pad_inches=0.1, transparent=True, dpi=150)
        plt.close(fig)
        
        svg_content = svg_buffer.getvalue()
        
        # Clean up SVG content
        svg_content = re.sub(r'<\?xml[^>]*\?>', '', svg_content)
        svg_content = re.sub(r'<!DOCTYPE[^>]*>', '', svg_content)
        
        return svg_content.strip()
    
    def _figure_to_base64(self, fig: plt.Figure) -> str:
        """Convert matplotlib figure to Base64 encoded PNG for web display"""
        try:
            # Save figure to BytesIO buffer as PNG
            buf = BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', 
                       pad_inches=0.1, transparent=True, dpi=150,
                       facecolor='white', edgecolor='none')
            plt.close(fig)
            
            # Get PNG data and encode to Base64
            buf.seek(0)
            png_data = buf.getvalue()
            base64_string = base64.b64encode(png_data).decode('utf-8')
            
            return base64_string
            
        except Exception as e:
            logger.error(f"Error converting figure to Base64: {e}")
            plt.close(fig)
            return ""
    
    def render_geometric_figure(self, schema_data: Dict[str, Any]) -> str:
        """Render a geometric figure from structured data as SVG (for PDF)"""
        figure_type = schema_data.get('figure', 'triangle')
        
        if figure_type in self.figure_renderers:
            try:
                return self.figure_renderers[figure_type](schema_data)
            except Exception as e:
                logger.error(f"Error rendering {figure_type}: {e}")
                return f'<span style="color: red; font-style: italic;">[Erreur rendu figure: {figure_type}]</span>'
        else:
            logger.warning(f"Unknown figure type: {figure_type}")
            return f'<span style="color: orange; font-style: italic;">[Figure non supportée: {figure_type}]</span>'
    
    def render_geometry_to_base64(self, schema_data: Dict[str, Any]) -> str:
        """Render a geometric figure from structured data as Base64 PNG (for web display)"""
        figure_type = schema_data.get('figure', 'triangle')
        
        if figure_type in self.figure_renderers:
            try:
                # Create figure and render based on type
                if figure_type == 'triangle_rectangle':
                    fig, ax = self._create_figure(6, 5)
                    self._render_right_triangle_to_figure(fig, ax, schema_data)
                    return self._figure_to_base64(fig)
                
                elif figure_type == 'triangle':
                    fig, ax = self._create_figure(6, 5)
                    points = schema_data.get('points', ['A', 'B', 'C'])
                    # Default equilateral triangle coordinates
                    coords = {
                        points[0]: (1.5, 1),
                        points[1]: (4.5, 1), 
                        points[2]: (3, 3.5)
                    }
                    # Draw triangle
                    triangle_coords = [coords[p] for p in points] + [coords[points[0]]]
                    xs, ys = zip(*triangle_coords)
                    ax.plot(xs, ys, color=self.colors['line'], linewidth=2, zorder=1)
                    # Add points and labels
                    for point, coord in coords.items():
                        self._add_point(ax, coord[0], coord[1], point)
                    return self._figure_to_base64(fig)
                
                elif figure_type == 'carre':
                    fig, ax = self._create_figure(5, 5)
                    points = schema_data.get('points', ['A', 'B', 'C', 'D'])
                    # Square coordinates
                    coords = {
                        points[0]: (1, 1),
                        points[1]: (3.5, 1),
                        points[2]: (3.5, 3.5),
                        points[3]: (1, 3.5)
                    }
                    # Draw square
                    square_coords = [coords[p] for p in points] + [coords[points[0]]]
                    xs, ys = zip(*square_coords)
                    ax.plot(xs, ys, color=self.colors['line'], linewidth=2, zorder=1)
                    # Add points and labels
                    for point, coord in coords.items():
                        self._add_point(ax, coord[0], coord[1], point)
                    return self._figure_to_base64(fig)
                
                elif figure_type == 'rectangle':
                    fig, ax = self._create_figure(6, 4)
                    points = schema_data.get('points', ['A', 'B', 'C', 'D'])
                    # Rectangle coordinates
                    coords = {
                        points[0]: (1, 1),
                        points[1]: (4.5, 1),
                        points[2]: (4.5, 2.5),
                        points[3]: (1, 2.5)
                    }
                    # Draw rectangle
                    rect_coords = [coords[p] for p in points] + [coords[points[0]]]
                    xs, ys = zip(*rect_coords)
                    ax.plot(xs, ys, color=self.colors['line'], linewidth=2, zorder=1)
                    # Add points and labels
                    for point, coord in coords.items():
                        self._add_point(ax, coord[0], coord[1], point)
                    return self._figure_to_base64(fig)
                
                elif figure_type == 'cercle':
                    fig, ax = self._create_figure(5, 5)
                    center_label = schema_data.get('centre', 'O')
                    rayon = schema_data.get('rayon', 1.5)
                    # Circle center
                    center_coord = (2.5, 2.5)
                    # Draw circle
                    circle = plt.Circle(center_coord, rayon, fill=False, 
                                      color=self.colors['line'], linewidth=2)
                    ax.add_patch(circle)
                    # Add center point
                    self._add_point(ax, center_coord[0], center_coord[1], center_label)
                    # Add radius line if specified
                    if schema_data.get('montrer_rayon', True):
                        radius_end = (center_coord[0] + rayon, center_coord[1])
                        ax.plot([center_coord[0], radius_end[0]], 
                               [center_coord[1], radius_end[1]], 
                               color=self.colors['construction'], 
                               linewidth=1.5, linestyle='--')
                        # Add radius label
                        mid_radius = ((center_coord[0] + radius_end[0])/2, 
                                     (center_coord[1] + radius_end[1])/2)
                        radius_label = schema_data.get('label_rayon', 'r')
                        ax.text(mid_radius[0], mid_radius[1] + 0.2, radius_label, 
                               fontsize=10, ha='center', va='center',
                               bbox=dict(boxstyle="round,pad=0.2", facecolor='white', 
                                        edgecolor='none', alpha=0.8))
                    return self._figure_to_base64(fig)
                
                elif figure_type == 'parallelogramme':
                    fig, ax = self._create_figure(6, 4)
                    points = schema_data.get('points', ['A', 'B', 'C', 'D'])
                    # Parallelogram coordinates
                    coords = {
                        points[0]: (1, 1),
                        points[1]: (4, 1),
                        points[2]: (4.5, 2.5),
                        points[3]: (1.5, 2.5)
                    }
                    # Draw parallelogram
                    para_coords = [coords[p] for p in points] + [coords[points[0]]]
                    xs, ys = zip(*para_coords)
                    ax.plot(xs, ys, color=self.colors['line'], linewidth=2, zorder=1)
                    # Add points and labels
                    for point, coord in coords.items():
                        self._add_point(ax, coord[0], coord[1], point)
                    return self._figure_to_base64(fig)
                
                else:
                    # Fallback for any unsupported types
                    logger.warning(f"Figure type {figure_type} not yet implemented for Base64 rendering")
                    return ""
                
            except Exception as e:
                logger.error(f"Error rendering {figure_type} to Base64: {e}")
                return ""
        else:
            logger.warning(f"Unknown figure type for Base64: {figure_type}")
            return ""
    
    def extract_geometry_schema_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract the first geometric schema from text"""
        if not text:
            return None
        
        # Pattern to find geometric schema JSON
        pattern = r'\{\s*"type"\s*:\s*"schema_geometrique"[^}]*\}'
        match = re.search(pattern, text)
        
        if match:
            try:
                schema_json = match.group(0)
                schema_data = json.loads(schema_json)
                
                if schema_data.get('type') == 'schema_geometrique':
                    return schema_data
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in geometric schema: {e}")
                return None
            except Exception as e:
                logger.error(f"Error extracting geometric schema: {e}")
                return None
        
        return None
    
    def process_geometric_schemas_for_web(self, text: str) -> str:
        """Process text to replace geometric schemas with Base64 images for web display"""
        if not text:
            return text
        
        # Pattern to find geometric schema JSON
        pattern = r'\{\s*"type"\s*:\s*"schema_geometrique"[^}]*\}'
        
        def replace_schema_with_base64(match):
            try:
                schema_json = match.group(0)
                schema_data = json.loads(schema_json)
                
                if schema_data.get('type') == 'schema_geometrique':
                    base64_image = self.render_geometry_to_base64(schema_data)
                    
                    if base64_image:
                        return f'<div class="geometric-figure" style="text-align: center; margin: 15px 0;"><img src="data:image/png;base64,{base64_image}" alt="Schéma géométrique" style="max-width: 400px; height: auto;"/></div>'
                    else:
                        # Fallback to text description if Base64 generation fails
                        figure_name = schema_data.get('figure', 'figure')
                        points = ', '.join(schema_data.get('points', []))
                        return f'<div style="text-align: center; margin: 15px 0; padding: 10px; border: 1px dashed #ccc; font-style: italic;">[Schéma: {figure_name} avec points {points}]</div>'
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in geometric schema: {e}")
                return f'<span style="color: red; font-style: italic;">[Schéma géométrique invalide]</span>'
            except Exception as e:
                logger.error(f"Error processing geometric schema for web: {e}")
                return f'<span style="color: red; font-style: italic;">[Erreur schéma géométrique]</span>'
            
            return match.group(0)  # Return original if no processing needed
        
        result = re.sub(pattern, replace_schema_with_base64, text)
        return result
    
    def process_geometric_schemas(self, text: str) -> str:
        """Process text to find and render geometric schemas as SVG (for PDF)"""
        if not text:
            return text
        
        # Pattern to find geometric schema JSON
        pattern = r'\{\s*"type"\s*:\s*"schema_geometrique"[^}]*\}'
        
        def replace_schema(match):
            try:
                schema_json = match.group(0)
                schema_data = json.loads(schema_json)
                
                if schema_data.get('type') == 'schema_geometrique':
                    svg_content = self.render_geometric_figure(schema_data)
                    return f'<div class="geometric-figure" style="text-align: center; margin: 15px 0;">{svg_content}</div>'
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in geometric schema: {e}")
                return f'<span style="color: red; font-style: italic;">[Schéma géométrique invalide]</span>'
            except Exception as e:
                logger.error(f"Error processing geometric schema: {e}")
                return f'<span style="color: red; font-style: italic;">[Erreur schéma géométrique]</span>'
            
            return match.group(0)  # Return original if no processing needed
        
        result = re.sub(pattern, replace_schema, text)
        return result


# Global instance
geometry_renderer = GeometryRenderer()