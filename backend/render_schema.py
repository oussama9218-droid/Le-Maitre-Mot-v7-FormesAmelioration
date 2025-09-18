"""
Schema Rendering Module - Convert JSON geometric schemas to SVG images
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from io import StringIO
import logging
from logger import get_logger, log_execution_time, log_schema_processing

logger = get_logger()

class SchemaRenderer:
    """Converts JSON schema descriptions to SVG figures"""
    
    def __init__(self):
        # Configure matplotlib for clean SVG output
        plt.rcParams.update({
            'font.size': 10,
            'font.family': 'sans-serif',
            'svg.fonttype': 'none',  # Keep text as text in SVG
            'figure.figsize': (4, 4),  # Fixed uniform size
            'figure.facecolor': 'white',  # White background
            'axes.facecolor': 'white',
            'savefig.facecolor': 'white',
            'savefig.edgecolor': 'none'
        })
    
    @log_execution_time("render_to_svg")
    def render_to_svg(self, schema_data: dict) -> str:
        """
        Convert schema JSON to SVG string
        Args:
            schema_data: JSON schema like {"type": "cylindre", "rayon": 3, "hauteur": 5}
        Returns:
            SVG string for embedding in HTML
        """
        if not schema_data or not isinstance(schema_data, dict):
            logger.debug("No schema data provided or invalid format")
            return ""
        
        schema_type = schema_data.get("type", "").lower()
        logger.info(
            "Starting SVG rendering",
            module_name="render_schema",
            func_name="render_to_svg", 
            schema_type=schema_type
        )
        
        try:
            if schema_type == "cylindre":
                return self._render_cylindre(schema_data)
            elif schema_type == "triangle":
                return self._render_triangle(schema_data)
            elif schema_type == "triangle_rectangle":
                return self._render_triangle_rectangle(schema_data)
            elif schema_type == "rectangle":
                return self._render_rectangle(schema_data)
            elif schema_type == "carre":
                return self._render_carre(schema_data)
            elif schema_type == "cercle":
                return self._render_cercle(schema_data)
            elif schema_type == "pyramide":
                return self._render_pyramide(schema_data)
            else:
                logger.warning(
                    "Unsupported schema type - falling back to generic polygon",
                    module_name="render_schema",
                    func_name="render_to_svg",
                    schema_type=schema_type,
                    status="unsupported_fallback"
                )
                # Try generic polygon fallback for unsupported types
                return self._render_generic_polygon(schema_data)
                
        except Exception as e:
            logger.error(
                "Error rendering schema",
                module_name="render_schema", 
                func_name="render_to_svg",
                schema_type=schema_type,
                error=str(e),
                schema_data_keys=list(schema_data.keys()) if isinstance(schema_data, dict) else "N/A",
                status="error",
                exc_info=True
            )
            log_schema_processing(schema_type, False)
            return ""
    
    def _render_cylindre(self, data: dict) -> str:
        """Render a cylinder with given radius and height"""
        fig, ax = plt.subplots(figsize=(4, 4))
        
        rayon = data.get("rayon", 3)
        hauteur = data.get("hauteur", 5)
        
        # Draw cylinder (side view)
        # Top ellipse
        ellipse_top = patches.Ellipse((0, hauteur), rayon*2, rayon*0.3, 
                                    facecolor='lightblue', edgecolor='black', linewidth=2)
        ax.add_patch(ellipse_top)
        
        # Bottom ellipse  
        ellipse_bottom = patches.Ellipse((0, 0), rayon*2, rayon*0.3,
                                       facecolor='lightblue', edgecolor='black', linewidth=2)
        ax.add_patch(ellipse_bottom)
        
        # Side lines
        ax.plot([-rayon, -rayon], [0, hauteur], 'k-', linewidth=2)
        ax.plot([rayon, rayon], [0, hauteur], 'k-', linewidth=2)
        
        # Add labels
        ax.text(rayon + 0.5, hauteur/2, f'h = {hauteur} cm', fontsize=12, ha='left')
        ax.text(0, -rayon*0.5, f'r = {rayon} cm', fontsize=12, ha='center')
        
        # Clean axes and auto-center
        ax.set_aspect('equal')
        ax.axis('off')
        ax.relim()
        ax.autoscale_view()
        ax.set_title('Cylindre', fontsize=12, fontweight='bold', pad=10)
        
        return self._fig_to_svg(fig)
    
    def _render_triangle(self, data: dict) -> str:
        """Render a triangle"""
        fig, ax = plt.subplots(figsize=(6, 6))
        
        # Get points or use defaults
        points = data.get("points", ["A", "B", "C"])
        
        # Generate coordinates for all points
        coords = {}
        
        # Create default coordinates based on number of points
        if len(points) == 3:
            # Standard triangle
            coords = {
                points[0]: (0, 3),    # A
                points[1]: (0, 0),    # B  
                points[2]: (4, 0)     # C
            }
        elif len(points) == 4:
            # Rectangle or quadrilateral
            coords = {
                points[0]: (0, 3),    # A
                points[1]: (0, 0),    # B  
                points[2]: (4, 0),    # C
                points[3]: (4, 3)     # D
            }
        else:
            # Generic polygon - arrange points in circle
            import math
            for i, point in enumerate(points):
                angle = 2 * math.pi * i / len(points)
                x = 3 * math.cos(angle)
                y = 3 * math.sin(angle)
                coords[point] = (x, y)
        
        # Override with custom coordinates if provided
        labels = data.get("labels", {})
        for point, coord_str in labels.items():
            if isinstance(coord_str, str):
                # Parse coordinate string like "(0,3)"
                try:
                    coord_str = coord_str.strip("()")
                    x, y = map(float, coord_str.split(","))
                    coords[point] = (x, y)
                except:
                    logger.warning(f"Failed to parse coordinate '{coord_str}' for point '{point}'")
        
        # Validate that we have coordinates for all points
        available_coords = {p: coords[p] for p in points if p in coords}
        missing_points = [p for p in points if p not in coords]
        
        if missing_points:
            logger.warning(
                "Missing coordinates for points, cannot render figure",
                module_name="render_schema",
                func_name="_render_triangle",
                missing_points=missing_points,
                available_points=list(coords.keys()),
                status="incomplete_data"
            )
            return ""  # Return empty SVG instead of crashing
        
        # Draw polygon (triangle or other) - now safe from KeyError
        try:
            triangle_coords = [coords[p] for p in points] + [coords[points[0]]]
        except KeyError as e:
            logger.error(f"Unexpected KeyError after validation: {e}")
            return ""
        xs, ys = zip(*triangle_coords)
        ax.plot(xs, ys, 'b-', linewidth=2)
        ax.fill(xs[:-1], ys[:-1], alpha=0.3, color='lightblue')
        
        # Add point labels
        for point, (x, y) in coords.items():
            ax.plot(x, y, 'ro', markersize=6)
            ax.text(x-0.2, y+0.2, point, fontsize=12, fontweight='bold')
        
        # Add segments with lengths
        segments = data.get("segments", [])
        for segment in segments:
            if len(segment) >= 3:
                p1, p2, props = segment[0], segment[1], segment[2]
                if p1 in coords and p2 in coords:
                    longueur = props.get("longueur")
                    if longueur:
                        x1, y1 = coords[p1]
                        x2, y2 = coords[p2]
                        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
                        ax.text(mid_x, mid_y-0.3, f'{longueur} cm', 
                               fontsize=10, ha='center', bbox=dict(boxstyle="round,pad=0.3", 
                               facecolor="white", alpha=0.8))
        
        # Mark right angles
        angles = data.get("angles", [])
        for angle in angles:
            if len(angle) >= 2:
                point, props = angle[0], angle[1]
                if props.get("angle_droit") and point in coords:
                    x, y = coords[point]
                    # Draw right angle marker
                    size = 0.3
                    ax.plot([x, x+size, x+size, x], [y, y, y+size, y+size], 'k-', linewidth=1)
        
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_title('Triangle', fontsize=14, fontweight='bold')
        
        return self._fig_to_svg(fig)
    
    def _render_triangle_rectangle(self, data: dict) -> str:
        """Render a right triangle with proper right angle marker"""
        fig, ax = plt.subplots(figsize=(6, 6))
        
        # Get points or use defaults
        points = data.get("points", ["A", "B", "C"])
        
        # Default right triangle coordinates (right angle at B)
        coords = {
            points[0]: (0, 4),    # A (top)
            points[1]: (0, 0),    # B (right angle)
            points[2]: (3, 0)     # C (right)
        }
        
        # Override with custom coordinates if provided
        labels = data.get("labels", {})
        for point, coord_str in labels.items():
            if isinstance(coord_str, str):
                try:
                    coord_str = coord_str.strip("()")
                    x, y = map(float, coord_str.split(","))
                    coords[point] = (x, y)
                except:
                    logger.warning(f"Failed to parse coordinate '{point}: {coord_str}'")
        
        # CRITICAL: Ensure we have coordinates for ALL points to prevent KeyError
        missing_points = [p for p in points if p not in coords]
        if missing_points:
            logger.warning(
                "Missing coordinates for triangle_rectangle points",
                module_name="render_schema",
                func_name="_render_triangle_rectangle", 
                missing_points=missing_points,
                available_points=list(coords.keys())
            )
            # Add missing points with fallback positions to prevent KeyError
            for i, point in enumerate(missing_points):
                coords[point] = (i * 2, i * 2)  # Simple fallback positioning
            logger.info(f"Added fallback coordinates for missing points: {missing_points}")
        
        # Draw triangle
        try:
            triangle_coords = [coords[p] for p in points[:3]] + [coords[points[0]]]  # Use only first 3 points
            xs, ys = zip(*triangle_coords)
            ax.plot(xs, ys, 'b-', linewidth=2)
            ax.fill(xs[:-1], ys[:-1], alpha=0.3, color='lightblue')
        except KeyError as e:
            logger.error(f"KeyError in triangle rectangle rendering: {e}")
            return ""
        
        # Add point labels
        for point in points[:3]:  # Only label first 3 points
            if point in coords:
                x, y = coords[point]
                ax.plot(x, y, 'ro', markersize=6)
                ax.text(x-0.2, y+0.2, point, fontsize=12, fontweight='bold')
        
        # Add segments with lengths
        segments = data.get("segments", [])
        for segment in segments:
            if len(segment) >= 3:
                p1, p2, props = segment[0], segment[1], segment[2]
                if p1 in coords and p2 in coords:
                    longueur = props.get("longueur")
                    if longueur:
                        x1, y1 = coords[p1]
                        x2, y2 = coords[p2]
                        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
                        ax.text(mid_x, mid_y-0.3, f'{longueur} cm', 
                               fontsize=10, ha='center', bbox=dict(boxstyle="round,pad=0.3", 
                               facecolor="white", alpha=0.8))
        
        # Mark right angles - more robust
        angles = data.get("angles", [])
        for angle in angles:
            if len(angle) >= 2:
                point, props = angle[0], angle[1]
                if props.get("angle_droit") and point in coords:
                    x, y = coords[point]
                    # Draw right angle marker
                    size = 0.3
                    ax.plot([x, x+size, x+size, x], [y, y, y+size, y+size], 'k-', linewidth=1)
        
        # If no explicit right angle marked, mark the right angle at the second point (B)
        if not angles and len(points) >= 2:
            point = points[1]  # Usually B in triangle ABC
            if point in coords:
                x, y = coords[point]
                size = 0.3
                ax.plot([x, x+size, x+size, x], [y, y, y+size, y+size], 'k-', linewidth=1)
        
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_title('Triangle Rectangle', fontsize=14, fontweight='bold')
        
        return self._fig_to_svg(fig)
    
    def _render_rectangle(self, data: dict) -> str:
        """Render a rectangle"""
        fig, ax = plt.subplots(figsize=(6, 4))
        
        longueur = data.get("longueur", 6)
        largeur = data.get("largeur", 4)
        
        # Draw rectangle
        rect = patches.Rectangle((0, 0), longueur, largeur, 
                               facecolor='lightgreen', edgecolor='black', linewidth=2)
        ax.add_patch(rect)
        
        # Add labels
        ax.text(longueur/2, -0.5, f'{longueur} cm', fontsize=12, ha='center')
        ax.text(-0.5, largeur/2, f'{largeur} cm', fontsize=12, ha='center', rotation=90)
        
        ax.set_xlim(-1, longueur+1)
        ax.set_ylim(-1, largeur+1)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title('Rectangle', fontsize=14, fontweight='bold')
        
        return self._fig_to_svg(fig)
    
    def _render_carre(self, data: dict) -> str:
        """Render a square"""
        fig, ax = plt.subplots(figsize=(5, 5))
        
        cote = data.get("cote", 4)
        
        # Draw square
        square = patches.Rectangle((0, 0), cote, cote,
                                 facecolor='lightyellow', edgecolor='black', linewidth=2)
        ax.add_patch(square)
        
        # Add label
        ax.text(cote/2, -0.5, f'{cote} cm', fontsize=12, ha='center')
        
        ax.set_xlim(-1, cote+1)
        ax.set_ylim(-1, cote+1)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title('Carré', fontsize=14, fontweight='bold')
        
        return self._fig_to_svg(fig)
    
    def _render_cercle(self, data: dict) -> str:
        """Render a circle"""
        fig, ax = plt.subplots(figsize=(6, 6))
        
        rayon = data.get("rayon", 3)
        
        # Draw circle
        circle = patches.Circle((0, 0), rayon, facecolor='lightcoral', 
                              edgecolor='black', linewidth=2, alpha=0.7)
        ax.add_patch(circle)
        
        # Draw radius line
        ax.plot([0, rayon], [0, 0], 'k--', linewidth=2)
        ax.text(rayon/2, 0.3, f'r = {rayon} cm', fontsize=12, ha='center')
        
        # Add center point
        ax.plot(0, 0, 'ko', markersize=6)
        ax.text(0.2, 0.2, 'O', fontsize=12, fontweight='bold')
        
        ax.set_xlim(-rayon*1.2, rayon*1.2)
        ax.set_ylim(-rayon*1.2, rayon*1.2)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title('Cercle', fontsize=14, fontweight='bold')
        
        return self._fig_to_svg(fig)
    
    def _render_pyramide(self, data: dict) -> str:
        """Render a pyramid"""
        fig, ax = plt.subplots(figsize=(6, 6))
        
        base = data.get("base", "carre")
        hauteur = data.get("hauteur", 5)
        
        if base == "carre":
            cote = data.get("cote", 4)
            
            # Draw square base
            base_coords = [(0, 0), (cote, 0), (cote, cote), (0, cote), (0, 0)]
            xs, ys = zip(*base_coords)
            ax.plot(xs, ys, 'k-', linewidth=2)
            
            # Draw pyramid edges to apex
            apex = (cote/2, hauteur + cote/2)
            corners = [(0, 0), (cote, 0), (cote, cote), (0, cote)]
            
            for corner in corners:
                ax.plot([corner[0], apex[0]], [corner[1], apex[1]], 'k-', linewidth=2)
            
            # Add labels
            ax.text(cote/2, -0.5, f'{cote} cm', fontsize=12, ha='center')
            ax.text(-0.5, cote/2, f'{cote} cm', fontsize=12, ha='center', rotation=90)
            ax.text(apex[0]+0.5, apex[1], f'h = {hauteur} cm', fontsize=12, ha='left')
            
            # Mark apex
            ax.plot(apex[0], apex[1], 'ro', markersize=6)
            ax.text(apex[0]+0.2, apex[1]+0.2, 'S', fontsize=12, fontweight='bold')
        
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title('Pyramide', fontsize=14, fontweight='bold')
        
        return self._fig_to_svg(fig)
    
    def _fig_to_svg(self, fig) -> str:
        """Convert matplotlib figure to SVG string"""
        svg_buffer = StringIO()
        fig.savefig(svg_buffer, format='svg', bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close(fig)  # Free memory
        
        svg_content = svg_buffer.getvalue()
        svg_buffer.close()
        
        return svg_content
    
    def _render_generic_polygon(self, data: dict) -> str:
        """Generic fallback renderer for unsupported schema types"""
        fig, ax = plt.subplots(figsize=(6, 6))
        
        schema_type = data.get("type", "unknown")
        points = data.get("points", [])
        
        if not points:
            logger.warning("No points provided for generic polygon")
            return ""
        
        # Create default coordinates in a circle
        import math
        coords = {}
        for i, point in enumerate(points):
            angle = 2 * math.pi * i / len(points)
            x = 3 * math.cos(angle)
            y = 3 * math.sin(angle)
            coords[point] = (x, y)
        
        # Override with provided coordinates
        labels = data.get("labels", {})
        for point, coord_str in labels.items():
            if isinstance(coord_str, str) and point in coords:
                try:
                    coord_str = coord_str.strip("()")
                    x, y = map(float, coord_str.split(","))
                    coords[point] = (x, y)
                except:
                    pass  # Keep default
        
        # Draw polygon
        if len(points) >= 3:
            try:
                polygon_coords = [coords[p] for p in points] + [coords[points[0]]]
                xs, ys = zip(*polygon_coords)
                ax.plot(xs, ys, 'b-', linewidth=2)
                ax.fill(xs[:-1], ys[:-1], alpha=0.2, color='lightgray')
                
                # Add point labels
                for point, (x, y) in coords.items():
                    ax.plot(x, y, 'ro', markersize=6)
                    ax.text(x-0.2, y+0.2, point, fontsize=12, fontweight='bold')
                
                ax.set_aspect('equal')
                ax.set_title(f'{schema_type.title()} (générique)', fontsize=14, fontweight='bold')
                
                logger.info(f"Generic polygon rendered for type: {schema_type}")
                return self._fig_to_svg(fig)
                
            except Exception as e:
                logger.error(f"Error in generic polygon rendering: {e}")
                return ""
        else:
            logger.warning(f"Not enough points for polygon: {len(points)}")
            return ""

# Global instance
schema_renderer = SchemaRenderer()