from fastapi import FastAPI, APIRouter, HTTPException, Response, Depends, BackgroundTasks, Request
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
import tempfile
import weasyprint
from jinja2 import Template
import requests

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

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
    }
}

# PDF Templates
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

SUJET_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ document.type_doc|title }} - {{ document.matiere }} {{ document.niveau }}</title>
    <style>
        @page {
            size: A4;
            margin: 2cm 1.5cm 2cm 1.5cm;
            @top-center {
                content: "{{ document.matiere }} - {{ document.niveau }} - {{ document.chapitre }}";
                font-family: 'Arial', sans-serif;
                font-size: 10pt;
                color: #666;
            }
            @bottom-center {
                content: "Page " counter(page) " / " counter(pages);
                font-family: 'Arial', sans-serif;
                font-size: 10pt;
                color: #666;
            }
        }
        
        body {
            font-family: 'Arial', sans-serif;
            font-size: 11pt;
            line-height: 1.4;
            color: #333;
        }
        
        .header {
            text-align: center;
            border-bottom: 2px solid #333;
            padding-bottom: 1cm;
            margin-bottom: 1.5cm;
        }
        
        .title {
            font-size: 18pt;
            font-weight: bold;
            margin-bottom: 0.5cm;
        }
        
        .subtitle {
            font-size: 14pt;
            color: #666;
            margin-bottom: 0.3cm;
        }
        
        .info-line {
            font-size: 10pt;
            color: #888;
        }
        
        .exercise {
            margin-bottom: 2cm;
            page-break-inside: avoid;
        }
        
        .exercise-header {
            font-weight: bold;
            font-size: 12pt;
            margin-bottom: 0.5cm;
            padding: 0.3cm;
            background-color: #f5f5f5;
            border-left: 4px solid #333;
        }
        
        .exercise-content {
            margin-left: 0.5cm;
            margin-bottom: 1cm;
        }
        
        .exercise-text {
            text-align: justify;
            margin-bottom: 1cm;
        }
        
        .answer-space {
            border: 1px solid #ddd;
            min-height: 3cm;
            margin-top: 0.5cm;
            background-color: #fafafa;
        }
        
        .answer-lines {
            height: 2.5cm;
            background-image: repeating-linear-gradient(
                transparent,
                transparent 0.6cm,
                #ddd 0.6cm,
                #ddd 0.62cm
            );
        }
        
        .difficulty-badge {
            display: inline-block;
            padding: 0.1cm 0.3cm;
            font-size: 9pt;
            background-color: #e8f4f8;
            border: 1px solid #bee5eb;
            border-radius: 0.2cm;
            margin-left: 0.5cm;
        }
        
        .points {
            float: right;
            font-size: 10pt;
            color: #666;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="title">{{ document.type_doc|title }}</div>
        <div class="subtitle">{{ document.matiere }} - {{ document.niveau }}</div>
        <div class="subtitle">{{ document.chapitre }}</div>
        <div class="info-line">
            Difficulté: {{ document.difficulte|title }} | 
            {{ document.nb_exercices }} exercices | 
            Généré le {{ date_creation }}
        </div>
    </div>
    
    {% for exercise in document.exercises %}
    <div class="exercise">
        <div class="exercise-header">
            Exercice {{ loop.index }}
            <span class="difficulty-badge">{{ exercise.difficulte }}</span>
            <span class="points">
                {% set total_points = exercise.bareme|sum(attribute='points') %}
                ({{ "%.1f"|format(total_points) }} pts)
            </span>
        </div>
        <div class="exercise-content">
            <div class="exercise-text">{{ exercise.enonce }}</div>
            <div class="answer-space">
                <div class="answer-lines"></div>
            </div>
        </div>
    </div>
    {% endfor %}
</body>
</html>
"""

CORRIGE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Corrigé - {{ document.type_doc|title }} - {{ document.matiere }} {{ document.niveau }}</title>
    <style>
        @page {
            size: A4;
            margin: 2cm 1.5cm 2cm 1.5cm;
            @top-center {
                content: "CORRIGÉ - {{ document.matiere }} - {{ document.niveau }} - {{ document.chapitre }}";
                font-family: 'Arial', sans-serif;
                font-size: 10pt;
                color: #666;
            }
            @bottom-center {
                content: "Page " counter(page) " / " counter(pages);
                font-family: 'Arial', sans-serif;
                font-size: 10pt;
                color: #666;
            }
        }
        
        body {
            font-family: 'Arial', sans-serif;
            font-size: 11pt;
            line-height: 1.4;
            color: #333;
        }
        
        .header {
            text-align: center;
            border-bottom: 2px solid #d32f2f;
            padding-bottom: 1cm;
            margin-bottom: 1.5cm;
        }
        
        .title {
            font-size: 18pt;
            font-weight: bold;
            margin-bottom: 0.5cm;
            color: #d32f2f;
        }
        
        .subtitle {
            font-size: 14pt;
            color: #666;
            margin-bottom: 0.3cm;
        }
        
        .info-line {
            font-size: 10pt;
            color: #888;
        }
        
        .exercise {
            margin-bottom: 2cm;
            page-break-inside: avoid;
        }
        
        .exercise-header {
            font-weight: bold;
            font-size: 12pt;
            margin-bottom: 0.5cm;
            padding: 0.3cm;
            background-color: #ffebee;
            border-left: 4px solid #d32f2f;
        }
        
        .exercise-content {
            margin-left: 0.5cm;
            margin-bottom: 1cm;
        }
        
        .exercise-text {
            text-align: justify;
            margin-bottom: 1cm;
            font-style: italic;
            color: #555;
        }
        
        .solution {
            background-color: #f8f9fa;
            padding: 0.5cm;
            border-radius: 0.3cm;
            border-left: 4px solid #28a745;
        }
        
        .solution-title {
            font-weight: bold;
            color: #28a745;
            margin-bottom: 0.5cm;
        }
        
        .step {
            margin-bottom: 0.3cm;
            padding-left: 0.5cm;
        }
        
        .step-number {
            font-weight: bold;
            color: #28a745;
        }
        
        .final-result {
            background-color: #d4edda;
            padding: 0.3cm;
            margin-top: 0.5cm;
            border-radius: 0.2cm;
            font-weight: bold;
        }
        
        .bareme {
            margin-top: 1cm;
            padding: 0.5cm;
            background-color: #e3f2fd;
            border-radius: 0.3cm;
        }
        
        .bareme-title {
            font-weight: bold;
            color: #1976d2;
            margin-bottom: 0.3cm;
        }
        
        .bareme-item {
            font-size: 10pt;
            margin-bottom: 0.1cm;
        }
        
        .points {
            float: right;
            font-size: 10pt;
            color: #666;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="title">CORRIGÉ - {{ document.type_doc|title }}</div>
        <div class="subtitle">{{ document.matiere }} - {{ document.niveau }}</div>
        <div class="subtitle">{{ document.chapitre }}</div>
        <div class="info-line">
            Difficulté: {{ document.difficulte|title }} | 
            {{ document.nb_exercices }} exercices | 
            Généré le {{ date_creation }}
        </div>
    </div>
    
    {% for exercise in document.exercises %}
    <div class="exercise">
        <div class="exercise-header">
            Exercice {{ loop.index }} - Solution
            <span class="points">
                {% set total_points = exercise.bareme|sum(attribute='points') %}
                ({{ "%.1f"|format(total_points) }} pts)
            </span>
        </div>
        <div class="exercise-content">
            <div class="exercise-text">{{ exercise.enonce }}</div>
            
            <div class="solution">
                <div class="solution-title">Solution détaillée :</div>
                {% for etape in exercise.solution.etapes %}
                <div class="step">
                    <span class="step-number">{{ loop.index }}.</span> {{ etape }}
                </div>
                {% endfor %}
                
                <div class="final-result">
                    Résultat final : {{ exercise.solution.resultat }}
                </div>
            </div>
            
            {% if exercise.bareme %}
            <div class="bareme">
                <div class="bareme-title">Barème de notation :</div>
                {% for item in exercise.bareme %}
                <div class="bareme-item">
                    • {{ item.etape }} : {{ item.points }} pt(s)
                </div>
                {% endfor %}
            </div>
            {% endif %}
        </div>
    </div>
    {% endfor %}
</body>
</html>
"""

# Helper functions
async def check_guest_quota(guest_id: str):
    """Check if guest user can export (3 exports max)"""
    try:
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        export_count = await db.exports.count_documents({
            "guest_id": guest_id,
            "created_at": {"$gte": thirty_days_ago}
        })
        
        remaining = max(0, 3 - export_count)
        
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
        frontend_url = os.environ.get('FRONTEND_URL', 'https://edudocsai.preview.emergentagent.com')
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

async def generate_exercises_with_ai(matiere: str, niveau: str, chapitre: str, type_doc: str, difficulte: str, nb_exercices: int) -> List[Exercise]:
    """Generate exercises using AI"""
    
    # Level-specific guidance
    niveau_guidance = {
        "6e": "Niveau débutant - vocabulaire simple, calculs basiques, exemples concrets du quotidien",
        "5e": "Niveau intermédiaire - introduction de concepts plus abstraits mais restant accessibles", 
        "4e": "Niveau confirmé - calculs plus complexes, raisonnement mathématique développé",
        "3e": "Niveau avancé - préparation au lycée, concepts abstraits, démonstrations"
    }
    
    # Chapter-specific examples
    chapter_examples = {
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
        }
    }
    
    # Get specific guidance
    level_guide = niveau_guidance.get(niveau, "Adapter au niveau demandé")
    chapter_guide = chapter_examples.get(chapitre, {}).get(niveau, "Respecter le programme officiel")
    
    # Create LLM chat instance with faster model
    chat = LlmChat(
        api_key=emergent_key,
        session_id=f"exercise_gen_{uuid.uuid4()}",
        system_message=f"""Tu es un générateur d'exercices scolaires français pour {niveau} - {chapitre}.

Génère {nb_exercices} exercices RAPIDES ET EFFICACES.

RÈGLES:
1. Niveau {niveau} - Chapitre "{chapitre}"
2. {level_guide}
3. Format français correct (virgules décimaux)
4. Solutions en 2-3 étapes maximum

JSON OBLIGATOIRE:
{{
  "exercises": [
    {{
      "type": "ouvert",
      "enonce": "Énoncé concis",
      "difficulte": "{difficulte}",
      "solution": {{
        "etapes": ["Étape 1", "Étape 2"],
        "resultat": "Résultat"
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
        "Volumes": "Calculer volume pavé 4×3×2 cm",
        "Nombres relatifs": "Calculer -5 + 3 - (-2)",
        "Fractions": "Calculer 2/3 + 1/4"
    }
    
    example = examples.get(chapitre, f"Exercice {chapitre}")
    
    prompt = f"""
{matiere} {niveau} - {chapitre}
Génère {nb_exercices} exercices {difficulte}

Exemple: {example}

JSON uniquement:
"""
    
    try:
        user_message = UserMessage(text=prompt)
        
        # Set shorter timeout for faster response
        import asyncio
        response = await asyncio.wait_for(
            chat.send_message(user_message), 
            timeout=20.0  # 20 seconds max
        )
        
        # Parse the JSON response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON found in response")
            
        json_content = response[json_start:json_end]
        data = json.loads(json_content)
        
        # Convert to Exercise objects
        exercises = []
        for ex_data in data.get("exercises", []):
            # Clean the enonce to remove any unwanted formatting
            enonce = ex_data.get("enonce", "").strip()
            
            exercise = Exercise(
                type=ex_data.get("type", "ouvert"),
                enonce=enonce,
                donnees=None,  # Don't show technical data to users
                difficulte=ex_data.get("difficulte", difficulte),
                solution=ex_data.get("solution", {"etapes": ["Étape 1", "Étape 2"], "resultat": "Résultat"}),
                bareme=ex_data.get("bareme", [{"etape": "Méthode", "points": 2.0}, {"etape": "Résultat", "points": 2.0}]),
                seed=hash(enonce) % 1000000
            )
            exercises.append(exercise)
        
        if not exercises:
            raise ValueError("No exercises generated")
            
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
    
    # Quick templates based on chapter
    templates = {
        "Nombres relatifs": [
            "Calculer : {a} + {b} - ({c})",
            "Déterminer le signe de : {a} × {b}",
            "Résoudre : x + {a} = {b}"
        ],
        "Volumes": [
            "Calculer le volume d'un pavé de dimensions {a} cm × {b} cm × {c} cm",
            "Une boîte cubique a une arête de {a} cm. Quel est son volume ?",
            "Convertir {a} L en cm³"
        ],
        "Fractions": [
            "Calculer : 1/{a} + 1/{b}",
            "Simplifier : {a}/{b}",
            "Comparer : 1/{a} et 1/{b}"
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
        
        exercise = Exercise(
            type="ouvert",
            enonce=enonce,
            donnees=None,
            difficulte=difficulte,
            solution={
                "etapes": ["Appliquer la méthode du cours", "Effectuer les calculs"],
                "resultat": "Résultat à calculer"
            },
            bareme=[
                {"etape": "Méthode", "points": 2.0},
                {"etape": "Calcul", "points": 2.0}
            ],
            seed=random.randint(1000, 9999)
        )
        exercises.append(exercise)
    
    return exercises

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

@api_router.get("/quota/check")
async def check_quota_status(guest_id: str):
    """Check current quota status for guest user"""
    return await check_guest_quota(guest_id)
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

@api_router.post("/export")
async def export_pdf(request: ExportRequest, http_request: Request):
    """Export document as PDF"""
    try:
        # Check authentication - ONLY session token method (no legacy email fallback)
        session_token = http_request.headers.get("X-Session-Token")
        is_pro_user = False
        user_email = None
        
        # Authenticate using session token only
        if session_token:
            email = await validate_session_token(session_token)
            if email:
                is_pro, user = await check_user_pro_status(email)
                is_pro_user = is_pro
                user_email = email
                logger.info(f"Export request from Pro user via session: {email}, is_pro: {is_pro}")
            else:
                logger.info("Invalid session token provided")
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
        
        # Convert to Document object
        if isinstance(doc.get('created_at'), str):
            doc['created_at'] = datetime.fromisoformat(doc['created_at'])
        document = Document(**doc)
        
        # Select template
        template_content = SUJET_TEMPLATE if request.export_type == "sujet" else CORRIGE_TEMPLATE
        template = Template(template_content)
        
        # Render HTML
        html_content = template.render(
            document=document,
            date_creation=document.created_at.strftime("%d/%m/%Y à %H:%M")
        )
        
        # Generate PDF
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
        
        # Track export for guest quota (only for non-Pro users)
        if not is_pro_user and request.guest_id:
            export_record = {
                "id": str(uuid.uuid4()),
                "document_id": request.document_id,
                "export_type": request.export_type,
                "guest_id": request.guest_id,
                "user_email": user_email,
                "is_pro": is_pro_user,
                "created_at": datetime.now(timezone.utc)
            }
            await db.exports.insert_one(export_record)
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.write(pdf_bytes)
        temp_file.close()
        
        # Generate filename
        filename = f"LeMaitremot_{document.type_doc}_{document.matiere}_{document.niveau}_{request.export_type}.pdf"
        
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
async def get_documents(guest_id: str = None):
    """Get user documents"""
    try:
        if guest_id:
            # Get documents for guest user
            documents = await db.documents.find({"guest_id": guest_id}).sort("created_at", -1).limit(20).to_list(length=20)
        else:
            return {"documents": []}
        
        for doc in documents:
            if isinstance(doc.get('created_at'), str):
                doc['created_at'] = datetime.fromisoformat(doc['created_at'])
        
        return {"documents": [Document(**doc) for doc in documents]}
        
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
            doc["exercises"][exercise_index] = exercises[0].dict()
            await db.documents.update_one(
                {"id": document_id},
                {"$set": {"exercises": doc["exercises"]}}
            )
            
            return {"exercise": exercises[0]}
        
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