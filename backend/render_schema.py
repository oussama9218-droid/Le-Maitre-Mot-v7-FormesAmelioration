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
    
    # ========== UTILITY FUNCTIONS FOR DRAWING GEOMETRIC ELEMENTS ==========
    
    def draw_point(self, ax, x, y, label="", label_offset=(0.2, 0.2), color='red', size=6):
        """Draw a point with optional label"""
        ax.plot(x, y, 'o', color=color, markersize=size)
        if label:
            ax.text(x + label_offset[0], y + label_offset[1], label, 
                   fontsize=12, fontweight='bold', ha='center', va='center')
    
    def draw_segment(self, ax, x1, y1, x2, y2, color='blue', linewidth=2, style='-'):
        """Draw a line segment between two points"""
        ax.plot([x1, x2], [y1, y2], color=color, linewidth=linewidth, linestyle=style)
    
    def draw_len_label(self, ax, x1, y1, x2, y2, length, offset=0.3):
        """Draw a length label at the midpoint of a segment"""
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        
        # Calculate perpendicular offset for label positioning
        dx, dy = x2 - x1, y2 - y1
        length_seg = np.sqrt(dx**2 + dy**2)
        if length_seg > 0:
            # Perpendicular vector
            perp_x, perp_y = -dy / length_seg, dx / length_seg
            label_x = mid_x + perp_x * offset
            label_y = mid_y + perp_y * offset
        else:
            label_x, label_y = mid_x, mid_y + offset
        
        ax.text(label_x, label_y, f'{length} cm', fontsize=10, ha='center', va='center',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8, edgecolor='gray'))
    
    def draw_right_angle(self, ax, vertex_x, vertex_y, p1_x, p1_y, p2_x, p2_y, size=0.3):
        """Draw a right angle marker at vertex between two points"""
        # Vectors from vertex to the two points
        v1_x, v1_y = p1_x - vertex_x, p1_y - vertex_y
        v2_x, v2_y = p2_x - vertex_x, p2_y - vertex_y
        
        # Normalize vectors
        len1 = np.sqrt(v1_x**2 + v1_y**2)
        len2 = np.sqrt(v2_x**2 + v2_y**2)
        
        if len1 > 0 and len2 > 0:
            v1_x, v1_y = v1_x / len1 * size, v1_y / len1 * size
            v2_x, v2_y = v2_x / len2 * size, v2_y / len2 * size
            
            # Draw right angle square
            corner_x = vertex_x + v1_x + v2_x
            corner_y = vertex_y + v1_y + v2_y
            
            square_x = [vertex_x, vertex_x + v1_x, corner_x, vertex_x + v2_x, vertex_x]
            square_y = [vertex_y, vertex_y + v1_y, corner_y, vertex_y + v2_y, vertex_y]
            
            ax.plot(square_x, square_y, 'k-', linewidth=1)
    
    def draw_angle_arc(self, ax, vertex_x, vertex_y, p1_x, p1_y, p2_x, p2_y, radius=0.5, label=""):
        """Draw an arc to mark an angle"""
        import math
        
        # Calculate angles
        angle1 = math.atan2(p1_y - vertex_y, p1_x - vertex_x)
        angle2 = math.atan2(p2_y - vertex_y, p2_x - vertex_x)
        
        # Ensure angle2 > angle1
        if angle2 < angle1:
            angle2 += 2 * math.pi
        
        # Create arc
        angles = np.linspace(angle1, angle2, 50)
        arc_x = vertex_x + radius * np.cos(angles)
        arc_y = vertex_y + radius * np.sin(angles)
        
        ax.plot(arc_x, arc_y, 'k-', linewidth=1)
        
        # Add label if provided
        if label:
            mid_angle = (angle1 + angle2) / 2
            label_x = vertex_x + (radius + 0.2) * math.cos(mid_angle)
            label_y = vertex_y + (radius + 0.2) * math.sin(mid_angle)
            ax.text(label_x, label_y, label, fontsize=9, ha='center', va='center')
    
    def mark_parallel(self, ax, x1, y1, x2, y2, x3, y3, x4, y4, offset=0.1):
        """Mark two segments as parallel with arrow symbols"""
        # First segment midpoint and direction
        mid1_x, mid1_y = (x1 + x2) / 2, (y1 + y2) / 2
        dx1, dy1 = x2 - x1, y2 - y1
        len1 = np.sqrt(dx1**2 + dy1**2)
        
        # Second segment midpoint and direction  
        mid2_x, mid2_y = (x3 + x4) / 2, (y3 + y4) / 2
        dx2, dy2 = x4 - x3, y4 - y3
        len2 = np.sqrt(dx2**2 + dy2**2)
        
        if len1 > 0 and len2 > 0:
            # Perpendicular vectors for offset
            perp1_x, perp1_y = -dy1 / len1 * offset, dx1 / len1 * offset
            perp2_x, perp2_y = -dy2 / len2 * offset, dx2 / len2 * offset
            
            # Draw parallel marks (double arrows)
            for i, mult in enumerate([-0.1, 0.1]):
                # First segment marks
                mark1_x = mid1_x + perp1_x + mult * dx1 / len1 * 0.2
                mark1_y = mid1_y + perp1_y + mult * dy1 / len1 * 0.2
                ax.plot([mark1_x - perp1_x*0.5, mark1_x + perp1_x*0.5], 
                       [mark1_y - perp1_y*0.5, mark1_y + perp1_y*0.5], 'k-', linewidth=2)
                
                # Second segment marks
                mark2_x = mid2_x + perp2_x + mult * dx2 / len2 * 0.2
                mark2_y = mid2_y + perp2_y + mult * dy2 / len2 * 0.2
                ax.plot([mark2_x - perp2_x*0.5, mark2_x + perp2_x*0.5], 
                       [mark2_y - perp2_y*0.5, mark2_y + perp2_y*0.5], 'k-', linewidth=2)
    
    def mark_equal(self, ax, x1, y1, x2, y2, x3, y3, x4, y4, marks=1):
        """Mark two segments as equal with tick marks"""
        # First segment midpoint and perpendicular
        mid1_x, mid1_y = (x1 + x2) / 2, (y1 + y2) / 2
        dx1, dy1 = x2 - x1, y2 - y1
        len1 = np.sqrt(dx1**2 + dy1**2)
        
        # Second segment midpoint and perpendicular
        mid2_x, mid2_y = (x3 + x4) / 2, (y3 + y4) / 2
        dx2, dy2 = x4 - x3, y4 - y3
        len2 = np.sqrt(dx2**2 + dy2**2)
        
        if len1 > 0 and len2 > 0:
            # Perpendicular vectors
            perp1_x, perp1_y = -dy1 / len1 * 0.15, dx1 / len1 * 0.15
            perp2_x, perp2_y = -dy2 / len2 * 0.15, dx2 / len2 * 0.15
            
            # Draw equal marks
            for i in range(marks):
                offset = (i - (marks-1)/2) * 0.1
                
                # First segment marks
                mark1_x = mid1_x + offset * dx1 / len1
                mark1_y = mid1_y + offset * dy1 / len1
                ax.plot([mark1_x - perp1_x, mark1_x + perp1_x], 
                       [mark1_y - perp1_y, mark1_y + perp1_y], 'k-', linewidth=2)
                
                # Second segment marks
                mark2_x = mid2_x + offset * dx2 / len2
                mark2_y = mid2_y + offset * dy2 / len2
                ax.plot([mark2_x - perp2_x, mark2_x + perp2_x], 
                       [mark2_y - perp2_y, mark2_y + perp2_y], 'k-', linewidth=2)
    
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
        fig, ax = plt.subplots(figsize=(4, 4))
        
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
        
        # Draw polygon outline and fill
        try:
            triangle_coords = [coords[p] for p in points] + [coords[points[0]]]
        except KeyError as e:
            logger.error(f"Unexpected KeyError after validation: {e}")
            return ""
        
        xs, ys = zip(*triangle_coords)
        ax.plot(xs, ys, 'b-', linewidth=2)
        ax.fill(xs[:-1], ys[:-1], alpha=0.3, color='lightblue')
        
        # Draw points using utility function
        for point, (x, y) in coords.items():
            self.draw_point(ax, x, y, point, label_offset=(-0.2, 0.2))
        
        # Draw segments with lengths using utility functions
        segments = data.get("segments", [])
        for segment in segments:
            if len(segment) >= 3:
                p1, p2, props = segment[0], segment[1], segment[2]
                if p1 in coords and p2 in coords:
                    x1, y1 = coords[p1]
                    x2, y2 = coords[p2]
                    
                    # Draw segment
                    self.draw_segment(ax, x1, y1, x2, y2)
                    
                    # Add length label if provided
                    longueur = props.get("longueur")
                    if longueur:
                        self.draw_len_label(ax, x1, y1, x2, y2, longueur)
        
        # Mark right angles using utility function
        angles = data.get("angles", [])
        for angle in angles:
            if len(angle) >= 2:
                vertex, props = angle[0], angle[1]
                if props.get("angle_droit") and vertex in coords:
                    # Find two adjacent points to the vertex
                    vertex_x, vertex_y = coords[vertex]
                    adjacent_points = []
                    
                    for point in points:
                        if point != vertex and point in coords:
                            adjacent_points.append(point)
                    
                    if len(adjacent_points) >= 2:
                        p1_x, p1_y = coords[adjacent_points[0]]
                        p2_x, p2_y = coords[adjacent_points[1]]
                        self.draw_right_angle(ax, vertex_x, vertex_y, p1_x, p1_y, p2_x, p2_y)
        
        # Clean axes and auto-center
        ax.set_aspect('equal')
        ax.axis('off')
        ax.relim()
        ax.autoscale_view()
        ax.set_title('Triangle', fontsize=12, fontweight='bold', pad=10)
        
        return self._fig_to_svg(fig)
    
    def _render_triangle_rectangle(self, data: dict) -> str:
        """Render a right triangle with proper right angle marker"""
        fig, ax = plt.subplots(figsize=(4, 4))
        
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
        
        # Draw triangle outline and fill
        try:
            triangle_coords = [coords[p] for p in points[:3]] + [coords[points[0]]]  # Use only first 3 points
            xs, ys = zip(*triangle_coords)
            ax.plot(xs, ys, 'b-', linewidth=2)
            ax.fill(xs[:-1], ys[:-1], alpha=0.3, color='lightblue')
        except KeyError as e:
            logger.error(f"KeyError in triangle rectangle rendering: {e}")
            return ""
        
        # Draw points using utility function
        for point in points[:3]:  # Only label first 3 points
            if point in coords:
                x, y = coords[point]
                self.draw_point(ax, x, y, point, label_offset=(-0.2, 0.2))
        
        # Draw segments with lengths using utility functions
        segments = data.get("segments", [])
        for segment in segments:
            if len(segment) >= 3:
                p1, p2, props = segment[0], segment[1], segment[2]
                if p1 in coords and p2 in coords:
                    x1, y1 = coords[p1]
                    x2, y2 = coords[p2]
                    
                    # Draw segment
                    self.draw_segment(ax, x1, y1, x2, y2)
                    
                    # Add length label if provided
                    longueur = props.get("longueur")
                    if longueur:
                        self.draw_len_label(ax, x1, y1, x2, y2, longueur)
        
        # Mark right angles using utility function
        angles = data.get("angles", [])
        right_angle_marked = False
        
        for angle in angles:
            if len(angle) >= 2:
                vertex, props = angle[0], angle[1]
                if props.get("angle_droit") and vertex in coords:
                    vertex_x, vertex_y = coords[vertex]
                    
                    # Find adjacent points for right angle
                    adjacent_points = [p for p in points[:3] if p != vertex and p in coords]
                    if len(adjacent_points) >= 2:
                        p1_x, p1_y = coords[adjacent_points[0]]
                        p2_x, p2_y = coords[adjacent_points[1]]
                        self.draw_right_angle(ax, vertex_x, vertex_y, p1_x, p1_y, p2_x, p2_y)
                        right_angle_marked = True
        
        # If no explicit right angle marked, mark the right angle at the second point (B)
        if not right_angle_marked and len(points) >= 3:
            vertex = points[1]  # Usually B in triangle ABC
            if vertex in coords:
                vertex_x, vertex_y = coords[vertex]
                p1_x, p1_y = coords[points[0]]  # A
                p2_x, p2_y = coords[points[2]]  # C
                self.draw_right_angle(ax, vertex_x, vertex_y, p1_x, p1_y, p2_x, p2_y)
        
        # Clean axes and auto-center
        ax.set_aspect('equal')
        ax.axis('off')
        ax.relim()
        ax.autoscale_view()
        ax.set_title('Triangle Rectangle', fontsize=12, fontweight='bold', pad=10)
        
        return self._fig_to_svg(fig)
    
    def _render_rectangle(self, data: dict) -> str:
        """Render a rectangle"""
        fig, ax = plt.subplots(figsize=(4, 4))
        
        longueur = data.get("longueur", 6)
        largeur = data.get("largeur", 4)
        
        # Define rectangle corners
        coords = {
            'A': (0, largeur),     # Top-left
            'B': (0, 0),          # Bottom-left  
            'C': (longueur, 0),   # Bottom-right
            'D': (longueur, largeur)  # Top-right
        }
        
        # Draw rectangle using utility functions
        rect = patches.Rectangle((0, 0), longueur, largeur, 
                               facecolor='lightgreen', edgecolor='black', linewidth=2)
        ax.add_patch(rect)
        
        # Draw corner points
        for point, (x, y) in coords.items():
            self.draw_point(ax, x, y, point, label_offset=(0.2, 0.2), size=4)
        
        # Draw segments with lengths
        segments = [
            ('A', 'B', largeur, 'vertical'),
            ('B', 'C', longueur, 'horizontal'),
            ('C', 'D', largeur, 'vertical'),
            ('D', 'A', longueur, 'horizontal')
        ]
        
        for p1, p2, length, orientation in segments:
            x1, y1 = coords[p1]
            x2, y2 = coords[p2]
            
            # Draw length label
            if orientation == 'horizontal':
                if y1 == 0:  # Bottom edge
                    self.draw_len_label(ax, x1, y1, x2, y2, length, offset=-0.4)
                else:  # Top edge
                    self.draw_len_label(ax, x1, y1, x2, y2, length, offset=0.4)
            else:  # vertical
                if x1 == 0:  # Left edge
                    self.draw_len_label(ax, x1, y1, x2, y2, length, offset=-0.4)
                else:  # Right edge
                    self.draw_len_label(ax, x1, y1, x2, y2, length, offset=0.4)
        
        # Mark all corners as right angles
        for point in ['A', 'B', 'C', 'D']:
            vertex_x, vertex_y = coords[point]
            
            # Get adjacent points for each corner
            if point == 'A':
                p1_x, p1_y = coords['D']
                p2_x, p2_y = coords['B']
            elif point == 'B':
                p1_x, p1_y = coords['A']
                p2_x, p2_y = coords['C']
            elif point == 'C':
                p1_x, p1_y = coords['B']
                p2_x, p2_y = coords['D']
            else:  # D
                p1_x, p1_y = coords['C']
                p2_x, p2_y = coords['A']
            
            self.draw_right_angle(ax, vertex_x, vertex_y, p1_x, p1_y, p2_x, p2_y, size=0.2)
        
        # Clean axes and auto-center
        ax.set_aspect('equal')
        ax.axis('off')
        ax.relim()
        ax.autoscale_view()
        ax.set_title('Rectangle', fontsize=12, fontweight='bold', pad=10)
        
        return self._fig_to_svg(fig)
    
    def _render_carre(self, data: dict) -> str:
        """Render a square"""
        fig, ax = plt.subplots(figsize=(4, 4))
        
        cote = data.get("cote", 4)
        
        # Draw square
        square = patches.Rectangle((0, 0), cote, cote,
                                 facecolor='lightyellow', edgecolor='black', linewidth=2)
        ax.add_patch(square)
        
        # Add label
        ax.text(cote/2, -0.5, f'{cote} cm', fontsize=12, ha='center')
        
        # Clean axes and auto-center
        ax.set_aspect('equal')
        ax.axis('off')
        ax.relim()
        ax.autoscale_view()
        ax.set_title('Carré', fontsize=12, fontweight='bold', pad=10)
        
        return self._fig_to_svg(fig)
    
    def _render_cercle(self, data: dict) -> str:
        """Render a circle"""
        fig, ax = plt.subplots(figsize=(4, 4))
        
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
        
        # Clean axes and auto-center
        ax.set_aspect('equal')
        ax.axis('off')
        ax.relim()
        ax.autoscale_view()
        ax.set_title('Cercle', fontsize=12, fontweight='bold', pad=10)
        
        return self._fig_to_svg(fig)
    
    def _render_pyramide(self, data: dict) -> str:
        """Render a pyramid"""
        fig, ax = plt.subplots(figsize=(4, 4))
        
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
        
        # Clean axes and auto-center
        ax.set_aspect('equal')
        ax.axis('off')
        ax.relim()
        ax.autoscale_view()
        ax.set_title('Pyramide', fontsize=12, fontweight='bold', pad=10)
        
        return self._fig_to_svg(fig)
    
    def _fig_to_svg(self, fig) -> str:
        """Convert matplotlib figure to SVG string with border"""
        svg_buffer = StringIO()
        fig.savefig(svg_buffer, format='svg', bbox_inches='tight', 
                   facecolor='white', edgecolor='none', dpi=100)
        plt.close(fig)  # Free memory
        
        svg_content = svg_buffer.getvalue()
        svg_buffer.close()
        
        # Add light gray border to SVG
        if '<svg' in svg_content and '>' in svg_content:
            # Find the opening svg tag and add border styling
            start_idx = svg_content.find('<svg')
            end_idx = svg_content.find('>', start_idx) + 1
            svg_tag = svg_content[start_idx:end_idx]
            
            # Add border styling to the SVG
            if 'style=' in svg_tag:
                # Add to existing style
                svg_tag = svg_tag.replace('style="', 'style="border: 1px solid #ccc; ')
            else:
                # Add new style attribute
                svg_tag = svg_tag.replace('>', ' style="border: 1px solid #ccc; background: white;">')
            
            svg_content = svg_content[:start_idx] + svg_tag + svg_content[end_idx:]
        
        return svg_content
    
    def _render_generic_polygon(self, data: dict) -> str:
        """Generic fallback renderer for unsupported schema types"""
        fig, ax = plt.subplots(figsize=(4, 4))
        
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
                
                # Clean axes and auto-center
                ax.set_aspect('equal')
                ax.axis('off')
                ax.relim()
                ax.autoscale_view()
                ax.set_title(f'{schema_type.title()} (générique)', fontsize=12, fontweight='bold', pad=10)
                
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