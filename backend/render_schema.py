"""
Schema Rendering Module - Convert JSON geometric schemas to SVG images
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from io import StringIO
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
    
    def draw_polygon(self, ax, points_coords, fill_color='lightblue', edge_color='blue', linewidth=2, alpha=0.3):
        """Draw a polygon with automatic closure"""
        if not points_coords or len(points_coords) < 3:
            logger.warning("draw_polygon: Need at least 3 points")
            return
        
        # Automatic closure - add first point at the end if not already closed
        closed_coords = points_coords.copy()
        if closed_coords[0] != closed_coords[-1]:
            closed_coords.append(closed_coords[0])
        
        # Extract x and y coordinates
        xs, ys = zip(*closed_coords)
        
        # Draw polygon outline
        ax.plot(xs, ys, color=edge_color, linewidth=linewidth)
        
        # Fill polygon
        if alpha > 0:
            ax.fill(xs[:-1], ys[:-1], color=fill_color, alpha=alpha)
    
    def draw_circle(self, ax, center_x, center_y, radius=None, point_on_circle=None, 
                   fill_color='lightcoral', edge_color='black', linewidth=2, alpha=0.7):
        """Draw a circle with center + radius OR center + point on circle"""
        
        if radius is not None:
            # Method 1: center + radius
            circle_radius = radius
        elif point_on_circle is not None:
            # Method 2: center + point on circle
            px, py = point_on_circle
            circle_radius = np.sqrt((px - center_x)**2 + (py - center_y)**2)
        else:
            logger.warning("draw_circle: Need either radius or point_on_circle")
            return
        
        # Draw circle using matplotlib patch
        circle = patches.Circle((center_x, center_y), circle_radius, 
                              facecolor=fill_color, edgecolor=edge_color, 
                              linewidth=linewidth, alpha=alpha)
        ax.add_patch(circle)
        
        return circle_radius  # Return calculated radius for further use
    
    # ========== ADVANCED GEOMETRIC ELEMENTS ==========
    
    def draw_height(self, ax, vertex_x, vertex_y, base_p1_x, base_p1_y, base_p2_x, base_p2_y, 
                   color='green', linewidth=1.5, symbol_size=0.15):
        """Draw height from vertex perpendicular to base with foot marker"""
        # Calculate foot of perpendicular
        # Vector from base_p1 to base_p2
        base_dx = base_p2_x - base_p1_x
        base_dy = base_p2_y - base_p1_y
        base_length_sq = base_dx**2 + base_dy**2
        
        if base_length_sq == 0:
            return  # Degenerate base
        
        # Vector from base_p1 to vertex
        vertex_dx = vertex_x - base_p1_x
        vertex_dy = vertex_y - base_p1_y
        
        # Project vertex onto base line
        t = (vertex_dx * base_dx + vertex_dy * base_dy) / base_length_sq
        foot_x = base_p1_x + t * base_dx
        foot_y = base_p1_y + t * base_dy
        
        # Draw height line (dashed)
        self.draw_segment(ax, vertex_x, vertex_y, foot_x, foot_y, 
                         color=color, linewidth=linewidth, style='--')
        
        # Mark foot with small square (perpendicular symbol)
        self.draw_right_angle(ax, foot_x, foot_y, vertex_x, vertex_y, 
                             base_p1_x if t > 0.5 else base_p2_x, 
                             base_p1_y if t > 0.5 else base_p2_y, size=symbol_size)
        
        # Label height
        mid_x, mid_y = (vertex_x + foot_x) / 2, (vertex_y + foot_y) / 2
        ax.text(mid_x + 0.2, mid_y, 'h', fontsize=10, color=color, 
                fontweight='bold', ha='center', va='center')
        
        return (foot_x, foot_y)
    
    def draw_median(self, ax, vertex_x, vertex_y, side_p1_x, side_p1_y, side_p2_x, side_p2_y,
                   color='orange', linewidth=1.5):
        """Draw median from vertex to midpoint of opposite side"""
        # Calculate midpoint of opposite side
        mid_x = (side_p1_x + side_p2_x) / 2
        mid_y = (side_p1_y + side_p2_y) / 2
        
        # Draw median line (dash-dot)
        ax.plot([vertex_x, mid_x], [vertex_y, mid_y], 
                color=color, linewidth=linewidth, linestyle='-.', alpha=0.8)
        
        # Mark midpoint
        self.draw_point(ax, mid_x, mid_y, '', color=color, size=3)
        
        # Add small perpendicular marks on both halves of the side to show equal parts
        # Vector along the side
        side_dx = side_p2_x - side_p1_x
        side_dy = side_p2_y - side_p1_y
        side_length = np.sqrt(side_dx**2 + side_dy**2)
        
        if side_length > 0:
            # Perpendicular vector
            perp_x = -side_dy / side_length * 0.1
            perp_y = side_dx / side_length * 0.1
            
            # Mark equal halves
            for point in [(side_p1_x + mid_x)/2, (side_p1_y + mid_y)/2]:
                ax.plot([point - perp_x, point + perp_x], 
                       [(side_p1_y + mid_y)/2 - perp_y, (side_p1_y + mid_y)/2 + perp_y], 
                       color=color, linewidth=2)
            
            for point in [(mid_x + side_p2_x)/2, (mid_y + side_p2_y)/2]:
                ax.plot([point - perp_x, point + perp_x], 
                       [(mid_y + side_p2_y)/2 - perp_y, (mid_y + side_p2_y)/2 + perp_y], 
                       color=color, linewidth=2)
        
        # Label median
        label_x, label_y = (vertex_x + mid_x) / 2, (vertex_y + mid_y) / 2
        ax.text(label_x + 0.2, label_y, 'm', fontsize=10, color=color, 
                fontweight='bold', ha='center', va='center')
        
        return (mid_x, mid_y)
    
    def draw_bisector(self, ax, vertex_x, vertex_y, p1_x, p1_y, p2_x, p2_y, 
                     length=2.0, color='purple', linewidth=1.5):
        """Draw angle bisector from vertex between two points"""
        import math
        
        # Vectors from vertex to the two points
        v1_x, v1_y = p1_x - vertex_x, p1_y - vertex_y
        v2_x, v2_y = p2_x - vertex_x, p2_y - vertex_y
        
        # Normalize vectors
        len1 = np.sqrt(v1_x**2 + v1_y**2)
        len2 = np.sqrt(v2_x**2 + v2_y**2)
        
        if len1 > 0 and len2 > 0:
            v1_x, v1_y = v1_x / len1, v1_y / len1
            v2_x, v2_y = v2_x / len2, v2_y / len2
            
            # Bisector direction (sum of unit vectors)
            bisector_x = v1_x + v2_x
            bisector_y = v1_y + v2_y
            bisector_length = np.sqrt(bisector_x**2 + bisector_y**2)
            
            if bisector_length > 0:
                bisector_x /= bisector_length
                bisector_y /= bisector_length
                
                # End point of bisector
                end_x = vertex_x + bisector_x * length
                end_y = vertex_y + bisector_y * length
                
                # Draw bisector line (dotted)
                ax.plot([vertex_x, end_x], [vertex_y, end_y], 
                        color=color, linewidth=linewidth, linestyle=':', alpha=0.8)
                
                # Draw small arcs to show equal angles
                arc_radius = 0.4
                angle1 = math.atan2(v1_y, v1_x)
                angle2 = math.atan2(v2_y, v2_x)
                
                # Draw two small arcs
                for radius in [arc_radius * 0.7, arc_radius]:
                    angles = np.linspace(min(angle1, angle2), max(angle1, angle2), 20)
                    arc_x = vertex_x + radius * np.cos(angles)
                    arc_y = vertex_y + radius * np.sin(angles)
                    ax.plot(arc_x, arc_y, color=color, linewidth=1, alpha=0.6)
                
                # Label bisector
                label_x = vertex_x + bisector_x * (length * 0.6)
                label_y = vertex_y + bisector_y * (length * 0.6)
                ax.text(label_x + 0.1, label_y, 'b', fontsize=10, color=color, 
                        fontweight='bold', ha='center', va='center')
    
    def draw_perpendicular_bisector(self, ax, p1_x, p1_y, p2_x, p2_y, 
                                   length=3.0, color='red', linewidth=1.5):
        """Draw perpendicular bisector of a segment (médiatrice)"""
        # Midpoint of segment
        mid_x = (p1_x + p2_x) / 2
        mid_y = (p1_y + p2_y) / 2
        
        # Perpendicular direction
        dx = p2_x - p1_x
        dy = p2_y - p1_y
        segment_length = np.sqrt(dx**2 + dy**2)
        
        if segment_length > 0:
            # Perpendicular unit vector
            perp_x = -dy / segment_length
            perp_y = dx / segment_length
            
            # End points of perpendicular bisector
            end1_x = mid_x + perp_x * length / 2
            end1_y = mid_y + perp_y * length / 2
            end2_x = mid_x - perp_x * length / 2
            end2_y = mid_y - perp_y * length / 2
            
            # Draw perpendicular bisector (dash-dot-dot)
            ax.plot([end1_x, end2_x], [end1_y, end2_y], 
                    color=color, linewidth=linewidth, linestyle=(0, (3, 1, 1, 1)), alpha=0.8)
            
            # Mark midpoint with special symbol
            self.draw_point(ax, mid_x, mid_y, '', color=color, size=4)
            
            # Draw small perpendicular symbol at midpoint
            symbol_size = 0.15
            self.draw_right_angle(ax, mid_x, mid_y, p1_x, p1_y, end1_x, end1_y, size=symbol_size)
            
            # Mark equal distances from midpoint to endpoints of original segment
            self.mark_equal(ax, mid_x, mid_y, p1_x, p1_y, mid_x, mid_y, p2_x, p2_y, marks=1)
            
            # Label perpendicular bisector
            label_x = mid_x + perp_x * (length * 0.3)
            label_y = mid_y + perp_y * (length * 0.3)
            ax.text(label_x, label_y, '⊥', fontsize=12, color=color, 
                    fontweight='bold', ha='center', va='center')
    
    def process_geometric_properties(self, ax, data: dict, coords: dict):
        """Process and draw geometric properties from schema data"""
        
        # Process parallels
        paralleles = data.get("paralleles", [])
        for parallel_pair in paralleles:
            if len(parallel_pair) >= 2:
                seg1, seg2 = parallel_pair[0], parallel_pair[1]
                if len(seg1) >= 2 and len(seg2) >= 2:
                    p1, p2 = seg1[0], seg1[1]
                    p3, p4 = seg2[0], seg2[1]
                    
                    if all(p in coords for p in [p1, p2, p3, p4]):
                        self.mark_parallel(ax, *coords[p1], *coords[p2], *coords[p3], *coords[p4])
        
        # Process perpendiculars
        perpendiculaires = data.get("perpendiculaires", [])
        for perp_pair in perpendiculaires:
            if len(perp_pair) >= 2:
                seg1, seg2 = perp_pair[0], perp_pair[1]
                if len(seg1) >= 2 and len(seg2) >= 2:
                    p1, p2 = seg1[0], seg1[1]
                    p3, p4 = seg2[0], seg2[1]
                    
                    if all(p in coords for p in [p1, p2, p3, p4]):
                        # Find intersection point (assuming they intersect)
                        # For now, mark perpendicular at midpoints
                        mid1_x, mid1_y = (coords[p1][0] + coords[p2][0]) / 2, (coords[p1][1] + coords[p2][1]) / 2
                        
                        # Draw perpendicular symbol at intersection
                        self.draw_right_angle(ax, mid1_x, mid1_y, coords[p1][0], coords[p1][1], 
                                            coords[p3][0], coords[p3][1], size=0.2)
        
        # Process equal segments
        egaux = data.get("egaux", [])
        for equal_group in egaux:
            if len(equal_group) >= 2:
                segments = equal_group
                marks = len(segments)  # Different number of marks for different groups
                
                for i in range(len(segments) - 1):
                    seg1, seg2 = segments[i], segments[i + 1]
                    if len(seg1) >= 2 and len(seg2) >= 2:
                        p1, p2 = seg1[0], seg1[1]
                        p3, p4 = seg2[0], seg2[1]
                        
                        if all(p in coords for p in [p1, p2, p3, p4]):
                            self.mark_equal(ax, *coords[p1], *coords[p2], *coords[p3], *coords[p4], marks=1)
        
        # Process heights
        hauteurs = data.get("hauteurs", [])
        for height_data in hauteurs:
            if len(height_data) >= 3:
                vertex, base_p1, base_p2 = height_data[0], height_data[1], height_data[2]
                
                if all(p in coords for p in [vertex, base_p1, base_p2]):
                    self.draw_height(ax, *coords[vertex], *coords[base_p1], *coords[base_p2])
        
        # Process medians
        medianes = data.get("medianes", [])
        for median_data in medianes:
            if len(median_data) >= 3:
                vertex, side_p1, side_p2 = median_data[0], median_data[1], median_data[2]
                
                if all(p in coords for p in [vertex, side_p1, side_p2]):
                    self.draw_median(ax, *coords[vertex], *coords[side_p1], *coords[side_p2])
        
        # Process angle bisectors
        bissectrices = data.get("bissectrices", [])
        for bisector_data in bissectrices:
            if len(bisector_data) >= 3:
                vertex, p1, p2 = bisector_data[0], bisector_data[1], bisector_data[2]
                
                if all(p in coords for p in [vertex, p1, p2]):
                    self.draw_bisector(ax, *coords[vertex], *coords[p1], *coords[p2])
        
        # Process perpendicular bisectors
        mediatrices = data.get("mediatrices", [])
        for mediator_data in mediatrices:
            if len(mediator_data) >= 2:
                p1, p2 = mediator_data[0], mediator_data[1]
                
                if all(p in coords for p in [p1, p2]):
                    self.draw_perpendicular_bisector(ax, *coords[p1], *coords[p2])
    
    # ========== QUADRILATERAL ALIASES ==========
    
    def _render_quadrilatere(self, data: dict) -> str:
        """Generic quadrilateral renderer - delegates to specific types"""
        quad_type = data.get("sous_type", "rectangle").lower()
        
        # Map quadrilateral aliases to specific renderers
        quad_mapping = {
            "rectangle": self._render_rectangle,
            "carre": self._render_carre,
            "losange": self._render_losange,
            "parallelogramme": self._render_parallelogramme,
            "trapeze": self._render_trapeze,
            "trapeze_rectangle": self._render_trapeze_rectangle,
            "trapeze_isocele": self._render_trapeze_isocele
        }
        
        renderer = quad_mapping.get(quad_type, self._render_rectangle)
        logger.info(f"Rendering quadrilateral type: {quad_type}")
        return renderer(data)
    
    def _render_losange(self, data: dict) -> str:
        """Render a diamond/rhombus"""
        fig, ax = plt.subplots(figsize=(4, 4))
        
        cote = data.get("cote", 4)
        angle = data.get("angle", 60)  # Angle in degrees
        
        import math
        angle_rad = math.radians(angle)
        
        # Calculate diamond vertices
        coords = {
            'A': (0, 0),                                    # Bottom
            'B': (cote * math.cos(angle_rad), cote * math.sin(angle_rad)),  # Left
            'C': (cote * (1 + math.cos(angle_rad)), cote * math.sin(angle_rad)),  # Top
            'D': (cote, 0)                                  # Right
        }
        
        # Draw diamond using utility functions
        diamond_coords = [coords['A'], coords['B'], coords['C'], coords['D']]
        self.draw_polygon(ax, diamond_coords, fill_color='lightpink', edge_color='purple')
        
        # Draw corner points
        for point, (x, y) in coords.items():
            self.draw_point(ax, x, y, point, label_offset=(0.2, 0.2), size=4)
        
        # Mark all sides as equal
        sides = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')]
        for i in range(len(sides)):
            p1, p2 = sides[i]
            next_p1, next_p2 = sides[(i + 1) % len(sides)]
            
            # Mark adjacent sides as equal
            x1, y1 = coords[p1]
            x2, y2 = coords[p2]
            x3, y3 = coords[next_p1]
            x4, y4 = coords[next_p2]
            
            self.mark_equal(ax, x1, y1, x2, y2, x3, y3, x4, y4, marks=1)
        
        # Add side length label
        self.draw_len_label(ax, coords['A'][0], coords['A'][1], 
                           coords['B'][0], coords['B'][1], cote)
        
        # Process additional geometric properties
        self.process_geometric_properties(ax, data, coords)
        
        # Clean axes and auto-center
        ax.set_aspect('equal')
        ax.axis('off')
        ax.relim()
        ax.autoscale_view()
        ax.set_title('Losange', fontsize=12, fontweight='bold', pad=10)
        
        return self._fig_to_svg(fig)
    
    def _render_parallelogramme(self, data: dict) -> str:
        """Render a parallelogram"""
        fig, ax = plt.subplots(figsize=(4, 4))
        
        base = data.get("base", 5)
        cote = data.get("cote", 3)
        angle = data.get("angle", 60)  # Angle in degrees
        
        import math
        angle_rad = math.radians(angle)
        
        # Calculate parallelogram vertices
        coords = {
            'A': (0, 0),                                    # Bottom-left
            'B': (base, 0),                                # Bottom-right
            'C': (base + cote * math.cos(angle_rad), cote * math.sin(angle_rad)),  # Top-right
            'D': (cote * math.cos(angle_rad), cote * math.sin(angle_rad))          # Top-left
        }
        
        # Draw parallelogram using utility functions
        para_coords = [coords['A'], coords['B'], coords['C'], coords['D']]
        self.draw_polygon(ax, para_coords, fill_color='lightsteelblue', edge_color='steelblue')
        
        # Draw corner points
        for point, (x, y) in coords.items():
            self.draw_point(ax, x, y, point, label_offset=(0.2, 0.2), size=4)
        
        # Mark opposite sides as parallel and equal
        # AB || DC and AD || BC
        ab_coords = coords['A'] + coords['B']
        dc_coords = coords['D'] + coords['C']
        ad_coords = coords['A'] + coords['D']
        bc_coords = coords['B'] + coords['C']
        
        self.mark_parallel(ax, *ab_coords, *dc_coords)
        self.mark_parallel(ax, *ad_coords, *bc_coords)
        self.mark_equal(ax, *ab_coords, *dc_coords, marks=1)
        self.mark_equal(ax, *ad_coords, *bc_coords, marks=2)
        
        # Add length labels
        self.draw_len_label(ax, coords['A'][0], coords['A'][1], 
                           coords['B'][0], coords['B'][1], base, offset=-0.4)
        self.draw_len_label(ax, coords['A'][0], coords['A'][1], 
                           coords['D'][0], coords['D'][1], cote)
        
        # Process additional geometric properties
        self.process_geometric_properties(ax, data, coords)
        
        # Clean axes and auto-center
        ax.set_aspect('equal')
        ax.axis('off')
        ax.relim()
        ax.autoscale_view()
        ax.set_title('Parallélogramme', fontsize=12, fontweight='bold', pad=10)
        
        return self._fig_to_svg(fig)
    
    def _render_trapeze(self, data: dict) -> str:
        """Render a trapezoid"""
        fig, ax = plt.subplots(figsize=(4, 4))
        
        base_grande = data.get("base_grande", 6)
        base_petite = data.get("base_petite", 4)
        hauteur = data.get("hauteur", 3)
        decalage = data.get("decalage", 1)  # Offset for slanted sides
        
        # Calculate trapezoid vertices
        coords = {
            'A': (0, 0),                                    # Bottom-left
            'B': (base_grande, 0),                         # Bottom-right
            'C': (decalage + base_petite, hauteur),        # Top-right
            'D': (decalage, hauteur)                       # Top-left
        }
        
        # Draw trapezoid using utility functions
        trap_coords = [coords['A'], coords['B'], coords['C'], coords['D']]
        self.draw_polygon(ax, trap_coords, fill_color='lightsalmon', edge_color='darkorange')
        
        # Draw corner points
        for point, (x, y) in coords.items():
            self.draw_point(ax, x, y, point, label_offset=(0.2, 0.2), size=4)
        
        # Mark parallel bases
        ab_coords = coords['A'] + coords['B']
        dc_coords = coords['D'] + coords['C']
        self.mark_parallel(ax, *ab_coords, *dc_coords)
        
        # Add length labels
        self.draw_len_label(ax, coords['A'][0], coords['A'][1], 
                           coords['B'][0], coords['B'][1], base_grande, offset=-0.4)
        self.draw_len_label(ax, coords['D'][0], coords['D'][1], 
                           coords['C'][0], coords['C'][1], base_petite, offset=0.4)
        
        # Add height label
        mid_x = (coords['A'][0] + coords['D'][0]) / 2
        self.draw_segment(ax, mid_x, 0, mid_x, hauteur, color='gray', linewidth=1, style=':')
        ax.text(mid_x - 0.3, hauteur/2, f'h = {hauteur}', fontsize=10, ha='center', va='center',
                rotation=90, bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))
        
        # Clean axes and auto-center
        ax.set_aspect('equal')
        ax.axis('off')
        ax.relim()
        ax.autoscale_view()
        ax.set_title('Trapèze', fontsize=12, fontweight='bold', pad=10)
        
        return self._fig_to_svg(fig)
    
    def _render_trapeze_rectangle(self, data: dict) -> str:
        """Render a right trapezoid"""
        fig, ax = plt.subplots(figsize=(4, 4))
        
        base_grande = data.get("base_grande", 6)
        base_petite = data.get("base_petite", 4)
        hauteur = data.get("hauteur", 3)
        
        # Right trapezoid - perpendicular sides
        coords = {
            'A': (0, 0),                     # Bottom-left
            'B': (base_grande, 0),          # Bottom-right
            'C': (base_petite, hauteur),    # Top-right
            'D': (0, hauteur)               # Top-left
        }
        
        # Draw trapezoid using utility functions
        trap_coords = [coords['A'], coords['B'], coords['C'], coords['D']]
        self.draw_polygon(ax, trap_coords, fill_color='lightcyan', edge_color='teal')
        
        # Draw corner points
        for point, (x, y) in coords.items():
            self.draw_point(ax, x, y, point, label_offset=(0.2, 0.2), size=4)
        
        # Mark parallel bases
        ab_coords = coords['A'] + coords['B']
        dc_coords = coords['D'] + coords['C']
        self.mark_parallel(ax, *ab_coords, *dc_coords)
        
        # Mark right angles at A and D
        self.draw_right_angle(ax, coords['A'][0], coords['A'][1], 
                             coords['B'][0], coords['B'][1], coords['D'][0], coords['D'][1], size=0.2)
        self.draw_right_angle(ax, coords['D'][0], coords['D'][1], 
                             coords['A'][0], coords['A'][1], coords['C'][0], coords['C'][1], size=0.2)
        
        # Add length labels
        self.draw_len_label(ax, coords['A'][0], coords['A'][1], 
                           coords['B'][0], coords['B'][1], base_grande, offset=-0.4)
        self.draw_len_label(ax, coords['D'][0], coords['D'][1], 
                           coords['C'][0], coords['C'][1], base_petite, offset=0.4)
        self.draw_len_label(ax, coords['A'][0], coords['A'][1], 
                           coords['D'][0], coords['D'][1], hauteur, offset=-0.4)
        
        # Clean axes and auto-center
        ax.set_aspect('equal')
        ax.axis('off')
        ax.relim()
        ax.autoscale_view()
        ax.set_title('Trapèze Rectangle', fontsize=12, fontweight='bold', pad=10)
        
        return self._fig_to_svg(fig)
    
    def _render_trapeze_isocele(self, data: dict) -> str:
        """Render an isosceles trapezoid"""
        fig, ax = plt.subplots(figsize=(4, 4))
        
        base_grande = data.get("base_grande", 6)
        base_petite = data.get("base_petite", 4)
        hauteur = data.get("hauteur", 3)
        
        # Isosceles trapezoid - symmetric
        decalage = (base_grande - base_petite) / 2
        coords = {
            'A': (0, 0),                              # Bottom-left
            'B': (base_grande, 0),                   # Bottom-right
            'C': (decalage + base_petite, hauteur),  # Top-right
            'D': (decalage, hauteur)                 # Top-left
        }
        
        # Draw trapezoid using utility functions
        trap_coords = [coords['A'], coords['B'], coords['C'], coords['D']]
        self.draw_polygon(ax, trap_coords, fill_color='lavender', edge_color='mediumpurple')
        
        # Draw corner points
        for point, (x, y) in coords.items():
            self.draw_point(ax, x, y, point, label_offset=(0.2, 0.2), size=4)
        
        # Mark parallel bases
        ab_coords = coords['A'] + coords['B']
        dc_coords = coords['D'] + coords['C']
        self.mark_parallel(ax, *ab_coords, *dc_coords)
        
        # Mark equal legs (AD = BC)
        ad_coords = coords['A'] + coords['D']
        bc_coords = coords['B'] + coords['C']
        self.mark_equal(ax, *ad_coords, *bc_coords, marks=1)
        
        # Add length labels
        self.draw_len_label(ax, coords['A'][0], coords['A'][1], 
                           coords['B'][0], coords['B'][1], base_grande, offset=-0.4)
        self.draw_len_label(ax, coords['D'][0], coords['D'][1], 
                           coords['C'][0], coords['C'][1], base_petite, offset=0.4)
        
        # Clean axes and auto-center
        ax.set_aspect('equal')
        ax.axis('off')
        ax.relim()
        ax.autoscale_view()
        ax.set_title('Trapèze Isocèle', fontsize=12, fontweight='bold', pad=10)
        
        return self._fig_to_svg(fig)
    
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
            elif schema_type == "quadrilatere":
                return self._render_quadrilatere(schema_data)
            elif schema_type == "losange":
                return self._render_losange(schema_data)
            elif schema_type == "parallelogramme":
                return self._render_parallelogramme(schema_data)
            elif schema_type in ["trapeze", "trapèze"]:
                return self._render_trapeze(schema_data)
            elif schema_type == "trapeze_rectangle":
                return self._render_trapeze_rectangle(schema_data)
            elif schema_type == "trapeze_isocele":
                return self._render_trapeze_isocele(schema_data)
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
                except (ValueError, AttributeError, IndexError) as e:
                    logger.warning(f"Failed to parse coordinate '{coord_str}' for point '{point}': {e}")
        
        # Validate that we have coordinates for all points
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
        
        # Process additional geometric properties
        self.process_geometric_properties(ax, data, coords)
        
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
                except (ValueError, AttributeError, IndexError) as e:
                    logger.warning(f"Failed to parse coordinate '{point}: {coord_str}': {e}")
        
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
        
        # Process additional geometric properties
        self.process_geometric_properties(ax, data, coords)
        
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
        
        # Process additional geometric properties
        self.process_geometric_properties(ax, data, coords)
        
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
        
        # Define square corners
        coords = {
            'A': (0, cote),     # Top-left
            'B': (0, 0),       # Bottom-left  
            'C': (cote, 0),    # Bottom-right
            'D': (cote, cote)  # Top-right
        }
        
        # Draw square using utility functions
        square = patches.Rectangle((0, 0), cote, cote,
                                 facecolor='lightyellow', edgecolor='black', linewidth=2)
        ax.add_patch(square)
        
        # Draw corner points
        for point, (x, y) in coords.items():
            self.draw_point(ax, x, y, point, label_offset=(0.2, 0.2), size=4)
        
        # Draw equal segments (all sides equal)
        segments = [
            ('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'A')
        ]
        
        # Mark equal sides with single tick marks
        for i in range(len(segments)):
            p1, p2 = segments[i]
            x1, y1 = coords[p1]
            x2, y2 = coords[p2]
            
            # Add length label only to bottom edge
            if p1 == 'B' and p2 == 'C':
                self.draw_len_label(ax, x1, y1, x2, y2, cote, offset=-0.4)
        
        # Mark opposite sides as equal
        # AB = CD and BC = AD
        ab_coords = coords['A'] + coords['B']
        cd_coords = coords['C'] + coords['D']
        bc_coords = coords['B'] + coords['C']
        ad_coords = coords['A'] + coords['D']
        
        self.mark_equal(ax, *ab_coords, *cd_coords, marks=1)
        self.mark_equal(ax, *bc_coords, *ad_coords, marks=1)
        
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
        
        # Process additional geometric properties
        self.process_geometric_properties(ax, data, coords)
        
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
        
        # Draw center point using utility function
        self.draw_point(ax, 0, 0, 'O', label_offset=(0.2, 0.2), color='black', size=6)
        
        # Draw radius line using utility function
        radius_end_x, radius_end_y = rayon, 0
        self.draw_segment(ax, 0, 0, radius_end_x, radius_end_y, color='black', linewidth=2, style='--')
        
        # Add radius label using utility function
        self.draw_len_label(ax, 0, 0, radius_end_x, radius_end_y, f'r = {rayon}', offset=0.3)
        
        # Optional: Add diameter line and label
        if data.get("show_diameter", False):
            self.draw_segment(ax, -rayon, 0, rayon, 0, color='gray', linewidth=1, style=':')
            self.draw_len_label(ax, -rayon, 0, rayon, 0, f'd = {2*rayon}', offset=-0.3)
        
        # Optional: Mark points on circle
        points = data.get("points", [])
        for i, point_data in enumerate(points):
            if isinstance(point_data, dict):
                angle = point_data.get("angle", i * 90)  # Default angles at 0°, 90°, 180°, 270°
                label = point_data.get("label", f"P{i+1}")
                
                import math
                x = rayon * math.cos(math.radians(angle))
                y = rayon * math.sin(math.radians(angle))
                
                self.draw_point(ax, x, y, label, label_offset=(0.3, 0.3), color='blue', size=4)
        
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
                except (ValueError, AttributeError, IndexError):
                    pass  # Keep default coordinates
        
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