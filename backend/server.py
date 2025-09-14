from fastapi import FastAPI, APIRouter, HTTPException, Response, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from emergentintegrations.llm.chat import LlmChat, UserMessage
import json
import tempfile
import weasyprint
from jinja2 import Template
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

# Security
security = HTTPBearer(auto_error=False)

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
    user_id: Optional[str] = None  # For registered users
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

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    nom: Optional[str] = None
    etablissement: Optional[str] = None
    account_type: str = "free"  # "free", "pro"
    exports_used: int = 0
    max_exports: int = 50  # Free tier limit
    magic_token: Optional[str] = None
    token_expires: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None

class GenerateRequest(BaseModel):
    matiere: str
    niveau: str
    chapitre: str
    type_doc: str
    difficulte: str = "moyen"
    nb_exercices: int = 6
    versions: List[str] = ["A"]
    guest_id: Optional[str] = None

class AuthRequest(BaseModel):
    email: EmailStr
    nom: Optional[str] = None
    etablissement: Optional[str] = None

class ExportRequest(BaseModel):
    document_id: str
    export_type: str  # "sujet" or "corrige"
    guest_id: Optional[str] = None

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
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token"""
    if not credentials:
        return None
    
    try:
        # Simple token validation - in production use proper JWT
        user = await db.users.find_one({"magic_token": credentials.credentials})
        if user and user.get("token_expires") and user["token_expires"] > datetime.now(timezone.utc):
            return User(**user)
    except:
        pass
    return None

async def check_export_quota(user_id: str = None, guest_id: str = None):
    """Check if user can export (quota management)"""
    if user_id:
        user = await db.users.find_one({"id": user_id})
        if user:
            if user.get("account_type") == "pro":
                return True, "unlimited"
            elif user.get("exports_used", 0) < user.get("max_exports", 50):
                return True, f"remaining: {user.get('max_exports', 50) - user.get('exports_used', 0)}"
            else:
                return False, "quota_exceeded"
    else:
        # Guest mode - check exports in last 30 days
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        export_count = await db.exports.count_documents({
            "guest_id": guest_id,
            "created_at": {"$gte": thirty_days_ago}
        })
        if export_count < 3:
            return True, f"guest_remaining: {3 - export_count}"
        else:
            return False, "guest_quota_exceeded"
    
    return False, "no_access"

async def send_magic_link(email: str, token: str):
    """Send magic link email (development version)"""
    # For development/testing - store magic link in a simple way
    magic_link = f"https://lessonsmith.preview.emergentagent.com/auth/verify?token={token}"
    
    print(f"🔗 Magic link for {email}: {magic_link}")
    
    # Store in database for easy retrieval during testing
    magic_link_record = {
        "email": email,
        "token": token,
        "magic_link": magic_link,
        "created_at": datetime.now(timezone.utc),
        "used": False
    }
    await db.magic_links.insert_one(magic_link_record)
    
    return True

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
    return {"message": "API LessonSmith V1 - Générateur de documents pédagogiques"}

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

@api_router.post("/export")
async def export_pdf(request: ExportRequest):
    """Export document as PDF"""
    try:
        # Check quota first
        can_export, quota_info = await check_export_quota(guest_id=request.guest_id)
        
        if not can_export:
            if quota_info == "guest_quota_exceeded":
                raise HTTPException(status_code=402, detail={
                    "error": "quota_exceeded", 
                    "message": "Limite de 3 exports gratuits atteinte. Créez un compte pour continuer.",
                    "action": "signup_required"
                })
            else:
                raise HTTPException(status_code=402, detail="Quota d'exports dépassé")
        
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
        
        # Track export
        export_record = {
            "id": str(uuid.uuid4()),
            "document_id": request.document_id,
            "export_type": request.export_type,
            "guest_id": request.guest_id,
            "created_at": datetime.now(timezone.utc)
        }
        await db.exports.insert_one(export_record)
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.write(pdf_bytes)
        temp_file.close()
        
        # Generate filename
        filename = f"{document.type_doc}_{document.matiere}_{document.niveau}_{request.export_type}.pdf"
        
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

@api_router.get("/quota/check")
async def check_quota_status(guest_id: str):
    """Check current quota status for guest user"""
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
        logger.error(f"Error checking quota: {e}")
        return {
            "exports_used": 0,
            "exports_remaining": 3,
            "max_exports": 3,
            "quota_exceeded": False
        }

@api_router.post("/quota/reset")
async def reset_quota_for_testing(guest_id: str):
    """Reset quota for testing purposes (development only)"""
    try:
        # Delete all exports for this guest
        result = await db.exports.delete_many({"guest_id": guest_id})
        
        return {
            "message": f"Quota réinitialisé pour {guest_id}",
            "deleted_exports": result.deleted_count,
            "new_quota": {
                "exports_used": 0,
                "exports_remaining": 3,
                "max_exports": 3,
                "quota_exceeded": False
            }
        }
        
    except Exception as e:
        logger.error(f"Error resetting quota: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la réinitialisation")

@api_router.post("/auth/signup")
async def signup_request(request: AuthRequest):
    """Request signup with magic link"""
    try:
        # Check if user already exists
        existing_user = await db.users.find_one({"email": request.email})
        if existing_user:
            # User exists, send login link
            magic_token = str(uuid.uuid4())
            token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
            
            await db.users.update_one(
                {"email": request.email},
                {"$set": {
                    "magic_token": magic_token,
                    "token_expires": token_expires
                }}
            )
        else:
            # Create new user
            magic_token = str(uuid.uuid4())
            token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
            
            user = User(
                email=request.email,
                nom=request.nom,
                etablissement=request.etablissement,
                magic_token=magic_token,
                token_expires=token_expires
            )
            
            await db.users.insert_one(user.dict())
        
        # Send magic link (in production, send real email)
        await send_magic_link(request.email, magic_token)
        
        return {
            "message": "Un lien de connexion a été envoyé à votre adresse email",
            "email": request.email
        }
        
    except Exception as e:
        logger.error(f"Error in signup: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'inscription")

@api_router.get("/auth/magic-links/{email}")
async def get_magic_link_for_testing(email: str):
    """Get magic link for testing purposes (development only)"""
    try:
        # Find the most recent magic link for this email
        magic_link = await db.magic_links.find_one(
            {"email": email, "used": False},
            sort=[("created_at", -1)]
        )
        
        if not magic_link:
            raise HTTPException(status_code=404, detail="Aucun lien magique trouvé pour cette adresse")
        
        return {
            "email": email,
            "magic_link": magic_link["magic_link"],
            "token": magic_link["token"],
            "created_at": magic_link["created_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting magic link: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du lien")

@api_router.get("/auth/verify")
async def verify_magic_link(token: str):
    """Verify magic link and return auth token"""
    try:
        user = await db.users.find_one({
            "magic_token": token,
            "token_expires": {"$gt": datetime.now(timezone.utc)}
        })
        
        if not user:
            raise HTTPException(status_code=400, detail="Lien invalide ou expiré")
        
        # Mark magic link as used
        await db.magic_links.update_one(
            {"token": token},
            {"$set": {"used": True}}
        )
        
        # Update last login
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {"last_login": datetime.now(timezone.utc)}}
        )
        
        return {
            "token": token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "nom": user.get("nom"),
                "account_type": user.get("account_type", "free")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la vérification")

@api_router.get("/documents")
async def get_documents(guest_id: str = None, current_user: User = Depends(get_current_user)):
    """Get user documents"""
    try:
        if current_user:
            # Get documents for registered user
            documents = await db.documents.find({"user_id": current_user.id}).sort("created_at", -1).limit(50).to_list(length=50)
        elif guest_id:
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