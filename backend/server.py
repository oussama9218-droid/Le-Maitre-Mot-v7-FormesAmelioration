from fastapi import FastAPI, APIRouter, HTTPException, Response, Depends, BackgroundTasks, Request, Form, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest
import json
import re
import tempfile
import weasyprint
from jinja2 import Template
from latex_to_svg import latex_renderer
from geometry_renderer import geometry_renderer
from render_schema import schema_renderer
import requests
from logger import get_logger, log_execution_time, log_ai_generation, log_schema_processing, log_user_context, log_quota_check

ROOT_DIR = Path(__file__).parent
TEMPLATES_DIR = ROOT_DIR / 'templates'
load_dotenv(ROOT_DIR / '.env')

# Template loading function
def load_template(template_name: str) -> str:
    """Load HTML template from templates directory"""
    template_path = TEMPLATES_DIR / f"{template_name}.html"
    if not template_path.exists():
        raise FileNotFoundError(f"Template {template_name}.html not found in {TEMPLATES_DIR}")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()

# Icon mapping for exercises - Professional cascading logic
EXERCISE_ICON_MAPPING = {
    # Priority 1: By exercise type (most robust)
    "geometry": "triangle-ruler",
    "algebra": "calculator",
    "statistics": "bar-chart",
    "probability": "dice-6",
    "text": "file-text",
    
    # Priority 2: By chapter (fallback)
    "Théorème de Pythagore": "triangle-ruler",
    "Théorème de Thalès": "triangle-ruler", 
    "Trigonométrie": "triangle-ruler",
    "Géométrie": "triangle-ruler",
    "Géométrie dans l'espace": "cube",
    "Géométrie - Triangles et quadrilatères": "triangle-ruler",
    "Fractions": "calculator",
    "Équations": "calculator",
    "Fonctions": "function-square",
    "Statistiques": "bar-chart",
    "Probabilités": "dice-6",
    "Volumes": "cube",
    
    # Physics-Chemistry icons (future expansion)
    "Matière": "atom",
    "Énergie": "zap",
    "Forces": "magnet",
    
    # Priority 3: Default fallback
    "default": "book-open"
}

def enrich_exercise_with_icon(exercise_data: dict, chapitre: str) -> dict:
    """
    Professional cascading icon enrichment logic:
    1. Priority: Use type from AI if provided and valid
    2. Fallback: Use chapter-based mapping  
    3. Detection: Analyze content for type hints
    4. Default: Use generic icon
    """
    
    # Priority 1: Use type from AI if provided and valid
    ai_type = exercise_data.get("type", "").lower()
    if ai_type in EXERCISE_ICON_MAPPING:
        exercise_data["icone"] = EXERCISE_ICON_MAPPING[ai_type]
        exercise_data["type"] = ai_type  # Ensure type is set
        return exercise_data
    
    # Priority 2: Use chapter-based mapping
    if chapitre in EXERCISE_ICON_MAPPING:
        exercise_data["icone"] = EXERCISE_ICON_MAPPING[chapitre]
        # Infer type from chapter
        if any(geo_word in chapitre.lower() for geo_word in ["géométrie", "pythagore", "thalès", "trigonométrie", "triangle", "volume"]):
            exercise_data["type"] = "geometry"
        elif any(alg_word in chapitre.lower() for alg_word in ["équation", "fonction", "fraction", "algèbre", "calcul"]):
            exercise_data["type"] = "algebra"
        elif any(stat_word in chapitre.lower() for stat_word in ["statistique", "probabilité"]):
            exercise_data["type"] = "statistics"
        else:
            exercise_data["type"] = "text"
        return exercise_data
    
    # Priority 3: Content-based detection (for unknown chapters)
    enonce = exercise_data.get("enonce", "").lower()
    if any(geo_word in enonce for geo_word in ["triangle", "cercle", "carré", "rectangle", "géométrique", "angle", "côté", "volume", "aire"]):
        exercise_data["type"] = "geometry"
        exercise_data["icone"] = "triangle-ruler"
    elif any(alg_word in enonce for alg_word in ["équation", "fonction", "fraction", "calcul", "nombre", "résoudre", "simplifier"]):
        exercise_data["type"] = "algebra" 
        exercise_data["icone"] = "calculator"
    elif any(stat_word in enonce for stat_word in ["statistique", "moyenne", "graphique", "données", "probabilité", "hasard"]):
        exercise_data["type"] = "statistics"
        exercise_data["icone"] = "bar-chart"
    else:
        # Priority 4: Default fallback
        exercise_data["type"] = "text"
        exercise_data["icone"] = EXERCISE_ICON_MAPPING["default"]
    
    return exercise_data

# Removed duplicate sanitize_ai_response function - using the newer one below

# Professional content processing function
@log_execution_time("process_schema_to_base64")
def process_schema_to_base64(schema: Optional[dict]) -> Optional[str]:
    """
    Process a geometric schema dictionary to Base64 image for web display.
    Returns Base64 string or None if no schema or processing failed.
    """
    logger = get_logger()
    
    if not schema or not isinstance(schema, dict):
        logger.debug("No schema provided or invalid schema format")
        return None
    
    schema_type = schema.get("type", "unknown")
    logger.debug(
        "Starting schema to Base64 conversion",
        module_name="schema",
        func_name="process_schema_to_base64",
        schema_type=schema_type
    )
    
    try:
        # Convert schema to geometry_renderer format
        geometry_schema = {
            "type": "schema_geometrique",
            "figure": schema.get("type", "triangle"),
            "donnees": schema
        }
        
        # Render to Base64 for web display
        base64_image = geometry_renderer.render_geometry_to_base64(geometry_schema)
        
        if base64_image:
            logger.info(
                "Schema successfully rendered to Base64",
                module_name="schema",
                func_name="process_schema_to_base64",
                schema_type=schema_type,
                base64_length=len(base64_image),
                status="success"
            )
            log_schema_processing(schema_type, True)
            return base64_image
        else:
            logger.warning(
                "Schema rendering failed",
                module_name="schema",
                func_name="process_schema_to_base64",
                schema_type=schema_type,
                status="failed"
            )
            log_schema_processing(schema_type, False)
            return None
            
    except Exception as e:
        logger.error(f"❌ Error processing schema to Base64: {e}")
        return None

def process_exercise_content(content: str) -> str:
    """
    Processes the exercise content to render both LaTeX and geometric schemas.
    This centralizes all content processing logic for consistency.
    """
    if not content or not isinstance(content, str):
        return content if isinstance(content, str) else ""
    
    # 1. Process legacy geometric schemas (for backward compatibility)
    try:
        content = geometry_renderer.process_geometric_schemas_for_web(content)
    except Exception as e:
        logger.error(f"Error processing legacy geometric schemas: {e}")
    
    # 2. Process LaTeX formulas
    try:
        content = latex_renderer.convert_latex_to_svg(content)
    except Exception as e:
        logger.error(f"Error processing LaTeX: {e}")
    
    return content

def reconcile_enonce_schema(enonce: str, schema_data: dict) -> dict:
    """
    Réconcilie l'énoncé et le schéma : complète les labels depuis l'énoncé, 
    détecte les symboles de parallèles (//) et perpendiculaires (⊥)
    
    Args:
        enonce: Texte de l'énoncé de l'exercice
        schema_data: Données du schéma géométrique
    
    Returns:
        dict: Schéma enrichi avec les informations extraites de l'énoncé
    """
    if not enonce or not schema_data or not isinstance(schema_data, dict):
        return schema_data or {}
    
    enriched_schema = schema_data.copy()
    warnings = []
    
    # Extract points mentioned in the text
    points_pattern = r'\b([A-Z])\b'
    mentioned_points = set(re.findall(points_pattern, enonce))
    
    # Get existing points from schema
    existing_points = set(enriched_schema.get("points", []))
    
    # Find missing points that are mentioned in text but not in schema
    missing_in_schema = mentioned_points - existing_points
    if missing_in_schema:
        warnings.append(f"Points mentionnés dans l'énoncé mais absents du schéma: {sorted(missing_in_schema)}")
        # Add missing points to schema
        enriched_schema["points"] = list(existing_points | missing_in_schema)
        
        # Add automatic positions for missing points
        labels = enriched_schema.get("labels", {})
        positions = [(5, 0), (0, 5), (-5, 0), (0, -5), (3.5, 3.5), (-3.5, 3.5), (-3.5, -3.5), (3.5, -3.5)]
        position_index = 0
        
        for point in sorted(missing_in_schema):
            if point not in labels and position_index < len(positions):
                x, y = positions[position_index]
                auto_coords = f"({x},{y})"
                labels[point] = auto_coords
                position_index += 1
                
                logger.warning(f"Point {point} ajouté automatiquement à {auto_coords}")
        
        enriched_schema["labels"] = labels
    
    # Find points in schema but not mentioned in text
    missing_in_text = existing_points - mentioned_points
    if missing_in_text:
        warnings.append(f"Points dans le schéma mais non mentionnés dans l'énoncé: {sorted(missing_in_text)}")
    
    # Extract coordinate information from text
    # Pattern for coordinates like "A(0,3)", "B(-2, 4)", etc.
    coord_pattern = r'([A-Z])\s*\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)'
    text_coordinates = re.findall(coord_pattern, enonce)
    
    if text_coordinates:
        labels = enriched_schema.get("labels", {})
        for point, x, y in text_coordinates:
            coord_str = f"({x},{y})"
            if point in labels and labels[point] != coord_str:
                warnings.append(f"Coordonnées contradictoires pour {point}: énoncé={coord_str}, schéma={labels[point]}")
            else:
                labels[point] = coord_str
                logger.info(f"Coordonnées extraites de l'énoncé: {point}{coord_str}")
        
        enriched_schema["labels"] = labels
    
    # Detect parallel symbols (//) in text
    parallel_patterns = [
        r'([A-Z]{2})\s*//\s*([A-Z]{2})',  # AB // CD
        r'([A-Z])\s*([A-Z])\s*//\s*([A-Z])\s*([A-Z])',  # A B // C D  
        r'\(([A-Z])([A-Z])\)\s*//\s*\(([A-Z])([A-Z])\)',  # (AB) // (CD)
    ]
    
    detected_parallels = []
    for pattern in parallel_patterns:
        matches = re.findall(pattern, enonce)
        for match in matches:
            if len(match) == 2:  # Format: AB // CD
                seg1, seg2 = match[0], match[1]
                if len(seg1) == 2 and len(seg2) == 2:
                    detected_parallels.append([[list(seg1), list(seg2)]])
            elif len(match) == 4:  # Format: A B // C D
                seg1 = [match[0], match[1]]
                seg2 = [match[2], match[3]]
                detected_parallels.append([[seg1, seg2]])
    
    if detected_parallels:
        existing_parallels = enriched_schema.get("paralleles", [])
        for parallel_pair in detected_parallels:
            if parallel_pair not in existing_parallels:
                existing_parallels.extend(parallel_pair)
                logger.info(f"Parallèles détectées dans l'énoncé: {parallel_pair}")
        enriched_schema["paralleles"] = existing_parallels
    
    # Detect perpendicular symbols (⊥) in text
    perpendicular_patterns = [
        r'([A-Z]{2})\s*⊥\s*([A-Z]{2})',  # AB ⊥ CD
        r'([A-Z])\s*([A-Z])\s*⊥\s*([A-Z])\s*([A-Z])',  # A B ⊥ C D
        r'\(([A-Z])([A-Z])\)\s*⊥\s*\(([A-Z])([A-Z])\)',  # (AB) ⊥ (CD)
    ]
    
    detected_perpendiculars = []
    for pattern in perpendicular_patterns:
        matches = re.findall(pattern, enonce)
        for match in matches:
            if len(match) == 2:  # Format: AB ⊥ CD
                seg1, seg2 = match[0], match[1]
                if len(seg1) == 2 and len(seg2) == 2:
                    detected_perpendiculars.append([[list(seg1), list(seg2)]])
            elif len(match) == 4:  # Format: A B ⊥ C D
                seg1 = [match[0], match[1]]
                seg2 = [match[2], match[3]]
                detected_perpendiculars.append([[seg1, seg2]])
    
    if detected_perpendiculars:
        existing_perpendiculars = enriched_schema.get("perpendiculaires", [])
        for perp_pair in detected_perpendiculars:
            if perp_pair not in existing_perpendiculars:
                existing_perpendiculars.extend(perp_pair)
                logger.info(f"Perpendiculaires détectées dans l'énoncé: {perp_pair}")
        enriched_schema["perpendiculaires"] = existing_perpendiculars
    
    # Detect length information from text
    # Pattern for lengths like "AB = 5 cm", "longueur BC = 3", etc.
    length_patterns = [
        r'([A-Z]{2})\s*=\s*(\d+(?:\.\d+)?)\s*(?:cm|m)?',  # AB = 5 cm
        r'longueur\s+([A-Z]{2})\s*=\s*(\d+(?:\.\d+)?)',   # longueur AB = 5
        r'([A-Z])\s*([A-Z])\s*=\s*(\d+(?:\.\d+)?)\s*(?:cm|m)?',  # A B = 5 cm
    ]
    
    detected_lengths = {}
    for pattern in length_patterns:
        matches = re.findall(pattern, enonce)
        for match in matches:
            if len(match) == 2:  # Format: AB = 5
                segment, length = match[0], match[1]
                if len(segment) == 2:
                    detected_lengths[segment] = float(length)
            elif len(match) == 3:  # Format: A B = 5
                p1, p2, length = match[0], match[1], match[2]
                segment = p1 + p2
                detected_lengths[segment] = float(length)
    
    if detected_lengths:
        segments = enriched_schema.get("segments", [])
        for segment_name, length in detected_lengths.items():
            p1, p2 = list(segment_name)
            # Look for existing segment or add new one
            found = False
            for segment in segments:
                if len(segment) >= 3 and segment[0] == p1 and segment[1] == p2:
                    segment[2]["longueur"] = length
                    found = True
                    break
            
            if not found:
                segments.append([p1, p2, {"longueur": length}])
                logger.info(f"Longueur extraite de l'énoncé: {segment_name} = {length}")
        
        enriched_schema["segments"] = segments
    
    # Detect right angles in text
    right_angle_patterns = [
        r'angle\s+droit\s+en\s+([A-Z])',  # angle droit en B
        r'rectangle\s+en\s+([A-Z])',      # rectangle en B
        r'perpendiculaire\s+en\s+([A-Z])', # perpendiculaire en B
    ]
    
    detected_right_angles = []
    for pattern in right_angle_patterns:
        matches = re.findall(pattern, enonce)
        for vertex in matches:
            detected_right_angles.append([vertex, {"angle_droit": True}])
    
    if detected_right_angles:
        angles = enriched_schema.get("angles", [])
        for right_angle in detected_right_angles:
            if right_angle not in angles:
                angles.append(right_angle)
                logger.info(f"Angle droit détecté dans l'énoncé: {right_angle[0]}")
        enriched_schema["angles"] = angles
    
    # Log warnings
    if warnings:
        for warning in warnings:
            logger.warning(f"[reconcile_enonce_schema] {warning}")
    
    # Log summary of enrichment
    original_elements = len(schema_data.get("points", [])) + len(schema_data.get("segments", [])) + len(schema_data.get("angles", []))
    enriched_elements = len(enriched_schema.get("points", [])) + len(enriched_schema.get("segments", [])) + len(enriched_schema.get("angles", []))
    
    if enriched_elements > original_elements:
        logger.info(f"[reconcile_enonce_schema] Schéma enrichi par l'énoncé: {original_elements} → {enriched_elements} éléments")
    
    return enriched_schema

