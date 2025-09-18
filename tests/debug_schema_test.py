#!/usr/bin/env python3
"""
Tests de débogage pour les schémas géométriques
Génère des snapshots SVG/PNG, calcule MD5 et tailles, teste PDF minimal
"""

import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path
from PIL import Image
from io import BytesIO
import cairosvg
import tempfile
import weasyprint

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from render_schema import schema_renderer
from logger import get_logger

logger = get_logger()

class SchemaDebugTester:
    """Testeur de débogage pour les schémas géométriques"""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent / "schema_snapshots"
        self.test_dir.mkdir(exist_ok=True)
        self.results = []
    
    def get_test_schemas(self):
        """Retourne 10 schémas de test variés"""
        return [
            {
                "name": "triangle_simple",
                "schema": {
                    "type": "triangle",
                    "points": ["A", "B", "C"],
                    "labels": {"A": "(0,3)", "B": "(0,0)", "C": "(4,0)"},
                    "segments": [["A", "B", {"longueur": 3}], ["B", "C", {"longueur": 4}]]
                }
            },
            {
                "name": "triangle_rectangle",
                "schema": {
                    "type": "triangle_rectangle",
                    "points": ["A", "B", "C"],
                    "labels": {"A": "(0,4)", "B": "(0,0)", "C": "(3,0)"},
                    "angles": [["B", {"angle_droit": True}]],
                    "segments": [["A", "B", {"longueur": 4}], ["B", "C", {"longueur": 3}]],
                    "hauteurs": [["A", "B", "C"]]
                }
            },
            {
                "name": "rectangle",
                "schema": {
                    "type": "rectangle",
                    "longueur": 6,
                    "largeur": 4,
                    "paralleles": [[["A", "B"], ["D", "C"]], [["A", "D"], ["B", "C"]]]
                }
            },
            {
                "name": "carre",
                "schema": {
                    "type": "carre",
                    "cote": 4,
                    "egaux": [[["A", "B"], ["B", "C"], ["C", "D"], ["D", "A"]]]
                }
            },
            {
                "name": "cercle",
                "schema": {
                    "type": "cercle",
                    "rayon": 3,
                    "show_diameter": True
                }
            },
            {
                "name": "losange",
                "schema": {
                    "type": "losange",
                    "cote": 4,
                    "angle": 60,
                    "egaux": [[["A", "B"], ["B", "C"], ["C", "D"], ["D", "A"]]]
                }
            },
            {
                "name": "parallelogramme",
                "schema": {
                    "type": "parallelogramme",
                    "base": 5,
                    "cote": 3,
                    "angle": 60,
                    "paralleles": [[["A", "B"], ["D", "C"]], [["A", "D"], ["B", "C"]]]
                }
            },
            {
                "name": "trapeze_rectangle",
                "schema": {
                    "type": "trapeze_rectangle",
                    "base_grande": 6,
                    "base_petite": 4,
                    "hauteur": 3,
                    "paralleles": [[["A", "B"], ["D", "C"]]],
                    "perpendiculaires": [[["A", "D"], ["A", "B"]]]
                }
            },
            {
                "name": "triangle_avec_medianes",
                "schema": {
                    "type": "triangle",
                    "points": ["A", "B", "C", "M", "N", "P"],
                    "labels": {"A": "(0,4)", "B": "(-2,0)", "C": "(2,0)"},
                    "medianes": [["A", "B", "C"], ["B", "A", "C"], ["C", "A", "B"]],
                    "segments": [["A", "B", {"longueur": 4.47}], ["B", "C", {"longueur": 4}], ["A", "C", {"longueur": 4.47}]]
                }
            },
            {
                "name": "schema_invalide",
                "schema": {
                    "type": "triangle",
                    "points": ["A"],  # Pas assez de points
                    "labels": {"A": "invalid_coord"},  # Coordonnées invalides
                    "segments": [["A", "B", {"longueur": 5}]]  # Point B n'existe pas
                }
            }
        ]
    
    def calculate_md5(self, content: bytes) -> str:
        """Calcule le MD5 d'un contenu"""
        return hashlib.md5(content).hexdigest()
    
    def svg_to_png(self, svg_content: str, output_path: Path) -> tuple[int, str]:
        """Convertit SVG en PNG et retourne (taille, md5)"""
        try:
            png_data = cairosvg.svg2png(bytestring=svg_content.encode('utf-8'))
            
            with open(output_path, 'wb') as f:
                f.write(png_data)
            
            size = len(png_data)
            md5_hash = self.calculate_md5(png_data)
            
            return size, md5_hash
        except Exception as e:
            logger.error(f"Erreur conversion SVG→PNG: {e}")
            return 0, "error"
    
    def test_schema_rendering(self, test_case: dict) -> dict:
        """Teste le rendu d'un schéma et génère les snapshots"""
        name = test_case["name"]
        schema = test_case["schema"]
        
        result = {
            "name": name,
            "schema_type": schema.get("type", "unknown"),
            "success": False,
            "svg_generated": False,
            "png_generated": False,
            "png_base64_generated": False,
            "svg_size": 0,
            "png_size": 0,
            "png_base64_size": 0,
            "svg_md5": "",
            "png_md5": "",
            "png_base64_md5": "",
            "validation_issues": [],
            "error": None
        }
        
        try:
            # Tester la validation du schéma
            is_valid, issues = schema_renderer.validate_schema(schema)
            result["validation_issues"] = issues
            
            # Générer le SVG (même si invalide pour tester le fallback)
            svg_content = schema_renderer.render_to_svg(schema)
            
            if svg_content:
                result["svg_generated"] = True
                
                # Sauvegarder le SVG
                svg_path = self.test_dir / f"{name}.svg"
                with open(svg_path, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
                
                result["svg_size"] = len(svg_content.encode('utf-8'))
                result["svg_md5"] = self.calculate_md5(svg_content.encode('utf-8'))
                
                # Convertir SVG en PNG via CairoSVG
                png_path = self.test_dir / f"{name}.png"
                png_size, png_md5 = self.svg_to_png(svg_content, png_path)
                
                if png_size > 0:
                    result["png_generated"] = True
                    result["png_size"] = png_size
                    result["png_md5"] = png_md5
            
            # TEST NOUVEAU: Générer PNG base64 directement
            png_base64 = schema_renderer.render_geometry_to_base64(schema)
            
            if png_base64:
                result["png_base64_generated"] = True
                
                # Sauvegarder le base64 pour inspection
                base64_path = self.test_dir / f"{name}_base64.txt"
                with open(base64_path, 'w', encoding='utf-8') as f:
                    f.write(png_base64)
                
                result["png_base64_size"] = len(png_base64)
                result["png_base64_md5"] = self.calculate_md5(png_base64.encode('utf-8'))
                
                result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Erreur lors du test {name}: {e}")
        
        return result
    
    def test_minimal_pdf(self) -> dict:
        """Teste la génération PDF minimale avec schémas"""
        result = {
            "success": False,
            "pdf_size": 0,
            "pdf_md5": "",
            "error": None
        }
        
        try:
            # Créer un document HTML minimal avec schémas
            triangle_svg = schema_renderer.render_to_svg({
                "type": "triangle",
                "points": ["A", "B", "C"],
                "labels": {"A": "(0,3)", "B": "(0,0)", "C": "(4,0)"}
            })
            
            rectangle_svg = schema_renderer.render_to_svg({
                "type": "rectangle",
                "longueur": 5,
                "largeur": 3
            })
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Test PDF Schémas</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .schema {{ margin: 20px 0; text-align: center; }}
                    .schema svg {{ border: 1px solid #ccc; }}
                </style>
            </head>
            <body>
                <h1>Test PDF avec Schémas Géométriques</h1>
                
                <h2>Triangle</h2>
                <div class="schema">
                    {triangle_svg}
                </div>
                
                <h2>Rectangle</h2>
                <div class="schema">
                    {rectangle_svg}
                </div>
                
                <p>PDF généré automatiquement par le système de test de schémas.</p>
            </body>
            </html>
            """
            
            # Générer le PDF
            pdf_path = self.test_dir / "test_schemas.pdf"
            pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
            
            with open(pdf_path, 'wb') as f:
                f.write(pdf_bytes)
            
            result["success"] = True
            result["pdf_size"] = len(pdf_bytes)
            result["pdf_md5"] = self.calculate_md5(pdf_bytes)
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Erreur génération PDF: {e}")
        
        return result
    
    def generate_report(self) -> str:
        """Génère un rapport de test détaillé"""
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r["success"])
        svg_generated = sum(1 for r in self.results if r["svg_generated"])
        png_generated = sum(1 for r in self.results if r["png_generated"])
        png_base64_generated = sum(1 for r in self.results if r["png_base64_generated"])
        
        report = [
            "=" * 60,
            "RAPPORT DE TEST - SCHÉMAS GÉOMÉTRIQUES",
            "=" * 60,
            f"Total des tests: {total_tests}",
            f"Tests réussis: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)",
            f"SVG générés: {svg_generated}/{total_tests}",
            f"PNG générés: {png_generated}/{total_tests}",
            f"PNG Base64 générés: {png_base64_generated}/{total_tests}",
            "",
            "DÉTAILS PAR TEST:",
            "-" * 40
        ]
        
        for result in self.results:
            status = "✅ RÉUSSI" if result["success"] else "❌ ÉCHEC"
            report.append(f"{result['name']:25} {status}")
            report.append(f"  Type: {result['schema_type']}")
            
            if result["svg_generated"]:
                report.append(f"  SVG: {result['svg_size']:,} bytes, MD5: {result['svg_md5'][:8]}...")
            
            if result["png_generated"]:
                report.append(f"  PNG: {result['png_size']:,} bytes, MD5: {result['png_md5'][:8]}...")
            
            if result["validation_issues"]:
                report.append(f"  Validation: {len(result['validation_issues'])} problème(s)")
                for issue in result["validation_issues"][:2]:  # Limiter à 2 pour la lisibilité
                    report.append(f"    - {issue}")
            
            if result["error"]:
                report.append(f"  Erreur: {result['error']}")
            
            report.append("")
        
        return "\n".join(report)
    
    def save_results_json(self):
        """Sauvegarde les résultats en JSON"""
        json_path = self.test_dir / "test_results.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": __import__('datetime').datetime.now().isoformat(),
                "total_tests": len(self.results),
                "successful_tests": sum(1 for r in self.results if r["success"]),
                "results": self.results
            }, f, indent=2, ensure_ascii=False)
    
    async def run_all_tests(self):
        """Lance tous les tests"""
        print("🔬 Démarrage des tests de schémas géométriques...")
        print(f"📁 Répertoire de sortie: {self.test_dir}")
        
        # Tester les 10 schémas
        test_schemas = self.get_test_schemas()
        for i, test_case in enumerate(test_schemas, 1):
            print(f"⚗️  Test {i}/10: {test_case['name']}")
            result = self.test_schema_rendering(test_case)
            self.results.append(result)
        
        # Test PDF minimal
        print("📄 Test PDF minimal...")
        pdf_result = self.test_minimal_pdf()
        
        # Générer le rapport
        report = self.generate_report()
        
        # Ajouter les résultats PDF au rapport
        if pdf_result["success"]:
            report += f"\n\nTEST PDF MINIMAL: ✅ RÉUSSI\n"
            report += f"Taille PDF: {pdf_result['pdf_size']:,} bytes\n"
            report += f"MD5 PDF: {pdf_result['pdf_md5']}\n"
        else:
            report += f"\n\nTEST PDF MINIMAL: ❌ ÉCHEC\n"
            report += f"Erreur: {pdf_result['error']}\n"
        
        # Sauvegarder le rapport
        report_path = self.test_dir / "test_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Sauvegarder les résultats JSON
        self.save_results_json()
        
        print(report)
        print(f"\n📊 Rapport sauvegardé: {report_path}")
        print(f"📈 Résultats JSON: {self.test_dir / 'test_results.json'}")
        print(f"🖼️  Snapshots: {len([f for f in self.test_dir.glob('*.svg')])} SVG, {len([f for f in self.test_dir.glob('*.png')])} PNG")

def main():
    """Point d'entrée principal"""
    try:
        tester = SchemaDebugTester()
        asyncio.run(tester.run_all_tests())
        return 0
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())