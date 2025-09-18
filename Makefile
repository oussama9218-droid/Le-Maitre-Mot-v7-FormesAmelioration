# Makefile pour Le Maître Mot - Tests et Développement

# Variables
PYTHON = python3
BACKEND_DIR = backend
FRONTEND_DIR = frontend
TESTS_DIR = tests
VENV_DIR = venv

# Couleurs pour les messages
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[1;33m
BLUE = \033[0;34m
NC = \033[0m # No Color

.PHONY: help install test test-schemas test-backend test-frontend lint clean setup dev-install

# Cible par défaut
help:
	@echo "$(BLUE)Le Maître Mot - Commandes disponibles:$(NC)"
	@echo ""
	@echo "$(GREEN)Installation:$(NC)"
	@echo "  make install       - Installer toutes les dépendances"
	@echo "  make dev-install   - Installation pour développement"
	@echo "  make setup         - Configuration initiale complète"
	@echo ""
	@echo "$(GREEN)Tests:$(NC)"
	@echo "  make test          - Lancer tous les tests"
	@echo "  make test-schemas  - Tests des schémas géométriques (snapshots SVG/PNG)"
	@echo "  make test-backend  - Tests backend uniquement"
	@echo "  make test-frontend - Tests frontend uniquement"
	@echo ""
	@echo "$(GREEN)Qualité du code:$(NC)"
	@echo "  make lint          - Vérification du code (Python + JS)"
	@echo "  make lint-python   - Linting Python uniquement"
	@echo "  make lint-js       - Linting JavaScript uniquement"
	@echo ""
	@echo "$(GREEN)Développement:$(NC)"
	@echo "  make dev           - Démarrer en mode développement"
	@echo "  make clean         - Nettoyer les fichiers temporaires"
	@echo "  make restart       - Redémarrer les services"

# Installation des dépendances
install:
	@echo "$(YELLOW)📦 Installation des dépendances...$(NC)"
	cd $(BACKEND_DIR) && pip install -r requirements.txt
	cd $(FRONTEND_DIR) && yarn install --frozen-lockfile
	@echo "$(GREEN)✅ Installation terminée$(NC)"

dev-install: install
	@echo "$(YELLOW)🔧 Installation des outils de développement...$(NC)"
	pip install pytest pytest-asyncio cairosvg pillow
	@echo "$(GREEN)✅ Installation dev terminée$(NC)"

setup: dev-install
	@echo "$(YELLOW)⚙️  Configuration initiale...$(NC)"
	mkdir -p $(TESTS_DIR)/schema_snapshots
	mkdir -p $(TESTS_DIR)/reports
	@echo "$(GREEN)✅ Configuration terminée$(NC)"

# Tests des schémas géométriques
test-schemas:
	@echo "$(BLUE)🔬 Tests des schémas géométriques$(NC)"
	@echo "$(YELLOW)Génération de 10 snapshots SVG/PNG avec MD5 et tailles...$(NC)"
	cd $(TESTS_DIR) && $(PYTHON) debug_schema_test.py
	@echo ""
	@echo "$(GREEN)📊 Résultats des tests de schémas:$(NC)"
	@if [ -f "$(TESTS_DIR)/schema_snapshots/test_report.txt" ]; then \
		tail -n 20 "$(TESTS_DIR)/schema_snapshots/test_report.txt"; \
	fi
	@echo ""
	@echo "$(BLUE)📁 Fichiers générés:$(NC)"
	@ls -la $(TESTS_DIR)/schema_snapshots/ | grep -E '\.(svg|png|pdf|json|txt)$$' || echo "Aucun fichier trouvé"

# Tests backend
test-backend:
	@echo "$(BLUE)🧪 Tests backend$(NC)"
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest ../$(TESTS_DIR)/ -v --tb=short

# Tests frontend
test-frontend:
	@echo "$(BLUE)🧪 Tests frontend$(NC)"
	cd $(FRONTEND_DIR) && yarn test --watchAll=false

# Tous les tests
test: test-backend test-frontend test-schemas
	@echo "$(GREEN)✅ Tous les tests terminés$(NC)"

# Linting
lint-python:
	@echo "$(YELLOW)🔍 Linting Python...$(NC)"
	cd $(BACKEND_DIR) && $(PYTHON) -m ruff check . --fix || true
	cd $(BACKEND_DIR) && $(PYTHON) -m ruff format . || true

lint-js:
	@echo "$(YELLOW)🔍 Linting JavaScript...$(NC)"
	cd $(FRONTEND_DIR) && yarn lint --fix || true

lint: lint-python lint-js
	@echo "$(GREEN)✅ Linting terminé$(NC)"

# Développement
dev:
	@echo "$(BLUE)🚀 Démarrage en mode développement$(NC)"
	@echo "Backend: http://localhost:8001"
	@echo "Frontend: http://localhost:3000"
	sudo supervisorctl start all

restart:
	@echo "$(YELLOW)🔄 Redémarrage des services...$(NC)"
	sudo supervisorctl restart all
	@echo "$(GREEN)✅ Services redémarrés$(NC)"

# Nettoyage
clean:
	@echo "$(YELLOW)🧹 Nettoyage...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -prune -o -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(TESTS_DIR)/schema_snapshots/*.svg 2>/dev/null || true
	rm -rf $(TESTS_DIR)/schema_snapshots/*.png 2>/dev/null || true
	rm -rf $(TESTS_DIR)/schema_snapshots/*.pdf 2>/dev/null || true
	@echo "$(GREEN)✅ Nettoyage terminé$(NC)"

# Tests de performance pour les schémas
perf-schemas:
	@echo "$(BLUE)⚡ Tests de performance des schémas$(NC)"
	@echo "$(YELLOW)Génération de 100 schémas pour mesurer les performances...$(NC)"
	cd $(TESTS_DIR) && time $(PYTHON) -c "
import sys
sys.path.insert(0, '../backend')
from render_schema import schema_renderer
import time

schemas = [
    {'type': 'triangle', 'points': ['A', 'B', 'C'], 'labels': {'A': '(0,3)', 'B': '(0,0)', 'C': '(4,0)'}},
    {'type': 'rectangle', 'longueur': 5, 'largeur': 3},
    {'type': 'cercle', 'rayon': 2}
] * 34  # 102 schémas au total

start = time.time()
for i, schema in enumerate(schemas):
    svg = schema_renderer.render_to_svg(schema)
    if i % 10 == 0:
        print(f'Schéma {i+1}/100 généré ({len(svg)} chars)')

end = time.time()
print(f'Performance: {len(schemas)} schémas en {end-start:.2f}s ({len(schemas)/(end-start):.1f} schémas/sec)')
"

# Validation des schémas de test
validate-schemas:
	@echo "$(BLUE)✅ Validation des schémas de test$(NC)"
	cd $(TESTS_DIR) && $(PYTHON) -c "
import sys
sys.path.insert(0, '../backend')
from render_schema import schema_renderer

test_schemas = [
    {'type': 'triangle', 'points': ['A', 'B', 'C'], 'labels': {'A': '(0,3)', 'B': '(0,0)', 'C': '(4,0)'}},
    {'type': 'rectangle', 'longueur': 5, 'largeur': 3},
    {'type': 'triangle', 'points': ['A']},  # Invalide
]

for i, schema in enumerate(test_schemas):
    is_valid, issues = schema_renderer.validate_schema(schema)
    status = '✅' if is_valid else '❌'
    print(f'{status} Schéma {i+1}: {schema.get(\"type\", \"unknown\")} - {\"Valide\" if is_valid else f\"{len(issues)} erreur(s)\"}')
    if issues:
        for issue in issues[:2]:
            print(f'  - {issue}')
"

# Statistiques du projet
stats:
	@echo "$(BLUE)📊 Statistiques du projet$(NC)"
	@echo ""
	@echo "$(YELLOW)Code Python:$(NC)"
	@find $(BACKEND_DIR) -name "*.py" | xargs wc -l | tail -1
	@echo "$(YELLOW)Code JavaScript:$(NC)"
	@find $(FRONTEND_DIR)/src -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" | xargs wc -l | tail -1
	@echo "$(YELLOW)Templates HTML:$(NC)"
	@find $(BACKEND_DIR)/templates -name "*.html" | xargs wc -l | tail -1
	@echo ""
	@echo "$(YELLOW)Schémas disponibles:$(NC)"
	@cd $(BACKEND_DIR) && $(PYTHON) -c "
import sys
sys.path.insert(0, '.')
from render_schema import schema_renderer
import inspect

methods = [m for m in dir(schema_renderer) if m.startswith('_render_') and callable(getattr(schema_renderer, m))]
print(f'Types de schémas supportés: {len(methods)}')
for method in sorted(methods):
    schema_type = method.replace('_render_', '')
    print(f'  - {schema_type}')
"

# Installation des dépendances manquantes pour les tests
install-test-deps:
	@echo "$(YELLOW)📦 Installation des dépendances de test...$(NC)"
	pip install pytest pytest-asyncio cairosvg pillow weasyprint
	@echo "$(GREEN)✅ Dépendances de test installées$(NC)"

# Aide étendue
help-extended: help
	@echo ""
	@echo "$(GREEN)Commandes avancées:$(NC)"
	@echo "  make perf-schemas     - Tests de performance des schémas"
	@echo "  make validate-schemas - Validation des schémas de test"
	@echo "  make stats           - Statistiques du projet"
	@echo "  make install-test-deps - Installer les dépendances de test"
	@echo ""
	@echo "$(BLUE)Exemples d'utilisation:$(NC)"
	@echo "  make test-schemas     # Générer 10 snapshots de test"
	@echo "  make clean test       # Nettoyer puis tester"
	@echo "  make lint test        # Vérifier le code puis tester"