def auto_place_points(schema: dict, missing_points: list) -> dict:
    """
    Intelligently place missing points based on schema type
    
    Args:
        schema: Schema dictionary 
        missing_points: List of point names to place
    
    Returns:
        dict: Updated labels with auto-placed points
    """
    if not missing_points:
        return {}
    
    schema_type = schema.get("type", "").lower()
    labels = schema.get("labels", {})
    
    auto_positions = {}
    placed_count = 0
    
    # Rule 1: Triangle with 3 missing points
    if schema_type in ["triangle", "triangle_rectangle"] and len(missing_points) == 3:
        triangle_positions = {"A": (0, 0), "B": (8, 0), "C": (0, 6)}
        for point in sorted(missing_points):
            if placed_count < 3:
                position_keys = list(triangle_positions.keys())
                if placed_count < len(position_keys):
                    pos = triangle_positions[position_keys[placed_count]]
                    auto_positions[point] = f"({pos[0]},{pos[1]})"
                    placed_count += 1
    
    # Rule 2: Quadrilaterals with 4 missing points
    elif schema_type in ["rectangle", "carre", "losange", "parallelogramme", "trapeze", 
                        "trapeze_rectangle", "trapeze_isocele", "quadrilatere"] and len(missing_points) == 4:
        quad_positions = {"A": (0, 0), "B": (8, 0), "C": (8, 6), "D": (0, 6)}
        for point in sorted(missing_points):
            if placed_count < 4:
                position_keys = list(quad_positions.keys())
                if placed_count < len(position_keys):
                    pos = quad_positions[position_keys[placed_count]]
                    auto_positions[point] = f"({pos[0]},{pos[1]})"
                    placed_count += 1
    
    # Rule 3: Distribute remaining points on circle of radius 5
    if placed_count < len(missing_points):
        remaining_points = missing_points[placed_count:]
        circle_positions = [(5, 0), (0, 5), (-5, 0), (0, -5), (3.5, 3.5), (-3.5, 3.5), (-3.5, -3.5), (3.5, -3.5)]
        
        for i, point in enumerate(remaining_points):
            if i < len(circle_positions):
                x, y = circle_positions[i]
                auto_positions[point] = f"({x},{y})"
    
    return auto_positions

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create uploads directory and mount static files
uploads_dir = ROOT_DIR / "uploads"
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Initialize LLM Chat
emergent_key = os.environ.get('EMERGENT_LLM_KEY')

# Initialize Stripe
stripe_secret_key = os.environ.get('STRIPE_SECRET_KEY')

# Define pricing packages (server-side only for security)
PRICING_PACKAGES = {
    "monthly": {
        "name": "Abonnement Mensuel",
        "amount": 9.99,
        "currency": "eur",
        "duration": "monthly",
        "description": "Accès illimité pendant 1 mois"
    },
    "yearly": {
        "name": "Abonnement Annuel", 
        "amount": 99.00,
        "currency": "eur",
        "duration": "yearly",
        "description": "Accès illimité pendant 1 an - Économisez 16%"
    }
}

# Define template styles available for export
EXPORT_TEMPLATE_STYLES = {
    "classique": {
        "name": "Classique",
        "description": "Style traditionnel élégant avec typographie serif",
        "preview_image": "/api/template-previews/classique.png",
        "available_for": ["free", "pro"],
        "sujet_template": "sujet_classique",
        "corrige_template": "corrige_classique"
    },
    "moderne": {
        "name": "Moderne",
        "description": "Style contemporain avec couleurs vives et design épuré",
        "preview_image": "/api/template-previews/moderne.png",
        "available_for": ["pro"],
        "sujet_template": "sujet_moderne",
        "corrige_template": "corrige_moderne"
    },
    "eleve": {
        "name": "Élève",
        "description": "Style coloré et ludique avec couleurs pastel",
        "preview_image": "/api/template-previews/eleve.png",
        "available_for": ["pro"],
        "sujet_template": "sujet_eleve",
        "corrige_template": "corrige_eleve"
    },
    "corrige_detaille": {
        "name": "Corrigé détaillé",
        "description": "Template spécialisé pour corrections avec barème et critères",
        "preview_image": "/api/template-previews/corrige_detaille.png",
        "available_for": ["pro"],
        "sujet_template": "sujet_classique",  # Utilise classique pour les sujets
        "corrige_template": "corrige_detaille"
    },
    "minimal": {
        "name": "Minimal",
        "description": "Style ultra-épuré, focus sur le contenu",
        "preview_image": "/api/template-previews/minimal.png",
        "available_for": ["pro"],
        "sujet_template": "sujet_minimal",
        "corrige_template": "corrige_minimal"
    },
    "academique": {
        "name": "Académique",
        "description": "Style officiel scolaire avec espaces de réponse et barème",
        "preview_image": "/api/template-previews/academique.png",
        "available_for": ["pro"],
        "sujet_template": "sujet_academique",
        "corrige_template": "corrige_academique"
    }
}

# Define Models
class Exercise(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # "ouvert", "qcm", "mixte"
    enonce: str
    donnees: Optional[dict] = None
    difficulte: str  # "facile", "moyen", "difficile"
    solution: dict  # {"etapes": [...], "resultat": "..."}
    bareme: List[dict] = []  # [{"etape": "...", "points": 1.0}]
    version: str = "A"
    seed: Optional[int] = None
    # New fields for UI enhancement
    exercise_type: Optional[str] = "text"  # "geometry", "algebra", "statistics", "text"
    icone: Optional[str] = "book-open"  # Icon identifier for frontend
    # NEW: Separate schema field (clean design)
    schema: Optional[dict] = None  # Geometric schema data separate from text
    # CRITICAL: Base64 schema image for frontend display
    schema_img: Optional[str] = None  # Base64 PNG image for web display

class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None  # For Pro users
    guest_id: Optional[str] = None  # For guest users
    matiere: str
    niveau: str
    chapitre: str
    type_doc: str  # "exercices", "controle", "dm"
    difficulte: str
    nb_exercices: int
    exercises: List[Exercise] = []
    export_count: int = 0  # Track exports for quotas
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProUser(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    nom: Optional[str] = None
    etablissement: Optional[str] = None
    account_type: str = "pro"
    subscription_type: str  # "monthly" or "yearly"
    subscription_expires: datetime
    stripe_customer_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None

class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    payment_id: Optional[str] = None
    amount: float
    currency: str
    package_id: str
    email: Optional[str] = None
    user_id: Optional[str] = None
    payment_status: str = "pending"  # pending, paid, failed, expired
    session_status: str = "initiated"  # initiated, complete, expired
    metadata: Optional[Dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class LoginSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_email: EmailStr
    session_token: str
    device_id: str  # Unique identifier for device/browser
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class LoginRequest(BaseModel):
    email: EmailStr

class VerifyLoginRequest(BaseModel):
    token: str
    device_id: str

class UserTemplate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_email: EmailStr
    logo_filename: Optional[str] = None
    logo_url: Optional[str] = None
    professor_name: Optional[str] = None
    school_name: Optional[str] = None
    school_year: Optional[str] = None
    footer_text: Optional[str] = None
    template_style: str = "minimaliste"  # minimaliste, classique, moderne
    colors: Optional[Dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class GenerateRequest(BaseModel):
    matiere: str
    niveau: str
    chapitre: str
    type_doc: str
    difficulte: str = "moyen"
    nb_exercices: int = 6
    versions: List[str] = ["A"]
    guest_id: Optional[str] = None

class ExportRequest(BaseModel):
    document_id: str
    export_type: str  # "sujet" or "corrige"
    guest_id: Optional[str] = None
    template_style: Optional[str] = "classique"  # Style d'export choisi

class AdvancedPDFOptions(BaseModel):
    page_format: str = "A4"  # A4, A4_compact, US_Letter
    margin_preset: str = "standard"  # standard, compact, generous
    custom_margins: Optional[Dict[str, str]] = None  # Override margin_preset if provided
    show_difficulty: bool = True
    show_creation_date: bool = True
    show_exercise_numbers: bool = True
    show_point_values: bool = True
    include_instructions: bool = True
    page_numbering: str = "bottom_center"  # bottom_center, bottom_right, top_right, none
    exercise_separator: str = "line"  # line, space, box, none
    question_numbering: str = "arabic"  # arabic, roman, letters, none
    color_scheme: str = "professional"  # professional, academic, modern, minimal
    font_scaling: float = 1.0  # 0.8 to 1.2

class EnhancedExportRequest(BaseModel):
    document_id: str
    export_type: str  # "sujet" or "corrige"
    guest_id: Optional[str] = None
    advanced_options: Optional[AdvancedPDFOptions] = None

class CheckoutRequest(BaseModel):
    package_id: str  # "monthly" or "yearly"
    origin_url: str
    email: Optional[str] = None
    nom: Optional[str] = None
    etablissement: Optional[str] = None

class CatalogItem(BaseModel):
    name: str
    levels: Optional[List[str]] = None
    chapters: Optional[List[str]] = None

class AnalyticsRequest(BaseModel):
    date_from: Optional[str] = None  # ISO date string
    date_to: Optional[str] = None
    user_email: Optional[str] = None  # For Pro users to see their own stats

class TemplateSaveRequest(BaseModel):
    professor_name: Optional[str] = None
    school_name: Optional[str] = None
    school_year: Optional[str] = None
    footer_text: Optional[str] = None
    template_style: str = "minimaliste"

# French curriculum data
CURRICULUM_DATA = {
    "Mathématiques": {
        "6e": [
            "Nombres entiers et décimaux",
            "Fractions",
            "Géométrie - Figures planes",
            "Périmètres et aires",
            "Volumes",
            "Proportionnalité"
        ],
        "5e": [
            "Nombres relatifs",
            "Fractions et nombres décimaux",
            "Expressions littérales",
            "Équations",
            "Géométrie - Triangles",
            "Parallélogrammes",
            "Symétrie centrale",
            "Statistiques"
        ],
        "4e": [
            "Nombres relatifs",
            "Fractions et puissances",
            "Calcul littéral",
            "Équations et inéquations",
            "Théorème de Pythagore",
            "Théorème de Thalès",
            "Géométrie - Cosinus",
            "Statistiques et probabilités"
        ],
        "3e": [
            "Arithmétique",
            "Calcul littéral et équations",
            "Fonctions linéaires et affines",
            "Théorème de Thalès",
            "Trigonométrie",
            "Statistiques et probabilités",
            "Géométrie dans l'espace"
        ]
    },
    "Français": {
        "6e": [
            "Récits d'aventures",
            "Récits de création et création poétique",
            "Résister au plus fort : ruses, mensonges et masques",
            "Grammaire - La phrase",
            "Conjugaison - Présent, passé, futur",
            "Orthographe - Accords dans le groupe nominal",
            "Vocabulaire - Formation des mots"
        ],
        "5e": [
            "Le voyage et l'aventure : pourquoi aller vers l'inconnu ?",
            "Avec autrui : familles, amis, réseaux",
            "Héros/héroïnes et héroïsmes",
            "Grammaire - Classes et fonctions",
            "Conjugaison - Modes et temps",
            "Orthographe - Accords sujet-verbe",
            "Vocabulaire - Sens propre et figuré"
        ],
        "4e": [
            "Dire l'amour",
            "Individu et société : confrontations de valeurs ?",
            "Fiction pour interroger le réel",
            "Grammaire - La phrase complexe",
            "Conjugaison - Temps du récit",
            "Orthographe - Participe passé",
            "Vocabulaire - Registres de langue"
        ],
        "3e": [
            "Se raconter, se représenter",
            "Dénoncer les travers de la société",
            "Visions poétiques du monde",
            "Agir sur le monde",
            "Grammaire - Subordonnées",
            "Expression écrite - Argumentation",
            "Vocabulaire - Champs lexicaux"
        ]
    },
    "Physique-Chimie": {
        "6e": [
            "Matière, mouvement, énergie, information",
            "Le vivant, sa diversité et les fonctions qui le caractérisent",
            "Matériaux et objets techniques",
            "La planète Terre, les êtres vivants dans leur environnement"
        ],
        "5e": [
            "Organisation et transformations de la matière",
            "Mouvement et interactions",
            "L'énergie et ses conversions",
            "Des signaux pour observer et communiquer"
        ],
        "4e": [
            "Organisation et transformations de la matière",
            "Mouvement et interactions",
            "L'énergie et ses conversions",
            "Des signaux pour observer et communiquer"
        ],
        "3e": [
            "Organisation et transformations de la matière",
            "Mouvement et interactions",
            "L'énergie et ses conversions",
            "Des signaux pour observer et communiquer"
        ]
    }
}

# PDF Templates - Unified WeasyPrint approach
TEMPLATE_STYLES = {
    "minimaliste": {
        "name": "Minimaliste",
        "description": "Design épuré et moderne",
        "header_font": "Helvetica",
        "header_font_size": 14,
        "content_font": "Helvetica",
        "content_font_size": 11,
        "primary_color": "#2c3e50",
        "secondary_color": "#7f8c8d",
        "accent_color": "#3498db",
        "separator_style": "line",
        "logo_max_height": 40
    },
    "classique": {
        "name": "Classique",
        "description": "Style académique traditionnel",
        "header_font": "Times-Roman",
        "header_font_size": 16,
        "content_font": "Times-Roman", 
        "content_font_size": 12,
        "primary_color": "#1a1a1a",
        "secondary_color": "#4a4a4a",
        "accent_color": "#8b4513",
        "separator_style": "double_line",
        "logo_max_height": 45
    },
    "moderne": {
        "name": "Moderne",
        "description": "Design contemporain et aéré",
        "header_font": "Helvetica-Light",
        "header_font_size": 15,
        "content_font": "Helvetica",
        "content_font_size": 11,
        "primary_color": "#34495e",
        "secondary_color": "#95a5a6",
        "accent_color": "#e74c3c",
        "separator_style": "gradient",
        "logo_max_height": 50
    }
}

# Advanced PDF Layout Options
PDF_LAYOUT_OPTIONS = {
    "page_formats": {
        "A4": {"width": "21cm", "height": "29.7cm"},
        "A4_compact": {"width": "21cm", "height": "29.7cm", "margin": "1.5cm"},
        "US_Letter": {"width": "8.5in", "height": "11in"}
    },
    "margin_presets": {
        "standard": {"top": "2.5cm", "bottom": "2.5cm", "left": "2cm", "right": "2cm"},
        "compact": {"top": "1.5cm", "bottom": "1.5cm", "left": "1.5cm", "right": "1.5cm"},
        "generous": {"top": "3cm", "bottom": "3cm", "left": "2.5cm", "right": "2.5cm"}
    },
    "content_options": {
        "show_difficulty": True,
        "show_creation_date": True,
        "show_exercise_numbers": True,
        "show_point_values": True,
        "include_instructions": True,
        "page_numbering": "bottom_center"  # Options: bottom_center, bottom_right, top_right, none
    },
    "visual_enhancements": {
        "exercise_separator": "line",  # Options: line, space, box, none
        "question_numbering": "arabic",  # Options: arabic, roman, letters, none
        "color_scheme": "professional",  # Options: professional, academic, modern, minimal
        "font_scaling": 1.0  # Multiplier for font sizes (0.8 to 1.2)
    }
}

# Templates are now loaded from external files
#ouss

'''"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {
            size: A4;
            margin: 2cm;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 12pt;
            line-height: 1.6;
            color: #2c3e50;
            background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
            margin: 0;
            padding: 0;
        }
        
        .page-container {
            background: white;
            padding: 30px;
            margin: 20px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            min-height: calc(100vh - 40px);
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 25px;
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(17, 153, 142, 0.3);
        }
        
        .title {
            font-size: 24pt;
            font-weight: bold;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .subtitle {
            font-size: 16pt;
            margin-bottom: 8px;
            opacity: 0.9;
        }
        
        .document-info {
            font-size: 12pt;
            margin-top: 15px;
            padding: 10px;
            background: rgba(255,255,255,0.2);
            border-radius: 8px;
        }
        
        .decoration {
            text-align: center;
            font-size: 20pt;
            color: #27ae60;
            margin: 20px 0;
        }
        
        .solution {
            margin: 25px 0;
            page-break-inside: avoid;
            border-left: 4px solid #27ae60;
            background: #f8f9fa;
            border-radius: 0 10px 10px 0;
            padding: 20px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        }
        
        .solution-header {
            background: linear-gradient(90deg, #27ae60, #229954);
            color: white;
            padding: 12px 20px;
            margin: -20px -20px 20px -20px;
            border-radius: 10px 10px 0 0;
            font-size: 16pt;
            font-weight: bold;
        }
        
        .solution-steps {
            background: #e8f5e8;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
            border-left: 4px solid #27ae60;
        }
        
        .solution-steps h4 {
            color: #27ae60;
            margin: 0 0 10px 0;
            font-size: 14pt;
        }
        
        .solution-steps ol {
            margin: 0;
            padding-left: 20px;
        }
        
        .solution-steps li {
            margin: 8px 0;
            font-size: 13pt;
            line-height: 1.5;
        }
        
        .final-result {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
            font-weight: bold;
            text-align: center;
            font-size: 14pt;
            box-shadow: 0 5px 15px rgba(240, 147, 251, 0.3);
        }
        
        .final-result::before {
            content: "🎯 ";
            font-size: 16pt;
        }
        
        .method-tip {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 8px;
            padding: 12px;
            margin: 15px 0;
            font-style: italic;
            color: #856404;
        }
        
        .method-tip::before {
            content: "💡 Astuce : ";
            font-weight: bold;
            color: #f39c12;
        }
        
        .footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            border-top: 2px solid #ecf0f1;
            color: #7f8c8d;
            font-size: 11pt;
        }
        
        .success-badge {
            display: inline-block;
            background: #27ae60;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12pt;
            margin: 10px 5px;
        }
    </style>
</head>
<body>
    <div class="page-container">
        <div class="header">
            <div class="title">{{ document.type_doc.title() }} - Corrigé ✅</div>
            <div class="subtitle">{{ document.matiere }} - {{ document.niveau }}</div>
            <div class="subtitle">📚 {{ document.chapitre }}</div>
            <div class="document-info">
                🎯 Difficulté: {{ document.difficulte.title() }} | 
                📝 {{ document.nb_exercices }} exercices | 
                📅 {{ date_creation }}
            </div>
        </div>
        
        <div class="decoration">🌟 Solutions détaillées 🌟</div>
        
        <div class="content">
            {% for exercice in document.exercises %}
                <div class="solution">
                    <div class="solution-header">
                        ✅ Exercice {{ loop.index }} - Corrigé
                    </div>
                    
                    {% if exercice.solution.etapes %}
                        <div class="solution-steps">
                            <h4>📋 Méthode étape par étape :</h4>
                            <ol>
                                {% for etape in exercice.solution.etapes %}
                                    <li>{{ etape }}</li>
                                {% endfor %}
                            </ol>
                        </div>
                        
                        <div class="method-tip">
                            Prends ton temps pour comprendre chaque étape avant de passer à la suivante !
                        </div>
                    {% endif %}
                    
                    {% if exercice.solution.resultat %}
                        <div class="final-result">
                            Résultat final : {{ exercice.solution.resultat }}
                        </div>
                    {% endif %}
                </div>
            {% endfor %}
        </div>
        
        <div class="success-badge">✨ Bravo !</div>
        <div class="success-badge">🎓 Bien joué !</div>
        <div class="success-badge">💪 Continue !</div>
        
        <div class="footer">
            🌟 Le Maître Mot - Générateur de documents pédagogiques 🌟<br>
            <small>Utilise ces corrections pour progresser !</small>
        </div>
    </div>
</body>
</html>
"""
'''
#ouss

# Pro Templates - Ultra Professional Design

@log_execution_time("check_guest_quota")
async def check_guest_quota(guest_id: str):
    """Check if guest user can export (3 exports max)"""
    logger = get_logger()
    logger.debug(
        "Starting guest quota check",
        module_name="quota",
        func_name="check_guest_quota",
        user_type="guest",
        guest_id=guest_id[:8] + "..." if guest_id and len(guest_id) > 8 else guest_id
    )
    
    try:
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        export_count = await db.exports.count_documents({
            "guest_id": guest_id,
            "created_at": {"$gte": thirty_days_ago}
        })
        
        remaining = max(0, 3 - export_count)
        
        # Log quota check result
        log_quota_check("guest", export_count, 3, guest_id=guest_id[:8] + "..." if guest_id and len(guest_id) > 8 else guest_id)
        
        logger.info(
            "Guest quota check completed",
            module_name="quota",
            func_name="check_guest_quota",
            user_type="guest",
            exports_used=export_count,
            exports_remaining=remaining,
            quota_exceeded=remaining == 0
        )
        
        return {
            "exports_used": export_count,
            "exports_remaining": remaining,
            "max_exports": 3,
            "quota_exceeded": remaining == 0
        }
        
    except Exception as e:
        logger.error(f"Error checking guest quota: {e}")
        return {
            "exports_used": 0,
            "exports_remaining": 3,
            "max_exports": 3,
            "quota_exceeded": False
        }

async def check_user_pro_status(email: str):
    """Check if user has active Pro subscription"""
    try:
        user = await db.pro_users.find_one({"email": email})
        if user and user.get("subscription_expires"):
            expires = user["subscription_expires"]
            if isinstance(expires, str):
                expires = datetime.fromisoformat(expires).replace(tzinfo=timezone.utc)
            elif isinstance(expires, datetime) and expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            logger.info(f"Checking Pro status for {email}: expires={expires}, now={now}")
            
            if expires > now:
                logger.info(f"User {email} is Pro (expires: {expires})")
                return True, user
            else:
                logger.info(f"User {email} Pro subscription expired")
        
        return False, None
        
    except Exception as e:
        logger.error(f"Error checking pro status: {e}")
        return False, None

async def require_pro_user(request: Request):
    """Middleware to require Pro user authentication"""
    session_token = request.headers.get("X-Session-Token")
    
    if not session_token:
        raise HTTPException(
            status_code=401, 
            detail="Authentification requise pour les fonctionnalités Pro"
        )
    
    email = await validate_session_token(session_token)
    if not email:
        raise HTTPException(
            status_code=401, 
            detail="Session invalide ou expirée"
        )
    
    is_pro, user = await check_user_pro_status(email)
    if not is_pro:
        raise HTTPException(
            status_code=403, 
            detail="Abonnement Pro requis pour cette fonctionnalité"
        )
    
    return email

# ReportLab-dependent functions commented out due to import removal
# These functions were using ReportLab for PDF generation with personalized templates

# class PersonalizedDocTemplate(BaseDocTemplate):
#     """Custom document template with personalized headers and footers"""
#     [COMMENTED OUT - ReportLab dependency removed]

# def create_personalized_styles(template_config):
#     """Create ReportLab styles based on template configuration"""
#     [COMMENTED OUT - ReportLab dependency removed]

# async def create_personalized_pdf(document, template_config, export_type="sujet"):
#     """Create PDF with personalized template using ReportLab Flowables"""
#     [COMMENTED OUT - ReportLab dependency removed]
#     return None

async def send_magic_link_email(email: str, token: str):
    """Send magic link email via Brevo"""
    try:
        brevo_api_key = os.environ.get('BREVO_API_KEY')
        sender_email = os.environ.get('BREVO_SENDER_EMAIL')
        sender_name = os.environ.get('BREVO_SENDER_NAME', 'Le Maître Mot')
        
        if not brevo_api_key or not sender_email:
            logger.error("Brevo credentials not configured")
            return False
        
        # Generate magic link URL
        frontend_url = os.environ.get('FRONTEND_URL', 'https://lemaitremot.preview.emergentagent.com')
        magic_link = f"{frontend_url}/login/verify?token={token}"
        
        # Email content
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%); padding: 2rem; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 1.5rem;">Le Maître Mot</h1>
                <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0;">Connexion à votre compte Pro</p>
            </div>
            
            <div style="background: white; padding: 2rem; border-radius: 0 0 8px 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <h2 style="color: #1f2937; margin-top: 0;">Connexion demandée</h2>
                <p style="color: #4b5563; line-height: 1.6;">
                    Vous avez demandé à vous connecter à votre compte Le Maître Mot Pro. 
                    Cliquez sur le bouton ci-dessous pour vous connecter automatiquement.
                </p>
                
                <div style="text-align: center; margin: 2rem 0;">
                    <a href="{magic_link}" 
                       style="background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%); 
                              color: white;
                              text-decoration: none;
                              padding: 1rem 2rem;
                              border-radius: 8px;
                              font-weight: bold;
                              display: inline-block;">
                        🔐 Se connecter à Le Maître Mot Pro
                    </a>
                </div>
                
                <div style="background: #f3f4f6; padding: 1rem; border-radius: 6px; margin: 1.5rem 0;">
                    <p style="margin: 0; font-size: 0.875rem; color: #6b7280;">
                        <strong>⚠️ Important :</strong> Ce lien est valide pendant 15 minutes et ne peut être utilisé qu'une seule fois.
                        Pour des raisons de sécurité, toute autre session active sera automatiquement fermée.
                    </p>
                </div>
                
                <p style="color: #6b7280; font-size: 0.875rem; line-height: 1.4;">
                    Si vous n'avez pas demandé cette connexion, ignorez cet email. 
                    Votre compte reste sécurisé.
                </p>
                
                <div style="border-top: 1px solid #e5e7eb; margin-top: 2rem; padding-top: 1rem;">
                    <p style="color: #9ca3af; font-size: 0.75rem; margin: 0; text-align: center;">
                        Le Maître Mot - Générateur de documents pédagogiques
                    </p>
                </div>
            </div>
        </div>
        """
        
        # Send email using requests (simple approach)
        import requests
        
        headers = {
            'api-key': brevo_api_key,
            'Content-Type': 'application/json'
        }
        
        data = {
            'sender': {
                'name': sender_name,
                'email': sender_email
            },
            'to': [
                {
                    'email': email,
                    'name': email.split('@')[0]
                }
            ],
            'subject': '🔐 Connexion à Le Maître Mot Pro',
            'htmlContent': html_content
        }
        
        response = requests.post(
            'https://api.brevo.com/v3/smtp/email',
            headers=headers,
            json=data,
            timeout=10
        )
        
        if response.status_code == 201:
            logger.info(f"Magic link email sent successfully to {email}")
            return True
        else:
            logger.error(f"Failed to send magic link email: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending magic link email: {e}")
        return False

async def create_login_session(email: str, device_id: str):
    """Create a new login session and invalidate old ones"""
    try:
        # Generate secure session token
        session_token = str(uuid.uuid4()) + "-" + str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        
        # Create new session data
        session = LoginSession(
            user_email=email,
            session_token=session_token,
            device_id=device_id,
            expires_at=expires_at
        )
        
        session_dict = session.dict()
        session_dict['expires_at'] = session_dict['expires_at'].isoformat()
        session_dict['created_at'] = session_dict['created_at'].isoformat()
        session_dict['last_used'] = session_dict['last_used'].isoformat()
        
        # Remove all existing sessions for this user (single device policy)
        delete_result = await db.login_sessions.delete_many({"user_email": email})
        logger.info(f"Deleted {delete_result.deleted_count} existing sessions for {email}")
        
        # Insert the new session
        await db.login_sessions.insert_one(session_dict)
        logger.info(f"Created new session for {email} on device {device_id}")
        
        # Update user's last_login
        await db.pro_users.update_one(
            {"email": email},
            {"$set": {"last_login": datetime.now(timezone.utc)}}
        )
        
        logger.info(f"Login session created successfully for {email} - all previous sessions invalidated")
        return session_token
        
    except Exception as e:
        logger.error(f"Error creating login session: {e}")
        return None

async def validate_session_token(session_token: str):
    """Validate a session token and return user email if valid"""
    try:
        session = await db.login_sessions.find_one({"session_token": session_token})
        
        if not session:
            return None
            
        # Check expiration
        expires_at = session.get('expires_at')
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at).replace(tzinfo=timezone.utc)
        elif isinstance(expires_at, datetime) and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        
        if expires_at < now:
            # Session expired, clean it up
            await db.login_sessions.delete_one({"session_token": session_token})
            return None
            
        # Update last_used
        await db.login_sessions.update_one(
            {"session_token": session_token},
            {"$set": {"last_used": datetime.now(timezone.utc)}}
        )
        
        return session.get('user_email')
        
    except Exception as e:
        logger.error(f"Error validating session token: {e}")
        return None

def sanitize_ai_response(response: str) -> str:
    """
    Clean and validate AI JSON responses to handle common formatting issues.
    Ensures consistent JSON structure for schema processing.
    """
    try:
        # Remove any leading/trailing whitespace and non-JSON text
        response = response.strip()
        
        # Find JSON boundaries
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            logger.warning("No JSON found in AI response")
            return '{"schema": null}'
        
        json_content = response[json_start:json_end]
        
        # PHASE 3 FIX: Clean common JSON formatting issues
        # Fix single quotes to double quotes
        json_content = re.sub(r"'([^']*)':", r'"\1":', json_content)  # Fix keys
        json_content = re.sub(r":\s*'([^']*)'", r': "\1"', json_content)  # Fix values
        
        # Fix missing commas (basic pattern)
        json_content = re.sub(r'}\s*{', '}, {', json_content)
        json_content = re.sub(r']\s*"', '], "', json_content)
        
        # Validate JSON syntax
        try:
            parsed = json.loads(json_content)
            
            # Ensure standard "schema" key (handle various formats)
            if "schéma" in parsed:
                parsed["schema"] = parsed.pop("schéma")
            elif "schema_geometrique" in parsed:
                parsed["schema"] = parsed.pop("schema_geometrique")
            
            # PHASE 3 FIX: Validate schema completeness
            if "schema" in parsed and parsed["schema"] is not None:
                schema = parsed["schema"]
                if isinstance(schema, dict):
                    points = schema.get("points", [])
                    labels = schema.get("labels", {})
                    
                    # Check if all points have coordinates
                    missing_coords = [p for p in points if p not in labels]
                    if missing_coords:
                        logger.warning(
                            "Schema has points without coordinates",
                            module_name="sanitize",
                            func_name="sanitize_ai_response",
                            missing_coords=missing_coords,
                            available_coords=list(labels.keys())
                        )
                        # Try to add default coordinates for missing points
                        for i, point in enumerate(missing_coords):
                            labels[point] = f"({i*2},{i*2})"  # Simple fallback
                        schema["labels"] = labels
                        logger.info(f"Added fallback coordinates for points: {missing_coords}")
            
            # Return cleaned JSON
            return json.dumps(parsed)
            
        except json.JSONDecodeError as e:
            logger.error(
                "Invalid JSON syntax in AI response after cleaning",
                module_name="sanitize",
                func_name="sanitize_ai_response",
                error=str(e),
                json_preview=json_content[:200]
            )
            return '{"schema": null}'
            
    except Exception as e:
        logger.error(f"Error sanitizing AI response: {e}")
        return '{"schema": null}'

@log_execution_time("generate_geometry_schema_with_ai")
async def generate_geometry_schema_with_ai(enonce: str) -> str:
    """
    Makes a second AI call to generate a geometry schema based on the exercise text.
    Returns the JSON string of the schema.
    """
    logger = get_logger()
    logger.debug(
        "Starting geometry schema generation",
        module_name="schema",
        func_name="generate_geometry_schema_with_ai",
        enonce_length=len(enonce),
        enonce_preview=enonce[:100]
    )
    
    try:
        # Create LLM chat instance with faster model
        chat = LlmChat(
            api_key=emergent_key,
            session_id=f"schema_gen_{uuid.uuid4()}",
            system_message="""En tant que moteur de génération de schémas, ton unique tâche est de créer un schéma géométrique JSON à partir de l'énoncé d'exercice.

**Instructions :**
1. Analyse l'énoncé pour identifier les points, segments et longueurs mentionnés.
2. Crée une structure JSON valide pour le schéma, comme dans l'exemple ci-dessous.
3. Ne renvoie QUE le code JSON, sans texte ni explication supplémentaire.
4. Si l'énoncé ne contient pas de géométrie, renvoie un objet JSON vide `{}`.

**Exemple de JSON pour un triangle** :
{
    "type": "triangle",
    "points": ["A", "B", "C"],
    "labels": {"A": "(0,8)", "B": "(0,0)", "C": "(6,0)"},
    "segments": [["A","B", {"longueur": 8}], ["B","C", {"longueur": 6}]],
    "angles": [["B", {"angle_droit": true}]]
}

**RÈGLE CRITIQUE** : Si tu listes N points, tu DOIS fournir N coordonnées dans labels.
Exemple INCORRECT: points: ["A","B","C","D"] avec labels: {"A":"(0,3)", "B":"(0,0)", "C":"(4,0)"}
Exemple CORRECT: points: ["A","B","C","D"] avec labels: {"A":"(0,3)", "B":"(0,0)", "C":"(4,0)", "D":"(4,3)"}

**Types de figures supportés** : triangle, triangle_rectangle, carre, rectangle, cercle, pyramide
**IMPORTANT** : 
- TOUJOURS fournir des coordonnées pour TOUS les points listés
- Si points: ["A", "B", "C", "D"], alors labels DOIT contenir A, B, C ET D
- Ne PAS générer trapeze ou autres types non supportés (sauf ceux listés ci-dessus)"""
        ).with_model("openai", "gpt-4o")
        
        # Create focused prompt for schema generation with STRICT format requirements  
        prompt = f"""
**ÉNONCÉ DE L'EXERCICE :**
"{enonce}"

Tu dois analyser cet énoncé et générer un schéma géométrique dans le format JSON EXACT suivant :

```json
{{
    "schema": {{
        "type": "triangle",
        "points": ["A", "B", "C"],
        "segments": [["A", "B", {{"longueur": 5}}], ["B", "C", {{"longueur": 3}}]],
        "angles": [["B", {{"angle_droit": true}}]]
    }}
}}
```

**RÈGLES IMPÉRATIVES :**
1. TOUJOURS utiliser la clé "schema" (sans accent, sans underscore)
2. TOUJOURS fermer toutes les accolades et crochets
3. TOUJOURS utiliser des virgules correctes
4. Types valides : "triangle", "rectangle", "carre", "cercle", "pyramide"
5. Si pas de géométrie, retourner : {{"schema": null}}

Réponds UNIQUEMENT avec ce JSON, rien d'autre.
"""

        user_message = UserMessage(text=prompt)
        
        # Set shorter timeout for faster response
        import asyncio
        response = await asyncio.wait_for(
            chat.send_message(user_message), 
            timeout=15.0  # 15 seconds max for schema generation
        )
        
        # Sanitize and validate the AI response
        sanitized_response = sanitize_ai_response(response)
        
        # Verify we have a valid schema
        try:
            parsed = json.loads(sanitized_response)
            if parsed.get("schema") is not None:
                schema_type = parsed['schema'].get('type', 'unknown')
                logger.info(
                    "Valid schema generated successfully",
                    module_name="schema",
                    func_name="generate_geometry_schema_with_ai",
                    schema_type=schema_type,
                    status="success"
                )
                log_ai_generation("second_pass_success", True, schema_type=schema_type)
            else:
                logger.debug("No schema needed for this exercise")
                
            return sanitized_response
        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to parse sanitized schema response",
                module_name="schema",
                func_name="generate_geometry_schema_with_ai",
                error=str(e),
                status="parse_error"
            )
            return '{"schema": null}'
        
    except Exception as e:
        logger.error(f"Error in AI geometry generation: {e}")
        return "{}"  # Return empty JSON object on error

@log_execution_time("generate_exercises_with_ai")
async def generate_exercises_with_ai(matiere: str, niveau: str, chapitre: str, type_doc: str, difficulte: str, nb_exercices: int) -> List[Exercise]:
    """Generate exercises using AI"""
    logger = get_logger()
    
    # Log input parameters
    logger.info(
        "Starting AI exercise generation",
        module_name="generation",
        func_name="generate_exercises_with_ai",
        matiere=matiere,
        niveau=niveau,
        chapitre=chapitre,
        type_doc=type_doc,
        difficulte=difficulte,
        nb_exercices=nb_exercices
    )
    
    # Level-specific guidance
    niveau_guidance = {
        "6e": "Niveau débutant - vocabulaire simple, calculs basiques, exemples concrets du quotidien",
        "5e": "Niveau intermédiaire - introduction de concepts plus abstraits mais restant accessibles", 
        "4e": "Niveau confirmé - calculs plus complexes, raisonnement mathématique développé",
        "3e": "Niveau avancé - préparation au lycée, concepts abstraits, démonstrations"
    }
    
    # Chapter-specific examples by subject
    chapter_examples = {
        # Mathématiques
        "Volumes": {
            "6e": "Utiliser des objets du quotidien (boîtes, bouteilles), unités simples (cm³, L), calculs avec nombres entiers ou décimaux simples",
            "5e": "Prismes et cylindres, conversions d'unités, calculs avec fractions simples",
            "4e": "Pyramides et cônes, volumes composés, problèmes de proportionnalité",
            "3e": "Solides de révolution, problèmes d'optimisation, calculs complexes"
        },
        "Nombres relatifs": {
            "5e": "Introduction intuitive avec température, altitude, calculs simples",
            "4e": "Opérations complètes, règles des signes, problèmes contextualisés",
            "3e": "Applications complexes, équations, inéquations"
        },
        
        # Français
        "Récits d'aventures": {
            "6e": "Lecture d'extraits d'aventures, compréhension du schéma narratif, vocabulaire de l'action et du suspense"
        },
        "Grammaire - La phrase": {
            "6e": "Types et formes de phrases, ponctuation, reconnaissance sujet/verbe/complément"
        },
        "Le voyage et l'aventure : pourquoi aller vers l'inconnu ?": {
            "5e": "Analyse de textes narratifs, étude des motifs du départ, expression écrite créative"
        },
        "Dire l'amour": {
            "4e": "Poésie lyrique, registres de langue, figures de style, expression des sentiments"
        },
        "Se raconter, se représenter": {
            "3e": "Autobiographie, mémoires, analyse de l'écriture de soi, réflexion sur l'identité"
        },
        
        # Physique-Chimie
        "Matière, mouvement, énergie, information": {
            "6e": "États de la matière, observations simples, classification des objets"
        },
        "Organisation et transformations de la matière": {
            "5e": "Mélanges et corps purs, changements d'état, transformations chimiques simples",
            "4e": "Atomes et molécules, réactions chimiques, conservation de la masse",
            "3e": "Ions, pH, électrolyse, synthèse chimique"
        },
        "Mouvement et interactions": {
            "5e": "Description du mouvement, vitesse, interactions mécaniques",
            "4e": "Référentiel, relativité du mouvement, forces et effets",
            "3e": "Gravitation, poids et masse, interactions fondamentales"
        }
    }
    
    # Get specific guidance
    level_guide = niveau_guidance.get(niveau, "Adapter au niveau demandé")
    chapter_guide = chapter_examples.get(chapitre, {}).get(niveau, "Respecter le programme officiel")
    
    # Subject-specific instructions
    subject_instructions = {
        "Mathématiques": f"""
En tant qu'enseignant de mathématiques et expert en conception d'exercices, crée {nb_exercices} exercices pour un élève de {niveau} en {matiere}, sur le chapitre suivant: "{chapitre}". 
Chaque exercice doit avoir une difficulté {difficulte}.

**Instructions cruciales** :
1. Utilise des **valeurs numériques différentes et variées** pour chaque exercice (pas de répétition des mêmes données).
2.  Tous les exercices de géométrie doivent inclure systématiquement un schéma.
3. L’EXERCICE 2 DOIT OBLIGATOIREMENT avoir un schéma, quel que soit le type d’exercice.
4. Le schéma doit toujours être placé dans `"donnees.schema"` et jamais dans `"enonce"`.
5. L’énoncé doit contenir uniquement du texte lisible pour l’élève.
6. Le schéma doit suivre une structure claire (type, points, labels, segments, angles, etc.).

**Format JSON attendu pour chaque exercice** :
{{
  "titre": "Titre concis",
  "enonce": "Texte clair de l'exercice (sans JSON).",
  "type": "geometry",
  "difficulte": "{difficulte}",
  "donnees": {{
    "schema": {{
      "type": "triangle",
      "points": ["A", "B", "C"],
      "labels": {{"A": "(0,8)", "B": "(0,0)", "C": "(6,0)"}},
      "segments": [["A","B", {{"longueur": 8}}], ["B","C", {{"longueur": 6}}]],
      "angles": [["B", {{"angle_droit": true}}]]
    }}
  }},
  "solution": {{
    "etapes": ["..."],
    "resultat": "..."
  }},
  "bareme": [
    {{"etape": "Méthode", "points": 2.0}},
    {{"etape": "Résultat", "points": 2.0}}
  ]
}}

Réponds uniquement avec un tableau JSON contenant tous les exercices, sans texte ni explication supplémentaire.
"""
,

        "Français": f"""Tu es un générateur d'exercices de français pour {niveau} - {chapitre}.

Génère {nb_exercices} exercices RAPIDES ET EFFICACES.

RÈGLES FRANÇAIS:
1. Niveau {niveau} - Chapitre "{chapitre}"
2. {level_guide}
3. Exercices variés : analyse, grammaire, expression écrite
4. Textes supports courts et adaptés
5. Questions progressives et structurées""",

        "Physique-Chimie": f"""Tu es un générateur d'exercices de physique-chimie français pour {niveau} - {chapitre}.

Génère {nb_exercices} exercices RAPIDES ET EFFICACES.

RÈGLES PHYSIQUE-CHIMIE:
1. Niveau {niveau} - Chapitre "{chapitre}"
2. {level_guide}
3. Situations concrètes et expérimentales
4. Calculs simples adaptés au niveau
5. Schémas et observations privilégiés"""
    }
    
    system_msg = subject_instructions.get(matiere, subject_instructions["Mathématiques"])
    
    # Create LLM chat instance with faster model
    chat = LlmChat(
        api_key=emergent_key,
        session_id=f"exercise_gen_{uuid.uuid4()}",
        system_message=f"""{system_msg}

JSON OBLIGATOIRE:
{{
  "exercises": [
    {{
      "type": "ouvert",
      "enonce": "Énoncé concis et clair",
      "difficulte": "{difficulte}",
      "solution": {{
        "etapes": ["Étape 1", "Étape 2"],
        "resultat": "Résultat final"
      }},
      "bareme": [
        {{"etape": "Méthode", "points": 2.0}},
        {{"etape": "Résultat", "points": 2.0}}
      ]
    }}
  ]
}}"""
    ).with_model("openai", "gpt-4o")
    
    # Create concise prompt for faster generation
    examples = {
        # Mathématiques
        "Volumes": "Calculer volume pavé 4×3×2 cm",
        "Nombres relatifs": "Calculer -5 + 3 - (-2)",
        "Fractions": "Calculer 2/3 + 1/4",
        "Géométrie - Figures planes": "Calculer périmètre rectangle 5×3 cm",
        
        # Français
        "Récits d'aventures": "Analyser un extrait de roman d'aventures",
        "Grammaire - La phrase": "Identifier sujet et verbe dans une phrase",
        "Conjugaison - Présent, passé, futur": "Conjuguer 'aller' au présent",
        "Le voyage et l'aventure : pourquoi aller vers l'inconnu ?": "Analyser les motivations d'un personnage",
        "Dire l'amour": "Étudier une strophe de poème lyrique",
        "Se raconter, se représenter": "Analyser un passage autobiographique",
        
        # Physique-Chimie
        "Matière, mouvement, énergie, information": "Classer des objets selon leur état",
        "Organisation et transformations de la matière": "Identifier une transformation chimique",
        "Mouvement et interactions": "Décrire le mouvement d'un objet",
        "L'énergie et ses conversions": "Identifier des formes d'énergie"
    }
    
    example = examples.get(chapitre, f"Exercice {chapitre}")
    
    prompt = f"""
Génère {nb_exercices} exercices de {matiere} niveau {niveau} sur le chapitre: {chapitre}
Difficulté: {difficulte}

IMPORTANT: Réponds UNIQUEMENT en JSON valide, sans aucun texte avant ou après.

JSON requis:
{{
    "exercises": [
        {{
            "enonce": "Énoncé complet de l'exercice avec données numériques. Exemple: {example}",
            "type": "geometry",
            "icone": "triangle-ruler",
            "solution": {{
                "etapes": ["Étape 1 détaillée", "Étape 2 détaillée"],
                "resultat": "Résultat final avec unité"
            }},
            "difficulte": "{difficulte}",
            "bareme": [
                {{"etape": "Méthode", "points": 2.0}},
                {{"etape": "Résultat", "points": 2.0}}
            ]
        }}
    ]
}}

Types et icônes:
- geometry/triangle-ruler: géométrie, figures
- algebra/calculator: calculs, équations  
- statistics/bar-chart: statistiques, données
"""
    
    try:
        user_message = UserMessage(text=prompt)
        
        # FIRST PASS: Generate the exercise content
        logger.debug("Starting first AI pass - exercise content generation")
        log_ai_generation("first_pass_start", True)
        
        import asyncio
        response = await asyncio.wait_for(
            chat.send_message(user_message), 
            timeout=20.0  # 20 seconds max
        )
        
        logger.debug(f"First AI pass completed, response length: {len(response)} chars")
        
        # Parse the JSON response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON found in response")
            
        json_content = response[json_start:json_end]
        data = json.loads(json_content)
        
        # Convert to Exercise objects with professional content processing
        exercises = []
        for i, ex_data in enumerate(data.get("exercises", [])):
            # Enrich with icon before processing
            ex_data = enrich_exercise_with_icon(ex_data, chapitre)
            
            # Get the raw enonce
            enonce = ex_data.get("enonce", "").strip()
            
            # SECOND PASS: Generate geometric schema if this is a geometry exercise
            if matiere.lower() == "mathématiques":
                # Check if the exercise might need a geometric schema
                geometry_keywords = ["triangle", "cercle", "carré", "rectangle", "parallélogramme", 
                                   "géométrie", "figure", "pythagore", "thalès", "trigonométrie", 
                                   "angle", "périmètre", "aire", "longueur", "côté", "hypoténuse"]
                
                if any(keyword in enonce.lower() for keyword in geometry_keywords):
                    logger.info(
                        "Geometry keywords detected, starting schema generation",
                        module_name="generation",
                        func_name="schema_detection",
                        enonce_preview=enonce[:100],
                        detected_keywords=[kw for kw in geometry_keywords if kw in enonce.lower()]
                    )
                    
                    # Generate schema with second AI call
                    log_ai_generation("second_pass_start", True)
                    schema_json_str = await generate_geometry_schema_with_ai(enonce)
                    
                    # Add schema to separate field (CLEAN DESIGN - no more JSON in text!)
                    if len(schema_json_str.strip()) > 10:  # More robust check for content
                        try:
                            # Validate the generated schema with STANDARDIZED format
                            schema_data = json.loads(schema_json_str)
                            schema_content = schema_data.get("schema")  # STANDARD KEY: "schema"
                            
                            if schema_content is not None and isinstance(schema_content, dict) and "type" in schema_content:
                                # Reconcile schema with enonce text for better accuracy
                                enriched_schema = reconcile_enonce_schema(enonce, schema_content)
                                
                                # Store enriched schema in separate field - KEEP ENONCE PURE TEXT!
                                ex_data["schema"] = enriched_schema
                                ex_data["type"] = "geometry"
                                
                                log_schema_processing(
                                    schema_type=schema_content.get('type', 'unknown'),
                                    success=True,
                                    exercise_id=str(i+1)
                                )
                                logger.info(
                                    "Schema successfully stored in separate field",
                                    module_name="generation",
                                    func_name="schema_storage",
                                    schema_type=schema_content.get('type'),
                                    exercise_id=i+1
                                )
                            else:
                                logger.debug("No geometric schema needed for this exercise")
                                log_ai_generation("second_pass_skip", True)
                                
                        except json.JSONDecodeError as e:
                            logger.warning(f"⚠️ Invalid JSON schema generated: {e}, keeping text-only exercise")
            
            # CRITICAL FIX: Clean the enonce by removing any residual JSON schema blocks
            enonce_clean = re.sub(r'\{\s*"sch[ée]ma".*?\}', "", enonce, flags=re.DOTALL)
            enonce_clean = re.sub(r'\{\s*"schema".*?\}', "", enonce_clean, flags=re.DOTALL)
            enonce_clean = enonce_clean.strip()
            
            # Remove any trailing newlines or multiple spaces caused by JSON removal
            enonce_clean = re.sub(r'\n\s*\n+', '\n\n', enonce_clean)  # Clean up multiple newlines
            enonce_clean = re.sub(r'\s+$', '', enonce_clean)  # Remove trailing whitespace
            
            if enonce_clean != enonce:
                logger.info(
                    "Cleaned JSON artifacts from enonce",
                    module_name="generation",
                    func_name="enonce_cleaning",
                    original_length=len(enonce),
                    cleaned_length=len(enonce_clean),
                    exercise_id=i+1
                )
            
            # Process the CLEANED enonce with centralized content processing
            processed_enonce = process_exercise_content(enonce_clean)
            
            # Process solution steps and result
            solution = ex_data.get("solution", {"etapes": ["Étape 1", "Étape 2"], "resultat": "Résultat"})
            
            # Process each solution step
            if "etapes" in solution and isinstance(solution["etapes"], list):
                solution["etapes"] = [
                    process_exercise_content(step) for step in solution["etapes"]
                ]
            
            # Process solution result
            if "resultat" in solution:
                solution["resultat"] = process_exercise_content(solution["resultat"])
            
            # CRITICAL FIX: Preserve schema data and generate Base64 image
            schema_data = ex_data.get("schema", None)
            donnees_to_store = None
            schema_img_base64 = None
            
            if schema_data is not None:
                # Store schema in donnees for PDF processing
                donnees_to_store = {"schema": schema_data}
                logger.info(f"✅ Schema data preserved in donnees field: {schema_data.get('type', 'unknown')}")
                
                # CRITICAL: Generate Base64 image for frontend immediately
                schema_img_base64 = process_schema_to_base64(schema_data)
                if schema_img_base64:
                    schema_img_base64 = f"data:image/png;base64,{schema_img_base64}"
                    logger.info(
                        "Schema Base64 generated during exercise creation",
                        module_name="generation",
                        func_name="create_exercise",
                        exercise_id=i+1,
                        schema_type=schema_data.get('type'),
                        base64_length=len(schema_img_base64)
                    )
            
            exercise = Exercise(
                type=ex_data.get("type", "ouvert"),
                enonce=processed_enonce,
                donnees=donnees_to_store,  # ✅ PRESERVE SCHEMA DATA
                difficulte=ex_data.get("difficulte", difficulte),
                solution=solution,
                bareme=ex_data.get("bareme", [{"etape": "Méthode", "points": 2.0}, {"etape": "Résultat", "points": 2.0}]),
                seed=hash(processed_enonce) % 1000000,
                # Add icon and exercise type information
                exercise_type=ex_data.get("type", "text"),
                icone=ex_data.get("icone", EXERCISE_ICON_MAPPING["default"]),
                # NEW: Clean schema field (separate from text)
                schema=ex_data.get("schema", None),
                # CRITICAL: Base64 schema image for frontend
                schema_img=schema_img_base64
            )
            exercises.append(exercise)
        
        if not exercises:
            raise ValueError("No exercises generated")
            
        logger.info(
            "Successfully completed AI exercise generation",
            module_name="generation",
            func_name="generate_exercises_with_ai",
            total_exercises=len(exercises),
            geometry_exercises=sum(1 for ex in exercises if hasattr(ex, 'exercise_type') and ex.exercise_type == 'geometry'),
            approach="two_pass"
        )
        return exercises
        
    except asyncio.TimeoutError:
        logger.error("AI generation timeout - using fallback")
        return await generate_fallback_exercises(matiere, niveau, chapitre, difficulte, nb_exercices)
    except Exception as e:
        logger.error(f"Error generating exercises: {e}")
        return await generate_fallback_exercises(matiere, niveau, chapitre, difficulte, nb_exercices)

async def generate_fallback_exercises(matiere: str, niveau: str, chapitre: str, difficulte: str, nb_exercices: int) -> List[Exercise]:
    """Generate quick fallback exercises"""
    exercises = []
    
    # Quick templates based on chapter and subject
    templates = {
        # Mathématiques
        "Nombres relatifs": [
            "Calculer : {a} + {b} - ({c})",
            "Déterminer le signe de : {a} × {b}",
            "Résoudre : x + {a} = {b}"
        ],
        "Géométrie - Triangles et quadrilatères": [
            "Dans un triangle ABC, calculer l'aire sachant que AB = {a} cm, AC = {b} cm et l'angle A = 60°.",
            "Un parallélogramme ABCD a une base de {a} cm et une hauteur de {b} cm. Calculer son aire.",
            "Calculer le périmètre d'un rectangle de longueur {a} cm et largeur {b} cm."
        ],
        "Géométrie dans l'espace": [
            "Calculer le volume d'un cube d'arête {a} cm.",
            "Un parallélépipède rectangle a pour dimensions {a} cm × {b} cm × {c} cm. Calculer son volume.",
            "Calculer l'aire totale d'un cube d'arête {a} cm.",
            "Un cylindre a un rayon de {a} cm et une hauteur de {b} cm. Calculer son volume."
        ],
        "Volumes": [
            "Calculer le volume d'un pavé de dimensions {a} cm × {b} cm × {c} cm",
            "Une boîte cubique a une arête de {a} cm. Quel est son volume ?",
            "Convertir {a} L en cm³"
        ],
        "Théorème de Pythagore": [
            "Dans un triangle rectangle ABC rectangle en B, AB = {a} cm et BC = {b} cm. Calculer AC.",
            "Un triangle rectangle a des côtés de {a} cm et {b} cm. Calculer l'hypoténuse.",
            "Utiliser le théorème de Pythagore pour calculer le côté manquant : a = {a} cm, c = {b} cm."
        ],
        "Théorème de Thalès": [
            "Dans un triangle ABC, on trace une droite parallèle à BC. Si AB = {a} cm et la portion coupée = {b} cm, calculer les proportions.",
            "Deux droites parallèles coupent deux sécantes. Si les segments sont {a} cm et {b} cm d'un côté, et {c} cm de l'autre, calculer le quatrième segment.",
            "Utiliser le théorème de Thalès pour calculer une longueur manquante dans une configuration de triangles semblables."
        ],
        "Théorème de Thalès": [
            "Dans un triangle ABC, on trace une droite parallèle à BC. Si AB = {a} cm et la portion coupée = {b} cm, calculer les proportions.",
            "Deux droites parallèles coupent deux sécantes. Si les segments sont {a} cm et {b} cm d'un côté, et {c} cm de l'autre, calculer le quatrième segment.",
            "Utiliser le théorème de Thalès pour calculer une longueur manquante dans une configuration de triangles semblables."
        ],
        "Trigonométrie": [
            "Dans un triangle rectangle ABC rectangle en C, AB = {a} cm et AC = {b} cm. Calculer sin(A), cos(A) et tan(A).",
            "Un triangle rectangle a un angle de {a}° et une hypoténuse de {b} cm. Calculer les côtés adjacents et opposés.",
            "Utiliser les relations trigonométriques pour calculer la hauteur d'un bâtiment sachant que l'angle d'élévation est {a}° à {b} m de distance."
        ],
        "Fractions": [
            "Calculer : 1/{a} + 1/{b}",
            "Simplifier : {a}/{b}",
            "Comparer : 1/{a} et 1/{b}"
        ],
        
        # Français
        "Récits d'aventures": [
            "Identifier les étapes du schéma narratif dans un extrait",
            "Relever le vocabulaire de l'action dans le texte",
            "Expliquer les motivations du héros"
        ],
        "Grammaire - La phrase": [
            "Identifier le sujet et le verbe dans la phrase",
            "Transformer la phrase en phrase interrogative",
            "Corriger les erreurs de ponctuation"
        ],
        "Conjugaison - Présent, passé, futur": [
            "Conjuguer le verbe au temps demandé",
            "Identifier le temps des verbes soulignés",
            "Transformer la phrase au temps indiqué"
        ],
        
        # Physique-Chimie
        "Matière, mouvement, énergie, information": [
            "Classer ces objets selon leur état physique",
            "Identifier les propriétés de la matière observées",
            "Décrire les changements observés"
        ],
        "Organisation et transformations de la matière": [
            "Identifier s'il s'agit d'un mélange ou d'un corps pur",
            "Décrire la transformation observée",
            "Expliquer le changement d'état"
        ],
        "Mouvement et interactions": [
            "Décrire le mouvement de l'objet",
            "Identifier les forces qui s'exercent",
            "Calculer la vitesse moyenne"
        ]
    }
    
    template_list = templates.get(chapitre, [f"Exercice sur {chapitre}"])
    
    for i in range(nb_exercices):
        # Use modulo to cycle through templates
        template = template_list[i % len(template_list)]
        
        # Simple random values
        import random
        a, b, c = random.randint(2, 9), random.randint(2, 9), random.randint(2, 9)
        
        enonce = template.format(a=a, b=b, c=c)
        
        # CRITICAL: Apply content processing to fallback exercises too
        processed_enonce = process_exercise_content(enonce)
        
        # Create fallback exercise data and enrich with icon
        fallback_data = {
            "enonce": processed_enonce,
            "type": "text",
            "icone": "book-open"
        }
        fallback_data = enrich_exercise_with_icon(fallback_data, chapitre)
        
        exercise = Exercise(
            type="ouvert",
            enonce=fallback_data["enonce"],
            donnees=None,
            difficulte=difficulte,
            solution={
                "etapes": [
                    process_exercise_content("Appliquer la méthode du cours"), 
                    process_exercise_content("Effectuer les calculs")
                ],
                "resultat": process_exercise_content("Résultat à calculer")
            },
            bareme=[
                {"etape": "Méthode", "points": 2.0},
                {"etape": "Calcul", "points": 2.0}
            ],
            seed=random.randint(1000, 9999),
            exercise_type=fallback_data.get("type", "text"),
            icone=fallback_data.get("icone", "book-open")
        )
        exercises.append(exercise)
    
    return exercises

def format_exercises_for_export(exercises: List[dict], options: AdvancedPDFOptions) -> str:
    """Format exercises with advanced options"""
    formatted_content = []
    
    for i, exercise in enumerate(exercises, 1):
        exercise_parts = []
        
        # Exercise number with custom formatting
        if options.show_exercise_numbers:
            if options.question_numbering == "roman":
                number = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"][i-1] if i <= 10 else str(i)
            elif options.question_numbering == "letters":
                number = chr(64 + i) if i <= 26 else str(i)  # A, B, C...
            else:  # arabic or none
                number = str(i) if options.question_numbering == "arabic" else ""
            
            if number:
                exercise_parts.append(f"Exercice {number}")
        
        # Exercise content
        exercise_parts.append(exercise.get("enonce", ""))
        
        # Point values
        if options.show_point_values and exercise.get("bareme"):
            total_points = sum(item.get("points", 0) for item in exercise.get("bareme", []))
            if total_points > 0:
                exercise_parts.append(f"({total_points} points)")
        
        formatted_exercise = "\n".join(exercise_parts)
        
        # Exercise separator
        if options.exercise_separator == "line" and i < len(exercises):
            formatted_exercise += "\n" + "-" * 50 + "\n"
        elif options.exercise_separator == "space" and i < len(exercises):
            formatted_exercise += "\n\n"
        elif options.exercise_separator == "box":
            newline = '\n'
            lines = formatted_exercise.split(newline)
            box_width = len(lines[0]) + 4
            top_border = '┌' + '─' * box_width + '┐'
            bottom_border = '└' + '─' * box_width + '┘'
            content_lines = newline.join([f'│  {line}  │' for line in lines])
            formatted_exercise = f"{top_border}{newline}{content_lines}{newline}{bottom_border}"
        
        formatted_content.append(formatted_exercise)
    
    return "\n\n".join(formatted_content)

def format_solutions_for_export(exercises: List[dict], options: AdvancedPDFOptions) -> str:
    """Format solutions with advanced options"""
    formatted_content = []
    
    for i, exercise in enumerate(exercises, 1):
        solution_parts = []
        
        # Exercise number
        if options.show_exercise_numbers:
            if options.question_numbering == "roman":
                number = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"][i-1] if i <= 10 else str(i)
            elif options.question_numbering == "letters":
                number = chr(64 + i) if i <= 26 else str(i)
            else:
                number = str(i) if options.question_numbering == "arabic" else ""
            
            if number:
                solution_parts.append(f"Solution {number}")
        
        # Solution content
        solution = exercise.get("solution", {})
        if solution.get("etapes"):
            solution_parts.extend(solution["etapes"])
        if solution.get("resultat"):
            solution_parts.append(f"Résultat: {solution['resultat']}")
        
        formatted_solution = "\n".join(solution_parts)
        formatted_content.append(formatted_solution)
    
    return "\n\n".join(formatted_content)

def get_template_colors_and_fonts(template_config: dict) -> dict:
    """Get template colors and fonts based on style"""
    style_name = template_config.get('template_style', 'minimaliste')
    template_style = TEMPLATE_STYLES.get(style_name, TEMPLATE_STYLES['minimaliste'])
    
    return {
        'template_colors': {
            'primary': template_style['primary_color'],
            'secondary': template_style['secondary_color'],
            'accent': template_style['accent_color']
        },
        'template_fonts': {
            'header': template_style['header_font'],
            'content': template_style['content_font']
        }
    }

async def generate_advanced_pdf(document: dict, content: str, export_type: str, template_config: dict, options: AdvancedPDFOptions) -> bytes:
    """Generate PDF with advanced layout options"""
    # Get layout settings
    page_format = PDF_LAYOUT_OPTIONS["page_formats"].get(options.page_format, PDF_LAYOUT_OPTIONS["page_formats"]["A4"])
    margins = options.custom_margins or PDF_LAYOUT_OPTIONS["margin_presets"].get(options.margin_preset, PDF_LAYOUT_OPTIONS["margin_presets"]["standard"])
    
    # Build CSS with advanced options
    advanced_css = f"""
        @page {{
            size: {page_format.get('width', '21cm')} {page_format.get('height', '29.7cm')};
            margin-top: {margins['top']};
            margin-bottom: {margins['bottom']};
            margin-left: {margins['left']};
            margin-right: {margins['right']};
        }}
        
        body {{
            font-size: {11 * options.font_scaling}pt;
            line-height: {1.4 * options.font_scaling};
        }}
        
        .header {{
            font-size: {18 * options.font_scaling}pt;
        }}
        
        .exercise-number {{
            font-weight: bold;
            color: #2c3e50;
            margin-top: 20px;
        }}
    """
    
    # Use Pro template if available
    if template_config:
        template_style = TEMPLATE_STYLES.get(template_config.get('template_style', 'minimaliste'), TEMPLATE_STYLES['minimaliste'])
        template_colors = get_template_colors_and_fonts(template_config)
        
        if export_type == "sujet":
            template_content = load_template("sujet_pro")
        else:
            template_content = load_template("corrige_pro")
        
        html_content = Template(template_content).render(
            document={
                **document,
                'exercices': content,
                'type_doc': export_type.title()
            },
            date_creation=datetime.now().strftime("%d/%m/%Y"),
            **template_config,
            **template_colors,
            advanced_css=advanced_css
        )
    else:
        # Fallback to standard template with advanced options
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                {advanced_css}
                /* Standard styling with advanced options */
                .content {{ white-space: pre-line; }}
                .document-info {{ font-size: {10 * options.font_scaling}pt; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{export_type.title()}</h1>
                <h2>{document['matiere']} - {document['niveau']}</h2>
                <p>{document['chapitre']}</p>
                {f'<p>Difficulté: {document["difficulte"]}</p>' if options.show_difficulty else ''}
                {f'<p>Créé le {datetime.now().strftime("%d/%m/%Y")}</p>' if options.show_creation_date else ''}
            </div>
            <div class="content">{content}</div>
        </body>
        </html>
        """
    
    # Generate PDF
    pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
    return pdf_bytes

# API Routes
@api_router.get("/")
async def root():
    return {"message": "API Le Maître Mot V1 - Générateur de documents pédagogiques"}

@api_router.get("/catalog")
async def get_catalog():
    """Get the curriculum catalog"""
    catalog = []
    for matiere, niveaux in CURRICULUM_DATA.items():
        levels = []
        for niveau, chapitres in niveaux.items():
            levels.append({
                "name": niveau,
                "chapters": chapitres
            })
        catalog.append({
            "name": matiere,
            "levels": levels
        })
    return {"catalog": catalog}

@api_router.get("/pricing")
async def get_pricing():
    """Get pricing packages"""
    return {"packages": PRICING_PACKAGES}

@api_router.get("/analytics/overview")
async def get_analytics_overview(request: Request):
    """Get basic analytics overview (Pro only)"""
    try:
        user_email = await require_pro_user(request)
        logger.info(f"Analytics overview requested by Pro user: {user_email}")
        
        # Get user's documents count
        user_documents = await db.documents.count_documents({"user_id": user_email})
        guest_documents = await db.documents.count_documents({"guest_id": {"$regex": f".*{user_email.split('@')[0]}.*"}})
        
        # Get user's exports count
        user_exports = await db.exports.count_documents({"user_email": user_email})
        
        # Get recent activity (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_documents = await db.documents.count_documents({
            "$or": [{"user_id": user_email}, {"guest_id": {"$regex": f".*{user_email.split('@')[0]}.*"}}],
            "created_at": {"$gte": thirty_days_ago}
        })
        
        recent_exports = await db.exports.count_documents({
            "user_email": user_email,
            "created_at": {"$gte": thirty_days_ago}
        })
        
        # Get subject distribution
        subject_pipeline = [
            {"$match": {"$or": [{"user_id": user_email}, {"guest_id": {"$regex": f".*{user_email.split('@')[0]}.*"}}]}},
            {"$group": {"_id": "$matiere", "count": {"$sum": 1}}}
        ]
        subject_stats = await db.documents.aggregate(subject_pipeline).to_list(None)
        
        # Get template usage stats
        template_pipeline = [
            {"$match": {"user_email": user_email}},
            {"$group": {"_id": "$template_used", "count": {"$sum": 1}}}
        ]
        template_stats = await db.exports.aggregate(template_pipeline).to_list(None)
        
        return {
            "user_analytics": {
                "total_documents": user_documents + guest_documents,
                "total_exports": user_exports,
                "recent_activity": {
                    "documents_last_30_days": recent_documents,
                    "exports_last_30_days": recent_exports
                },
                "subject_distribution": [
                    {"subject": stat["_id"], "count": stat["count"]} 
                    for stat in subject_stats
                ],
                "template_usage": [
                    {"template": stat["_id"] or "standard", "count": stat["count"]} 
                    for stat in template_stats
                ],
                "subscription_info": {
                    "type": "Pro",
                    "analytics_enabled": True
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching analytics overview: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des analytics")

@api_router.get("/analytics/usage")
async def get_usage_analytics(request: Request, days: int = 30):
    """Get detailed usage analytics over time (Pro only)"""
    try:
        user_email = await require_pro_user(request)
        logger.info(f"Usage analytics requested by Pro user: {user_email} for {days} days")
        
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Daily document generation
        daily_docs_pipeline = [
            {
                "$match": {
                    "$or": [{"user_id": user_email}, {"guest_id": {"$regex": f".*{user_email.split('@')[0]}.*"}}],
                    "created_at": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "documents": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        daily_docs = await db.documents.aggregate(daily_docs_pipeline).to_list(None)
        
        # Daily exports
        daily_exports_pipeline = [
            {
                "$match": {
                    "user_email": user_email,
                    "created_at": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "exports": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        daily_exports = await db.exports.aggregate(daily_exports_pipeline).to_list(None)
        
        # Subject popularity over time
        subject_timeline_pipeline = [
            {
                "$match": {
                    "$or": [{"user_id": user_email}, {"guest_id": {"$regex": f".*{user_email.split('@')[0]}.*"}}],
                    "created_at": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                        "subject": "$matiere"
                    },
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id.date": 1}}
        ]
        subject_timeline = await db.documents.aggregate(subject_timeline_pipeline).to_list(None)
        
        return {
            "usage_analytics": {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                },
                "daily_activity": {
                    "documents": [
                        {"date": doc["_id"], "count": doc["documents"]} 
                        for doc in daily_docs
                    ],
                    "exports": [
                        {"date": exp["_id"], "count": exp["exports"]} 
                        for exp in daily_exports
                    ]
                },
                "subject_timeline": [
                    {
                        "date": item["_id"]["date"], 
                        "subject": item["_id"]["subject"], 
                        "count": item["count"]
                    }
                    for item in subject_timeline
                ]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching usage analytics: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des analytics d'usage")

@api_router.post("/generate")
async def generate_document(request: GenerateRequest):
    """Generate a document with exercises"""
    try:
        # Validate the curriculum selection
        if request.matiere not in CURRICULUM_DATA:
            raise HTTPException(status_code=400, detail="Matière non supportée")
        
        if request.niveau not in CURRICULUM_DATA[request.matiere]:
            raise HTTPException(status_code=400, detail="Niveau non supporté pour cette matière")
        
        if request.chapitre not in CURRICULUM_DATA[request.matiere][request.niveau]:
            raise HTTPException(status_code=400, detail="Chapitre non trouvé pour ce niveau")
        
        # Generate exercises
        exercises = await generate_exercises_with_ai(
            request.matiere,
            request.niveau,
            request.chapitre,
            request.type_doc,
            request.difficulte,
            request.nb_exercices
        )
        
        # Create document
        document = Document(
            guest_id=request.guest_id,
            matiere=request.matiere,
            niveau=request.niveau,
            chapitre=request.chapitre,
            type_doc=request.type_doc,
            difficulte=request.difficulte,
            nb_exercices=request.nb_exercices,
            exercises=exercises
        )
        
        # Save to database
        doc_dict = document.dict()
        # Convert datetime for MongoDB
        doc_dict['created_at'] = doc_dict['created_at'].isoformat()
        await db.documents.insert_one(doc_dict)
        
        # Return the document (already processed during generation)
        return {"document": document}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating document: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la génération du document")

@api_router.post("/auth/request-login")
async def request_login(request: LoginRequest):
    """Request a magic link for Pro user login"""
    try:
        # Check if user exists and is Pro
        is_pro, user = await check_user_pro_status(request.email)
        
        if not is_pro:
            # Don't reveal if user exists or not for security
            raise HTTPException(
                status_code=404, 
                detail="Utilisateur Pro non trouvé ou abonnement expiré"
            )
        
        # Generate magic link token (short-lived, 15 minutes)
        magic_token = str(uuid.uuid4()) + "-magic-" + str(int(datetime.now(timezone.utc).timestamp()))
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        
        # Store magic token temporarily
        await db.magic_tokens.insert_one({
            "token": magic_token,
            "email": request.email,
            "expires_at": expires_at,
            "used": False,
            "created_at": datetime.now(timezone.utc)
        })
        
        # Send magic link email
        email_sent = await send_magic_link_email(request.email, magic_token)
        
        if not email_sent:
            raise HTTPException(
                status_code=500,
                detail="Erreur lors de l'envoi de l'email"
            )
        
        return {
            "message": "Lien de connexion envoyé par email",
            "email": request.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in request login: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la demande de connexion"
        )

@api_router.post("/auth/verify-login")
async def verify_login(request: VerifyLoginRequest):
    """Verify magic link token and create session"""
    try:
        logger.info(f"Attempting to verify login with token: {request.token[:20]}...")
        
        # Find magic token
        magic_token_doc = await db.magic_tokens.find_one({
            "token": request.token,
            "used": False
        })
        
        if not magic_token_doc:
            logger.warning(f"Magic token not found or already used: {request.token[:20]}...")
            
            # Check if token exists but is used
            used_token = await db.magic_tokens.find_one({"token": request.token})
            if used_token:
                logger.info("Token exists but is already used")
                raise HTTPException(
                    status_code=400,
                    detail="Token déjà utilisé"
                )
            else:
                logger.info("Token does not exist in database")
                raise HTTPException(
                    status_code=400,
                    detail="Token invalide"
                )
        
        logger.info(f"Magic token found for email: {magic_token_doc.get('email')}")
        
        # Check token expiration
        expires_at = magic_token_doc.get('expires_at')
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at).replace(tzinfo=timezone.utc)
        elif isinstance(expires_at, datetime) and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        
        if expires_at < now:
            logger.warning(f"Token expired: expires_at={expires_at}, now={now}")
            # Token expired
            await db.magic_tokens.delete_one({"token": request.token})
            raise HTTPException(
                status_code=400,
                detail="Token expiré"
            )
        
        email = magic_token_doc.get('email')
        logger.info(f"Token is valid for email: {email}")
        
        # Verify user is still Pro
        is_pro, user = await check_user_pro_status(email)
        if not is_pro:
            logger.warning(f"User {email} is no longer Pro")
            raise HTTPException(
                status_code=403,
                detail="Abonnement Pro expiré"
            )
        
        logger.info(f"User {email} confirmed as Pro")
        
        # Mark token as used
        await db.magic_tokens.update_one(
            {"token": request.token},
            {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}}
        )
        logger.info(f"Magic token marked as used for {email}")
        
        # Create login session
        session_token = await create_login_session(email, request.device_id)
        
        if not session_token:
            logger.error("Failed to create login session")
            raise HTTPException(
                status_code=500,
                detail="Erreur lors de la création de la session"
            )
        
        logger.info(f"Login session created successfully for {email}")
        
        return {
            "message": "Connexion réussie",
            "email": email,
            "session_token": session_token,
            "expires_in": "24h"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in verify login: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la vérification du token"
        )

@api_router.post("/auth/logout")
async def logout(request: Request):
    """Logout user by invalidating session"""
    try:
        # Get session token from header
        session_token = request.headers.get("X-Session-Token")
        
        if not session_token:
            raise HTTPException(
                status_code=400,
                detail="Token de session manquant"
            )
        
        # Remove session
        result = await db.login_sessions.delete_one({"session_token": session_token})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Session non trouvée"
            )
        
        return {"message": "Déconnexion réussie"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in logout: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la déconnexion"
        )

@api_router.get("/subscription/status/{email}")
async def get_subscription_status(email: str):
    """Get detailed subscription status for an email"""
    try:
        is_pro, user = await check_user_pro_status(email)
        
        if not is_pro or not user:
            return {
                "is_pro": False,
                "message": "Aucun abonnement actif trouvé pour cette adresse email"
            }
        
        subscription_expires = user.get("subscription_expires")
        subscription_type = user.get("subscription_type", "inconnu")
        
        # Format dates
        if isinstance(subscription_expires, str):
            expires_date = datetime.fromisoformat(subscription_expires).replace(tzinfo=timezone.utc)
        elif isinstance(subscription_expires, datetime):
            expires_date = subscription_expires.replace(tzinfo=timezone.utc) if subscription_expires.tzinfo is None else subscription_expires
        else:
            expires_date = datetime.now(timezone.utc)
        
        now = datetime.now(timezone.utc)
        days_remaining = (expires_date - now).days
        
        return {
            "is_pro": True,
            "email": email,
            "subscription_type": subscription_type,
            "subscription_expires": expires_date.isoformat(),
            "expires_date_formatted": expires_date.strftime("%d/%m/%Y"),
            "days_remaining": max(0, days_remaining),
            "is_active": expires_date > now,
            "last_login": user.get("last_login"),
            "created_at": user.get("created_at")
        }
        
    except Exception as e:
        logger.error(f"Error getting subscription status for {email}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la vérification du statut d'abonnement")

@api_router.get("/template/styles")
async def get_template_styles():
    """Get available template styles (public endpoint)"""
    return {
        "styles": {
            style_id: {
                "name": style["name"],
                "description": style["description"],
                "preview_colors": {
                    "primary": style["primary_color"],
                    "secondary": style["secondary_color"], 
                    "accent": style["accent_color"]
                }
            }
            for style_id, style in TEMPLATE_STYLES.items()
        }
    }

@api_router.get("/export/styles")
async def get_export_styles(request: Request):
    """Get available export template styles based on user status"""
    try:
        # Check if user is Pro
        session_token = request.headers.get("X-Session-Token")
        is_pro = False
        
        if session_token:
            email = await validate_session_token(session_token)
            if email:
                is_pro, _ = await check_user_pro_status(email)
        
        # Filter styles based on user status
        available_styles = {}
        for style_id, style in EXPORT_TEMPLATE_STYLES.items():
            if "free" in style["available_for"] or (is_pro and "pro" in style["available_for"]):
                available_styles[style_id] = {
                    "name": style["name"],
                    "description": style["description"],
                    "preview_image": style["preview_image"],
                    "pro_only": "free" not in style["available_for"]
                }
        
        return {
            "styles": available_styles,
            "user_is_pro": is_pro
        }
        
    except Exception as e:
        logger.error(f"Error getting export styles: {e}")
        # Return at least the free style on error
        return {
            "styles": {
                "classique": {
                    "name": "Classique",
                    "description": "Style traditionnel élégant",
                    "preview_image": "/api/template-previews/classique.png",
                    "pro_only": False
                }
            },
            "user_is_pro": False
        }

@api_router.get("/template/get")
async def get_user_template(request: Request):
    """Get user's template configuration (Pro only)"""
    try:
        user_email = await require_pro_user(request)
        
        # Find user template
        template_doc = await db.user_templates.find_one({"user_email": user_email})
        
        if not template_doc:
            # Return default template
            default_template = UserTemplate(
                user_email=user_email,
                template_style="minimaliste"
            )
            return default_template.dict()
        
        # Convert to UserTemplate object
        template = UserTemplate(**template_doc)
        return template.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user template: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors du chargement du template")

class TemplateSaveRequest(BaseModel):
    professor_name: Optional[str] = None
    school_name: Optional[str] = None
    school_year: Optional[str] = None
    footer_text: Optional[str] = None
    template_style: str = "minimaliste"

@api_router.post("/template/save")
async def save_user_template(
    request: Request,
    professor_name: Optional[str] = Form(None),
    school_name: Optional[str] = Form(None),
    school_year: Optional[str] = Form(None),
    footer_text: Optional[str] = Form(None),
    template_style: str = Form("minimaliste"),
    logo: Optional[UploadFile] = File(None)
):
    """Save user's template configuration (Pro only)"""
    try:
        user_email = await require_pro_user(request)
        
        # Debug logging
        logger.info(f"🔍 Template save request for {user_email}: professor_name={professor_name}, school_name={school_name}, school_year={school_year}, footer_text={footer_text}, template_style={template_style}")
        
        # Handle logo upload
        logo_url = None
        logo_filename = None
        
        if logo and logo.filename:
            logger.info(f"🖼️ Logo upload detected: {logo.filename}, size: {logo.size}, content_type: {logo.content_type}")
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if logo.content_type not in allowed_types:
                raise HTTPException(status_code=400, detail="Type de fichier non supporté. Utilisez JPG, PNG, GIF ou WebP.")
            
            # Validate file size (max 5MB)
            if logo.size and logo.size > 5 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Fichier trop volumineux. Taille maximum: 5MB.")
            
            # Create uploads directory if it doesn't exist
            uploads_dir = ROOT_DIR / "uploads" / "logos"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename
            import uuid
            file_extension = logo.filename.split('.')[-1].lower()
            logo_filename = f"logo_{user_email.replace('@', '_').replace('.', '_')}_{uuid.uuid4().hex[:8]}.{file_extension}"
            logo_path = uploads_dir / logo_filename
            
            # Save file
            with open(logo_path, "wb") as buffer:
                content = await logo.read()
                buffer.write(content)
            
            # Create URL (relative path for serving)
            logo_url = f"/uploads/logos/{logo_filename}"
            logger.info(f"✅ Logo saved: {logo_path} -> {logo_url}")
        
        # Validate template style
        if template_style not in TEMPLATE_STYLES:
            raise HTTPException(status_code=400, detail="Style de template invalide")
        
        # Get current template or create new one
        existing_template = await db.user_templates.find_one({"user_email": user_email})
        
        if existing_template:
            # Update existing
            update_data = {
                "professor_name": professor_name,
                "school_name": school_name,
                "school_year": school_year,
                "footer_text": footer_text,
                "template_style": template_style,
                "updated_at": datetime.now(timezone.utc)
            }
            
            # Add logo data if uploaded
            if logo_url:
                update_data["logo_url"] = logo_url
                update_data["logo_filename"] = logo_filename
            
            logger.info(f"🔍 Updating existing template with data: {update_data}")
            
            await db.user_templates.update_one(
                {"user_email": user_email},
                {"$set": update_data}
            )
            
            # Get updated template
            updated_template = await db.user_templates.find_one({"user_email": user_email})
            template = UserTemplate(**updated_template)
        else:
            # Create new template
            template = UserTemplate(
                user_email=user_email,
                professor_name=professor_name,
                school_name=school_name,
                school_year=school_year,
                footer_text=footer_text,
                template_style=template_style,
                logo_url=logo_url,
                logo_filename=logo_filename
            )
            
            logger.info(f"🔍 Creating new template: {template.dict()}")
            
            await db.user_templates.insert_one(template.dict())
        
        logger.info(f"Template saved for user: {user_email}")
        return {
            "message": "Template sauvegardé avec succès",
            "template": template.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving user template: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la sauvegarde du template")

@api_router.get("/pdf/options")
async def get_pdf_options():
    """Get available PDF layout options (public endpoint)"""
    return {
        "layout_options": {
            "page_formats": [
                {"id": "A4", "name": "A4 Standard", "description": "Format A4 classique (21 × 29,7 cm)"},
                {"id": "A4_compact", "name": "A4 Compact", "description": "Format A4 avec marges réduites"},
                {"id": "US_Letter", "name": "US Letter", "description": "Format américain (8,5 × 11 pouces)"}
            ],
            "margin_presets": [
                {"id": "standard", "name": "Standard", "description": "Marges équilibrées (2,5cm haut/bas, 2cm gauche/droite)"},
                {"id": "compact", "name": "Compact", "description": "Marges réduites (1,5cm partout)"},
                {"id": "generous", "name": "Généreux", "description": "Marges importantes (3cm haut/bas, 2,5cm gauche/droite)"}
            ],
            "content_options": [
                {"id": "show_difficulty", "name": "Afficher la difficulté", "default": True},
                {"id": "show_creation_date", "name": "Afficher la date de création", "default": True},
                {"id": "show_exercise_numbers", "name": "Numéroter les exercices", "default": True},
                {"id": "show_point_values", "name": "Afficher les barèmes", "default": True},
                {"id": "include_instructions", "name": "Inclure les consignes", "default": True}
            ],
            "visual_options": [
                {"id": "page_numbering", "name": "Numérotation des pages", "options": [
                    {"value": "bottom_center", "label": "Bas centré"},
                    {"value": "bottom_right", "label": "Bas droite"},
                    {"value": "top_right", "label": "Haut droite"},
                    {"value": "none", "label": "Aucune"}
                ]},
                {"id": "exercise_separator", "name": "Séparateur d'exercices", "options": [
                    {"value": "line", "label": "Ligne"},
                    {"value": "space", "label": "Espace"},
                    {"value": "box", "label": "Encadré"},
                    {"value": "none", "label": "Aucun"}
                ]},
                {"id": "question_numbering", "name": "Numérotation des questions", "options": [
                    {"value": "arabic", "label": "1, 2, 3..."},
                    {"value": "roman", "label": "I, II, III..."},
                    {"value": "letters", "label": "a, b, c..."},
                    {"value": "none", "label": "Aucune"}
                ]}
            ]
        }
    }

@api_router.get("/quota/check")
@log_execution_time("check_quota_status")
async def check_quota_status(guest_id: str):
    """Check current quota status for guest user"""
    logger = get_logger()
    logger.info(
        "Checking quota status",
        module_name="quota",
        func_name="check_quota_status",
        user_type="guest",
        guest_id=guest_id[:8] + "..." if guest_id and len(guest_id) > 8 else guest_id
    )
    
    result = await check_guest_quota(guest_id)
    
    logger.info(
        "Quota check completed",
        module_name="quota",
        func_name="check_quota_status",
        user_type="guest",
        current_count=result.get("current_count", 0),
        limit=result.get("limit", 0),
        can_generate=result.get("can_generate", False)
    )
    
    return result
@api_router.get("/auth/session/validate")
async def validate_session(request: Request):
    """Validate current session and return user info"""
    try:
        session_token = request.headers.get("X-Session-Token")
        
        if not session_token:
            raise HTTPException(
                status_code=401,
                detail="Token de session manquant"
            )
        
        email = await validate_session_token(session_token)
        
        if not email:
            raise HTTPException(
                status_code=401,
                detail="Session invalide ou expirée"
            )
        
        # Check if user is still Pro
        is_pro, user = await check_user_pro_status(email)
        
        if not is_pro:
            # Clean up session if user is no longer Pro
            await db.login_sessions.delete_one({"session_token": session_token})
            raise HTTPException(
                status_code=403,
                detail="Abonnement Pro expiré"
            )
        
        return {
            "email": email,
            "is_pro": True,
            "subscription_expires": user.get('subscription_expires'),
            "last_login": user.get('last_login')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la validation de session"
        )
async def check_quota_status(guest_id: str):
    """Check current quota status for guest user"""
    return await check_guest_quota(guest_id)

def get_template_colors_and_fonts(template_config):
    """Get CSS colors and fonts for WeasyPrint templates based on template configuration"""
    style_name = template_config.get('template_style', 'minimaliste')
    template_style = TEMPLATE_STYLES.get(style_name, TEMPLATE_STYLES['minimaliste'])
    
    return {
        'template_colors': {
            'primary': template_style['primary_color'],
            'secondary': template_style['secondary_color'],
            'accent': template_style['accent_color']
        },
        'template_fonts': {
            'header': template_style['header_font'].replace('-', ' '),
            'content': template_style['content_font'].replace('-', ' ')
        }
    }

@api_router.post("/export")
@log_execution_time("export_pdf")
async def export_pdf(request: ExportRequest, http_request: Request):
    """Export document as PDF using unified WeasyPrint approach"""
    logger = get_logger()
    
    logger.info(
        "Starting PDF export",
        module_name="export",
        func_name="export_pdf",
        doc_id=request.document_id,
        export_type=request.export_type,
        template_style=getattr(request, 'template_style', 'default')
    )
    
    try:
        # Check authentication - ONLY session token method (no legacy email fallback)
        session_token = http_request.headers.get("X-Session-Token")
        is_pro_user = False
        user_email = None
        template_config = {}
        
        # Authenticate using session token only
        if session_token:
            logger.info(f"Session token provided: {session_token[:20]}...")
            email = await validate_session_token(session_token)
            if email:
                logger.info(f"Session token validated for email: {email}")
                is_pro, user = await check_user_pro_status(email)
                is_pro_user = is_pro
                user_email = email
                logger.info(f"Pro status check result - email: {email}, is_pro: {is_pro}")
                
                # Load user template configuration if Pro
                if is_pro:
                    logger.info(f"Loading template config for Pro user: {email}")
                    try:
                        template_doc = await db.user_templates.find_one({"user_email": email})
                        logger.info(f"🔍 Raw template doc from DB: {template_doc}")
                        if template_doc:
                            template_config = {
                                'template_style': template_doc.get('template_style', 'minimaliste'),
                                'professor_name': template_doc.get('professor_name'),
                                'school_name': template_doc.get('school_name'),
                                'school_year': template_doc.get('school_year'),
                                'footer_text': template_doc.get('footer_text'),
                                'logo_url': template_doc.get('logo_url'),
                                'logo_filename': template_doc.get('logo_filename')
                            }
                            logger.info(f"🔍 Processed template config for {email}: {template_config}")
                            
                            # Vérifier si on a des données réelles
                            has_real_data = any([
                                template_config.get('professor_name'),
                                template_config.get('school_name'),
                                template_config.get('school_year'),
                                template_config.get('footer_text')
                            ])
                            logger.info(f"🔍 Template has real data: {has_real_data}")
                        else:
                            # Default template for Pro users
                            template_config = {'template_style': 'minimaliste'}
                            logger.info(f"Using default template for Pro user {email}")
                    except Exception as e:
                        logger.error(f"Error loading template config: {e}")
                        template_config = {'template_style': 'minimaliste'}
                else:
                    logger.info(f"User {email} is not Pro - using standard PDF generation")
            else:
                logger.info("Session token validation failed - treating as guest")
        else:
            logger.info("No session token provided - treating as guest user")
        
        # Pro users have unlimited exports
        if not is_pro_user:
            # Check guest quota
            if not request.guest_id:
                raise HTTPException(status_code=400, detail="Guest ID required for non-Pro users")
                
            quota_status = await check_guest_quota(request.guest_id)
            
            if quota_status["quota_exceeded"]:
                raise HTTPException(status_code=402, detail={
                    "error": "quota_exceeded", 
                    "message": "Limite de 3 exports gratuits atteinte. Passez à l'abonnement Pro pour continuer.",
                    "action": "upgrade_required"
                })
        
        # Find the document
        doc = await db.documents.find_one({"id": request.document_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Document non trouvé")
        
        # CRITICAL: Process geometric schemas and LaTeX before PDF generation
        
        if 'exercises' in doc:
            for exercise in doc['exercises']:
                if 'enonce' in exercise and exercise['enonce']:
                    exercise['enonce'] = process_exercise_content(exercise['enonce'])
                
                # NEW: Generate SVG for schema if present in donnees
                if exercise.get('donnees') and isinstance(exercise['donnees'], dict):
                    schema_data = exercise['donnees'].get('schema')
                    if schema_data:
                        # Reconcile schema with enonce text before rendering
                        enonce = exercise.get('enonce', '')
                        enriched_schema = reconcile_enonce_schema(enonce, schema_data)
                        
                        schema_type = enriched_schema.get('type', 'unknown')
                        logger.info(
                            "Generating SVG for PDF schema",
                            module_name="export",
                            func_name="generate_svg",
                            doc_id=request.document_id,
                            schema_type=schema_type
                        )
                        
                        # Update the schema data with enriched version
                        exercise['donnees']['schema'] = enriched_schema
                        
                        svg_content = schema_renderer.render_to_svg(enriched_schema)
                        if svg_content:
                            exercise['schema_svg'] = svg_content
                            logger.info(
                                "SVG generated successfully for PDF",
                                module_name="export",
                                func_name="generate_svg",
                                doc_id=request.document_id,
                                schema_type=schema_type,
                                svg_length=len(svg_content),
                                status="success"
                            )
                            log_schema_processing(schema_type, True, doc_id=request.document_id)
                        else:
                            logger.warning(
                                "Failed to generate SVG for PDF schema",
                                module_name="export",
                                func_name="generate_svg",
                                doc_id=request.document_id,
                                schema_type=schema_type,
                                status="failed"
                            )
                            log_schema_processing(schema_type, False, doc_id=request.document_id)
                            exercise['schema_svg'] = ""
                    else:
                        exercise['schema_svg'] = ""
                else:
                    exercise['schema_svg'] = ""
                
                # Process solution if it exists
                if exercise.get('solution'):
                    if exercise['solution'].get('resultat'):
                        exercise['solution']['resultat'] = process_exercise_content(exercise['solution']['resultat'])
                        
                    if exercise['solution'].get('etapes') and isinstance(exercise['solution']['etapes'], list):
                        exercise['solution']['etapes'] = [
                            process_exercise_content(step) for step in exercise['solution']['etapes']
                        ]
            

        # Convert to Document object
        if isinstance(doc.get('created_at'), str):
            doc['created_at'] = datetime.fromisoformat(doc['created_at'])
        document = Document(**doc)
        
        # NEW TEMPLATE STYLE SYSTEM - Choose template based on requested style
        requested_style = request.template_style or "classique"
        logger.info(f"🎨 TEMPLATE STYLE EXPORT - Requested style: {requested_style}, Pro user: {is_pro_user}")
        
        # Validate style permission
        if requested_style not in EXPORT_TEMPLATE_STYLES:
            logger.warning(f"Invalid template style: {requested_style}, falling back to classique")
            requested_style = "classique"
        
        style_config = EXPORT_TEMPLATE_STYLES[requested_style]
        
        # Check if user has permission for this style
        if "free" not in style_config["available_for"] and not is_pro_user:
            logger.info(f"Style {requested_style} is Pro-only, user is not Pro. Using classique instead.")
            requested_style = "classique"
            style_config = EXPORT_TEMPLATE_STYLES["classique"]
        
        # Choose the correct template file
        if request.export_type == "sujet":
            template_name = style_config["sujet_template"]
        else:
            template_name = style_config["corrige_template"]
        
        logger.info(f"📄 Using template: {template_name} for style: {requested_style}")
        template_content = load_template(template_name)
        
        # Prepare render context
        render_context = {
            'document': document,
            'date_creation': datetime.now(timezone.utc).strftime("%d/%m/%Y"),
            'template_style': requested_style,  # Add template style for schema theming
        }
        
        # Add Pro personalization if available
        if is_pro_user and template_config:
            render_context['template_config'] = template_config
            render_context['school_name'] = template_config.get('school_name')
            render_context['professor_name'] = template_config.get('professor_name')
            render_context['school_year'] = template_config.get('school_year')
            render_context['footer_text'] = template_config.get('footer_text')
            render_context['logo_filename'] = template_config.get('logo_filename')
            
            # Add template style for schema theming
            render_context['template_style'] = template_config.get('template_style', 'academique')
            
            # Convert logo URL to absolute file path for WeasyPrint
            logo_url = template_config.get('logo_url')
            if logo_url and logo_url.startswith('/uploads/'):
                logo_file_path = ROOT_DIR / logo_url[1:]  # Remove leading slash
                if logo_file_path.exists():
                    absolute_logo_url = f"file://{logo_file_path}"
                    render_context['logo_url'] = absolute_logo_url
                    template_config['logo_url'] = absolute_logo_url
                    logger.info(f"✅ Logo converted for WeasyPrint: {logo_file_path}")
                else:
                    logger.warning(f"⚠️ Logo file not found: {logo_file_path}")
                    render_context['logo_url'] = None
                    template_config['logo_url'] = None
            else:
                render_context['logo_url'] = logo_url
            
            logger.info(f"🔍 FINAL RENDER CONTEXT FOR PRO USER:")
            logger.info(f"   school_name: {render_context.get('school_name')}")
            logger.info(f"   professor_name: {render_context.get('professor_name')}")
            logger.info(f"   logo_url: {render_context.get('logo_url')}")
       
        # Generate filename with style suffix
        filename = f"LeMaitremot_{document.type_doc}_{document.matiere}_{document.niveau}_{request.export_type}_{requested_style}.pdf"
        
        # Process LaTeX expressions in document before rendering
        logger.info("🔬 Converting LaTeX expressions to SVG...")
        
        # Convert document to dict for processing (to avoid Pydantic read-only issues)
        document_dict = document.dict()
        
        # Process each exercise and convert LaTeX to SVG
        try:
            for exercise in document_dict.get('exercises', []):
                # Process exercise statement
                if 'enonce' in exercise and exercise['enonce']:
                    # First process geometric schemas, then LaTeX
                    exercise['enonce'] = geometry_renderer.process_geometric_schemas(exercise['enonce'])
                    exercise['enonce'] = latex_renderer.convert_latex_to_svg(exercise['enonce'])
                
                # Process QCM options if they exist
                if (exercise.get('type') == 'qcm' and 
                    exercise.get('donnees') and 
                    exercise['donnees'].get('options')):
                    exercise['donnees']['options'] = [
                        latex_renderer.convert_latex_to_svg(
                            geometry_renderer.process_geometric_schemas(option)
                        )
                        for option in exercise['donnees']['options']
                    ]
                
                # Process solution if it exists
                if exercise.get('solution'):
                    # Process result
                    if exercise['solution'].get('resultat'):
                        processed_result = geometry_renderer.process_geometric_schemas(
                            exercise['solution']['resultat']
                        )
                        exercise['solution']['resultat'] = latex_renderer.convert_latex_to_svg(
                            processed_result
                        )
                    # Process steps
                    if exercise['solution'].get('etapes') and isinstance(exercise['solution']['etapes'], list):
                        exercise['solution']['etapes'] = [
                            latex_renderer.convert_latex_to_svg(
                                geometry_renderer.process_geometric_schemas(step)
                            )
                            for step in exercise['solution']['etapes']
                        ]
        
        except Exception as e:
            logger.error(f"Error during LaTeX to SVG conversion: {e}")
            # Continue with original document if conversion fails
            document_dict = document.dict()
        
        # Update render context with processed document
        render_context['document'] = document_dict
        
        # Generate SVG schemas for each exercise (before template render)
        exercises = document_dict.get('exercises', [])
        for i, exercise in enumerate(exercises, start=1):
            schema_data = None
            
            # Check for schema in donnees
            if exercise.get('donnees') and isinstance(exercise.get('donnees'), dict):
                schema_data = exercise.get('donnees').get('schema')
            
            if schema_data:
                try:
                    svg_content = schema_renderer.render_to_svg(schema_data)
                    if svg_content:
                        exercise['schema_svg'] = svg_content
                        logger.info(f"[EXPORT][PDF] Generated SVG for Exercice {i} - schema_svg length = {len(svg_content)}")
                    else:
                        logger.warning(f"[EXPORT][PDF] Failed to render schema for Exercice {i}")
                except Exception as e:
                    logger.error(f"[EXPORT][PDF] Error rendering schema for Exercice {i}: {e}")
        
        # Log schema_svg presence for debugging
        for i, ex in enumerate(exercises, start=1):
            schema_svg_length = len(ex.get('schema_svg', ''))
            logger.info(f"[EXPORT][PDF] Exercice {i} - schema_svg length = {schema_svg_length}")
        
        # Render HTML using Jinja2
        logger.info("🔧 Generating PDF with WeasyPrint...")
        template = Template(template_content)
        html_content = template.render(**render_context)
        
        logger.info("✅ Mathematical expressions converted to SVG")
        
        # Generate PDF with WeasyPrint
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.write(pdf_bytes)
        temp_file.close()
        
        # Track export for guest quota (only for non-Pro users)
        if not is_pro_user and request.guest_id:
            export_record = {
                "id": str(uuid.uuid4()),
                "document_id": request.document_id,
                "export_type": request.export_type,
                "guest_id": request.guest_id,
                "user_email": user_email,
                "is_pro": is_pro_user,
                "template_used": template_config.get('template_style') if template_config else 'standard',
                "created_at": datetime.now(timezone.utc)
            }
            await db.exports.insert_one(export_record)
        
        logger.info(f"✅ PDF generated successfully: {filename}")
        
        return FileResponse(
            temp_file.name,
            media_type='application/pdf',
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting PDF: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'export PDF")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting PDF: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'export PDF")

@api_router.post("/export/advanced")
async def export_pdf_advanced(request: EnhancedExportRequest, http_request: Request):
    """Export document as PDF with advanced layout options (Pro only)"""
    try:
        # Check authentication - Pro only feature
        session_token = http_request.headers.get("X-Session-Token")
        if not session_token:
            raise HTTPException(status_code=401, detail="Session token requis pour les options avancées")
        
        email = await validate_session_token(session_token)
        if not email:
            raise HTTPException(status_code=401, detail="Session token invalide")
        
        is_pro, user = await check_user_pro_status(email)
        if not is_pro:
            raise HTTPException(status_code=403, detail="Fonctionnalité Pro uniquement")
        
        logger.info(f"Advanced PDF export requested by Pro user: {email}")
        
        # Get document
        document = await db.documents.find_one({"id": request.document_id})
        if not document:
            raise HTTPException(status_code=404, detail="Document non trouvé")
        
        # CRITICAL: Process geometric schemas and LaTeX before PDF generation
        if 'exercises' in document:
            for exercise in document['exercises']:
                if 'enonce' in exercise and exercise['enonce']:
                    exercise['enonce'] = process_exercise_content(exercise['enonce'])
                
                # Process solution if it exists
                if exercise.get('solution'):
                    if exercise['solution'].get('resultat'):
                        exercise['solution']['resultat'] = process_exercise_content(exercise['solution']['resultat'])
                        
                    if exercise['solution'].get('etapes') and isinstance(exercise['solution']['etapes'], list):
                        exercise['solution']['etapes'] = [
                            process_exercise_content(step) for step in exercise['solution']['etapes']
                        ]
        
        # Load user template configuration
        template_config = {}
        template_doc = await db.user_templates.find_one({"user_email": email})
        if template_doc:
            template_config = {
                'template_style': template_doc.get('template_style', 'minimaliste'),
                'professor_name': template_doc.get('professor_name'),
                'school_name': template_doc.get('school_name'),
                'school_year': template_doc.get('school_year'),
                'footer_text': template_doc.get('footer_text'),
                'logo_url': template_doc.get('logo_url'),
                'logo_filename': template_doc.get('logo_filename')
            }
        else:
            template_config = {'template_style': 'minimaliste'}
        
        # Apply advanced options
        advanced_opts = request.advanced_options or AdvancedPDFOptions()
        
        # Generate content with advanced formatting
        if request.export_type == "sujet":
            content = format_exercises_for_export(document["exercises"], advanced_opts)
        else:  # corrige
            content = format_solutions_for_export(document["exercises"], advanced_opts)
        
        # Generate PDF with advanced layout
        pdf_content = await generate_advanced_pdf(
            document, content, request.export_type, template_config, advanced_opts
        )
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.write(pdf_content)
        temp_file.close()
        
        # Generate filename
        filename = f"LeMaitremot_{request.export_type}_{document['matiere']}_{document['niveau']}_advanced.pdf"
        
        # Record export
        export_record = {
            "id": str(uuid.uuid4()),
            "document_id": request.document_id,
            "export_type": request.export_type,
            "user_email": email,
            "is_pro": True,
            "template_used": template_config.get('template_style', 'minimaliste'),
            "advanced_options": advanced_opts.dict(),
            "created_at": datetime.now(timezone.utc)
        }
        await db.exports.insert_one(export_record)
        
        logger.info(f"✅ Advanced PDF generated successfully: {filename}")
        
        return FileResponse(
            temp_file.name,
            media_type='application/pdf',
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting advanced PDF: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'export PDF avancé")

@api_router.post("/checkout/session")
async def create_checkout_session(request: CheckoutRequest, http_request: Request):
    """Create Stripe checkout session"""
    try:
        # Validate package
        if request.package_id not in PRICING_PACKAGES:
            raise HTTPException(status_code=400, detail="Package invalide")
        
        # Check if email is already subscribed (anti-duplicate protection)
        if request.email:
            is_pro, existing_user = await check_user_pro_status(request.email)
            if is_pro and existing_user:
                subscription_expires = existing_user.get("subscription_expires")
                subscription_type = existing_user.get("subscription_type", "inconnu")
                
                # Format expiration date for display
                if isinstance(subscription_expires, str):
                    expires_date = datetime.fromisoformat(subscription_expires).replace(tzinfo=timezone.utc)
                elif isinstance(subscription_expires, datetime):
                    expires_date = subscription_expires.replace(tzinfo=timezone.utc) if subscription_expires.tzinfo is None else subscription_expires
                else:
                    expires_date = datetime.now(timezone.utc) + timedelta(days=30)  # fallback
                
                formatted_date = expires_date.strftime("%d/%m/%Y")
                
                logger.info(f"Duplicate subscription attempt for {request.email} - already Pro until {formatted_date}")
                
                raise HTTPException(
                    status_code=409,  # Conflict
                    detail={
                        "error": "already_subscribed",
                        "message": f"Cette adresse email dispose déjà d'un abonnement {subscription_type} actif jusqu'au {formatted_date}. Pour modifier votre abonnement, veuillez nous contacter.",
                        "subscription_type": subscription_type,
                        "expires_date": formatted_date,
                        "action": "contact_support"
                    }
                )
        
        package = PRICING_PACKAGES[request.package_id]
        logger.info(f"Creating checkout session for package: {package}")
        
        # Initialize Stripe
        host_url = str(http_request.base_url).rstrip('/')
        webhook_url = f"{host_url}/api/webhook/stripe"
        stripe_checkout = StripeCheckout(api_key=stripe_secret_key, webhook_url=webhook_url)
        
        # Build URLs from frontend origin
        success_url = f"{request.origin_url}/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{request.origin_url}/cancel"
        
        # Prepare metadata
        metadata = {
            "package_id": request.package_id,
            "email": request.email or "",
            "nom": request.nom or "",
            "etablissement": request.etablissement or "",
            "source": "lemaitremot_web"
        }
        
        # Create checkout session request
        checkout_request = CheckoutSessionRequest(
            amount=package["amount"],
            currency=package["currency"],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata
        )
        
        # Create session
        session = await stripe_checkout.create_checkout_session(checkout_request)
        
        # Store transaction
        transaction = PaymentTransaction(
            session_id=session.session_id,
            amount=package["amount"],
            currency=package["currency"],
            package_id=request.package_id,
            email=request.email,
            metadata=metadata,
            payment_status="pending",
            session_status="initiated"
        )
        
        # Save to database
        await db.payment_transactions.insert_one(transaction.dict())
        
        logger.info(f"Checkout session created: {session.session_id}")
        
        return {
            "url": session.url,
            "session_id": session.session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la création de la session")

@api_router.get("/checkout/status/{session_id}")
async def get_checkout_status(session_id: str):
    """Get checkout session status"""
    try:
        # Initialize Stripe
        stripe_checkout = StripeCheckout(api_key=stripe_secret_key, webhook_url="")
        
        # Get status from Stripe
        status = await stripe_checkout.get_checkout_status(session_id)
        
        # Find transaction in database
        transaction = await db.payment_transactions.find_one({"session_id": session_id})
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction non trouvée")
        
        # Update transaction status if payment completed
        if status.payment_status == "paid" and transaction.get("payment_status") != "paid":
            # Update transaction
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "payment_status": "paid",
                        "session_status": "complete",
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            # Create or update Pro user
            if transaction.get("email"):
                await create_pro_user_from_transaction(transaction, status)
        
        return {
            "session_id": session_id,
            "status": status.status,
            "payment_status": status.payment_status,
            "amount_total": status.amount_total,
            "currency": status.currency
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting checkout status: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la vérification du statut")

async def create_pro_user_from_transaction(transaction: dict, status):
    """Create Pro user from successful transaction"""
    try:
        package = PRICING_PACKAGES[transaction["package_id"]]
        
        # Calculate precise expiration date based on subscription type
        now = datetime.now(timezone.utc)
        if package["duration"] == "monthly":
            # Add exactly 1 month (30 days)
            expires = now + timedelta(days=30)
            logger.info(f"Monthly subscription: expires in 30 days ({expires.strftime('%d/%m/%Y %H:%M')})")
        else:  # yearly
            # Add exactly 1 year (365 days)
            expires = now + timedelta(days=365)
            logger.info(f"Yearly subscription: expires in 365 days ({expires.strftime('%d/%m/%Y %H:%M')})")
        
        # Check if user already exists (upgrade/renewal scenario)
        existing_user = await db.pro_users.find_one({"email": transaction["email"]})
        
        if existing_user:
            # User exists - extend subscription from current expiration or now, whichever is later
            current_expires = existing_user.get("subscription_expires")
            if current_expires:
                if isinstance(current_expires, str):
                    current_expires = datetime.fromisoformat(current_expires).replace(tzinfo=timezone.utc)
                elif isinstance(current_expires, datetime) and current_expires.tzinfo is None:
                    current_expires = current_expires.replace(tzinfo=timezone.utc)
                
                # If current subscription is still active, extend from expiration date
                if current_expires > now:
                    if package["duration"] == "monthly":
                        expires = current_expires + timedelta(days=30)
                    else:  # yearly
                        expires = current_expires + timedelta(days=365)
                    logger.info(f"Extending existing subscription from {current_expires.strftime('%d/%m/%Y')} to {expires.strftime('%d/%m/%Y')}")
        
        # Create/Update Pro user
        pro_user = ProUser(
            email=transaction["email"],
            nom=transaction.get("metadata", {}).get("nom") or existing_user.get("nom") if existing_user else None,
            etablissement=transaction.get("metadata", {}).get("etablissement") or existing_user.get("etablissement") if existing_user else None,
            subscription_type=package["duration"],
            subscription_expires=expires,
            last_login=existing_user.get("last_login") if existing_user else None
        )
        
        # Save to database (upsert)
        result = await db.pro_users.update_one(
            {"email": transaction["email"]},
            {"$set": pro_user.dict()},
            upsert=True
        )
        
        action = "updated" if result.matched_count > 0 else "created"
        logger.info(f"Pro user {action}: {transaction['email']} - {package['duration']} subscription expires {expires.strftime('%d/%m/%Y %H:%M')}")
        
        return expires
        
    except Exception as e:
        logger.error(f"Error creating pro user: {e}")
        return None

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    try:
        body = await request.body()
        stripe_signature = request.headers.get("Stripe-Signature")
        
        if not stripe_signature:
            raise HTTPException(status_code=400, detail="Missing Stripe signature")
        
        # Initialize Stripe
        stripe_checkout = StripeCheckout(api_key=stripe_secret_key, webhook_url="")
        
        # Handle webhook
        webhook_response = await stripe_checkout.handle_webhook(body, stripe_signature)
        
        logger.info(f"Webhook received: {webhook_response.event_type} for session {webhook_response.session_id}")
        
        # Process the webhook based on event type
        if webhook_response.event_type == "checkout.session.completed":
            # Find and update transaction
            await db.payment_transactions.update_one(
                {"session_id": webhook_response.session_id},
                {
                    "$set": {
                        "payment_status": webhook_response.payment_status,
                        "session_status": "complete",
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            # Get transaction details for user creation
            transaction = await db.payment_transactions.find_one({"session_id": webhook_response.session_id})
            if transaction and transaction.get("email"):
                # Create Pro user
                await create_pro_user_from_transaction(transaction, webhook_response)
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail="Webhook processing error")

@api_router.get("/user/status/{email}")
async def get_user_status(email: str):
    """Get user Pro status"""
    try:
        is_pro, user = await check_user_pro_status(email)
        
        if is_pro:
            return {
                "is_pro": True,
                "subscription_type": user.get("subscription_type"),
                "subscription_expires": user.get("subscription_expires"),
                "account_type": "pro"
            }
        else:
            return {
                "is_pro": False,
                "account_type": "guest"
            }
            
    except Exception as e:
        logger.error(f"Error getting user status: {e}")
        return {"is_pro": False, "account_type": "guest"}

@api_router.get("/documents")
@log_execution_time("get_documents")
async def get_documents(guest_id: str = None):
    """Get user documents"""
    logger = get_logger()
    user_type = "guest" if guest_id else "unknown"
    
    logger.info(
        "Starting document retrieval",
        module_name="documents",
        func_name="get_documents",
        user_type=user_type,
        guest_id=guest_id[:8] + "..." if guest_id and len(guest_id) > 8 else guest_id
    )
    
    try:
        if guest_id:
            # Get documents for guest user
            documents = await db.documents.find({"guest_id": guest_id}).sort("created_at", -1).limit(20).to_list(length=20)
        else:
            return {"documents": []}
        
        for doc in documents:
            if isinstance(doc.get('created_at'), str):
                doc['created_at'] = datetime.fromisoformat(doc['created_at'])
            
            # Apply professional content processing to ensure consistency
            # Process all content systematically to handle both old and new documents
            if 'exercises' in doc:
                for exercise in doc['exercises']:
                    if 'enonce' in exercise and exercise['enonce']:
                        exercise['enonce'] = process_exercise_content(exercise['enonce'])
                    
                    # schema_img is now generated during exercise creation, no need to process again
                    if exercise.get('schema_img'):
                        logger.debug(
                            "Schema image already present from generation",
                            module_name="documents",
                            func_name="check_schemas",
                            doc_id=str(doc.get('id', 'unknown'))[:8],
                            has_schema_img=bool(exercise.get('schema_img'))
                        )

                    # Process solution if it exists
                    if exercise.get('solution'):
                        if exercise['solution'].get('resultat'):
                            exercise['solution']['resultat'] = process_exercise_content(exercise['solution']['resultat'])
                                
                        if exercise['solution'].get('etapes') and isinstance(exercise['solution']['etapes'], list):
                            exercise['solution']['etapes'] = [
                                process_exercise_content(step) for step in exercise['solution']['etapes']
                            ]
        
        # Clean up MongoDB-specific fields that can't be JSON serialized
        for doc in documents:
            # Remove MongoDB ObjectId fields that cause serialization issues
            if '_id' in doc:
                del doc['_id']
        
        # Return raw documents to preserve dynamic fields like schema_img
        # Don't use Pydantic models here as they filter out dynamic fields
        return {"documents": documents}
        
    except Exception as e:
        logger.error(f"Error getting documents: {e}")
        return {"documents": []}

@api_router.post("/documents/{document_id}/vary/{exercise_index}")
async def vary_exercise(document_id: str, exercise_index: int):
    """Generate a variation of a specific exercise"""
    try:
        # Find the document
        doc = await db.documents.find_one({"id": document_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Document non trouvé")
        
        if exercise_index >= len(doc.get("exercises", [])):
            raise HTTPException(status_code=400, detail="Index d'exercice invalide")
        
        # Generate a new variation
        exercises = await generate_exercises_with_ai(
            doc["matiere"],
            doc["niveau"],
            doc["chapitre"],
            doc["type_doc"],
            doc["difficulte"],
            1  # Just one exercise
        )
        
        if exercises:
            # Update the specific exercise
            # Convert Exercise object to dict for MongoDB storage
            exercise_dict = exercises[0].dict() if hasattr(exercises[0], 'dict') else exercises[0]
            doc["exercises"][exercise_index] = exercise_dict
            await db.documents.update_one(
                {"id": document_id},
                {"$set": {"exercises": doc["exercises"]}}
            )
            
            # Return the exercise as dict for JSON serialization
            return {"exercise": exercise_dict}
        
        raise HTTPException(status_code=500, detail="Impossible de générer une variation")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error varying exercise: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la génération de la variation")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()