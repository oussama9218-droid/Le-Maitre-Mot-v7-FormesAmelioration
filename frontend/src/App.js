import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./components/ui/select";
import { Badge } from "./components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { Separator } from "./components/ui/separator";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "./components/ui/dialog";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import { Alert, AlertDescription } from "./components/ui/alert";
import { BookOpen, FileText, Download, Shuffle, Loader2, GraduationCap, AlertCircle, CheckCircle, User, Mail } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [catalog, setCatalog] = useState([]);
  const [selectedMatiere, setSelectedMatiere] = useState("");
  const [selectedNiveau, setSelectedNiveau] = useState("");
  const [selectedChapitre, setSelectedChapitre] = useState("");
  const [typeDoc, setTypeDoc] = useState("exercices");
  const [difficulte, setDifficulte] = useState("moyen");
  const [nbExercices, setNbExercices] = useState(6);
  const [currentDocument, setCurrentDocument] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [documents, setDocuments] = useState([]);
  
  // Guest and quota management
  const [guestId, setGuestId] = useState("");
  const [quotaStatus, setQuotaStatus] = useState({ exports_remaining: 3, quota_exceeded: false });
  const [showSignupModal, setShowSignupModal] = useState(false);
  const [signupData, setSignupData] = useState({ email: "", nom: "", etablissement: "" });
  const [signupLoading, setSignupLoading] = useState(false);
  const [signupSuccess, setSignupSuccess] = useState(false);
  
  // Export states
  const [exportingSubject, setExportingSubject] = useState(false);
  const [exportingSolution, setExportingSolution] = useState(false);

  // Initialize guest ID
  useEffect(() => {
    let storedGuestId = localStorage.getItem('lessonsmith_guest_id');
    if (!storedGuestId) {
      storedGuestId = 'guest_' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('lessonsmith_guest_id', storedGuestId);
    }
    setGuestId(storedGuestId);
  }, []);

  const fetchCatalog = async () => {
    try {
      const response = await axios.get(`${API}/catalog`);
      setCatalog(response.data.catalog);
    } catch (error) {
      console.error("Erreur lors du chargement du catalogue:", error);
    }
  };

  const fetchQuotaStatus = async () => {
    if (!guestId) return;
    try {
      const response = await axios.get(`${API}/quota/check?guest_id=${guestId}`);
      setQuotaStatus(response.data);
    } catch (error) {
      console.error("Erreur lors du chargement du quota:", error);
    }
  };

  const fetchDocuments = async () => {
    if (!guestId) return;
    try {
      const response = await axios.get(`${API}/documents?guest_id=${guestId}`);
      setDocuments(response.data.documents);
    } catch (error) {
      console.error("Erreur lors du chargement des documents:", error);
    }
  };

  const generateDocument = async () => {
    if (!selectedMatiere || !selectedNiveau || !selectedChapitre) {
      alert("Veuillez sélectionner une matière, un niveau et un chapitre");
      return;
    }

    setIsGenerating(true);
    try {
      const response = await axios.post(`${API}/generate`, {
        matiere: selectedMatiere,
        niveau: selectedNiveau,
        chapitre: selectedChapitre,
        type_doc: typeDoc,
        difficulte: difficulte,
        nb_exercices: nbExercices,
        guest_id: guestId
      });
      
      setCurrentDocument(response.data.document);
      await fetchDocuments();
    } catch (error) {
      console.error("Erreur lors de la génération:", error);
      alert("Erreur lors de la génération du document");
    } finally {
      setIsGenerating(false);
    }
  };

  const exportPDF = async (exportType) => {
    if (!currentDocument) return;

    const setLoading = exportType === 'sujet' ? setExportingSubject : setExportingSolution;
    setLoading(true);

    try {
      const response = await axios.post(`${API}/export`, {
        document_id: currentDocument.id,
        export_type: exportType,
        guest_id: guestId
      }, {
        responseType: 'blob'
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `${currentDocument.type_doc}_${currentDocument.matiere}_${currentDocument.niveau}_${exportType}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      // Refresh quota
      await fetchQuotaStatus();
      
    } catch (error) {
      console.error("Erreur lors de l'export:", error);
      
      if (error.response?.status === 402) {
        const errorData = error.response.data;
        if (errorData.action === "signup_required") {
          setShowSignupModal(true);
        } else {
          alert("Quota d'exports dépassé");
        }
      } else {
        alert("Erreur lors de l'export PDF");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async () => {
    if (!signupData.email) {
      alert("Veuillez saisir votre adresse email");
      return;
    }

    setSignupLoading(true);
    try {
      await axios.post(`${API}/auth/signup`, signupData);
      setSignupSuccess(true);
    } catch (error) {
      console.error("Erreur lors de l'inscription:", error);
      alert("Erreur lors de l'inscription");
    } finally {
      setSignupLoading(false);
    }
  };

  const varyExercise = async (exerciseIndex) => {
    if (!currentDocument) return;
    
    try {
      const response = await axios.post(`${API}/documents/${currentDocument.id}/vary/${exerciseIndex}`);
      const updatedDoc = { ...currentDocument };
      updatedDoc.exercises[exerciseIndex] = response.data.exercise;
      setCurrentDocument(updatedDoc);
    } catch (error) {
      console.error("Erreur lors de la variation:", error);
      alert("Erreur lors de la génération de la variation");
    }
  };

  useEffect(() => {
    fetchCatalog();
  }, []);

  useEffect(() => {
    if (guestId) {
      fetchQuotaStatus();
      fetchDocuments();
    }
  }, [guestId]);

  const availableLevels = catalog.find(m => m.name === selectedMatiere)?.levels || [];
  const availableChapters = availableLevels.find(l => l.name === selectedNiveau)?.chapters || [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-6">
            <GraduationCap className="h-12 w-12 text-blue-600 mr-3" />
            <h1 className="text-4xl font-bold text-gray-900">LessonSmith V1</h1>
          </div>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Générateur de documents pédagogiques personnalisés pour les enseignants français
          </p>
          
          {/* Quota Status */}
          <div className="mt-4">
            {quotaStatus.quota_exceeded ? (
              <Alert className="max-w-md mx-auto border-orange-200 bg-orange-50">
                <AlertCircle className="h-4 w-4 text-orange-600" />
                <AlertDescription className="text-orange-800">
                  <strong>Limite atteinte :</strong> 3 exports gratuits utilisés. 
                  <Button variant="link" className="p-0 h-auto text-orange-600 underline ml-1" onClick={() => setShowSignupModal(true)}>
                    Créer un compte
                  </Button> pour continuer.
                </AlertDescription>
              </Alert>
            ) : (
              <Alert className="max-w-md mx-auto border-green-200 bg-green-50">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <AlertDescription className="text-green-800">
                  <strong>Mode invité :</strong> {quotaStatus.exports_remaining} exports gratuits restants
                </AlertDescription>
              </Alert>
            )}
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Generation Panel */}
          <Card className="shadow-lg border-0 bg-white/80 backdrop-blur-sm">
            <CardHeader className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-t-lg">
              <CardTitle className="flex items-center">
                <BookOpen className="mr-2 h-5 w-5" />
                Créer un nouveau document
              </CardTitle>
              <CardDescription className="text-blue-50">
                Sélectionnez les paramètres pour générer votre document
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              {/* Step 1 */}
              <div className="space-y-4">
                <div className="flex items-center mb-3">
                  <div className="bg-blue-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold mr-3">1</div>
                  <h3 className="text-lg font-semibold text-gray-900">Programme scolaire</h3>
                </div>
                
                <div className="grid gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Matière</label>
                    <Select value={selectedMatiere} onValueChange={setSelectedMatiere}>
                      <SelectTrigger>
                        <SelectValue placeholder="Choisir une matière" />
                      </SelectTrigger>
                      <SelectContent>
                        {catalog.map(matiere => (
                          <SelectItem key={matiere.name} value={matiere.name}>
                            {matiere.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Niveau</label>
                    <Select value={selectedNiveau} onValueChange={setSelectedNiveau} disabled={!selectedMatiere}>
                      <SelectTrigger>
                        <SelectValue placeholder="Choisir un niveau" />
                      </SelectTrigger>
                      <SelectContent>
                        {availableLevels.map(niveau => (
                          <SelectItem key={niveau.name} value={niveau.name}>
                            {niveau.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Chapitre</label>
                    <Select value={selectedChapitre} onValueChange={setSelectedChapitre} disabled={!selectedNiveau}>
                      <SelectTrigger>
                        <SelectValue placeholder="Choisir un chapitre" />
                      </SelectTrigger>
                      <SelectContent>
                        {availableChapters.map(chapitre => (
                          <SelectItem key={chapitre} value={chapitre}>
                            {chapitre}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Step 2 */}
              <div className="space-y-4">
                <div className="flex items-center mb-3">
                  <div className="bg-blue-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold mr-3">2</div>
                  <h3 className="text-lg font-semibold text-gray-900">Paramètres du document</h3>
                </div>

                <div className="grid gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Type de document</label>
                    <Select value={typeDoc} onValueChange={setTypeDoc}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="exercices">Feuille d'exercices</SelectItem>
                        <SelectItem value="controle">Contrôle</SelectItem>
                        <SelectItem value="dm">Devoir maison</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Difficulté</label>
                    <Select value={difficulte} onValueChange={setDifficulte}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="facile">Facile</SelectItem>
                        <SelectItem value="moyen">Moyen</SelectItem>
                        <SelectItem value="difficile">Difficile</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Nombre d'exercices</label>
                    <Select value={nbExercices.toString()} onValueChange={(value) => setNbExercices(parseInt(value))}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {[3, 4, 5, 6, 7, 8, 9, 10].map(n => (
                          <SelectItem key={n} value={n.toString()}>{n} exercices</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Step 3 */}
              <div>
                <div className="flex items-center mb-4">
                  <div className="bg-blue-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold mr-3">3</div>
                  <h3 className="text-lg font-semibold text-gray-900">Génération</h3>
                </div>

                <Button 
                  onClick={generateDocument}
                  disabled={!selectedMatiere || !selectedNiveau || !selectedChapitre || isGenerating}
                  className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white py-3 rounded-lg font-semibold transition-all duration-200"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Génération en cours...
                    </>
                  ) : (
                    <>
                      <FileText className="mr-2 h-4 w-4" />
                      Générer le document
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Preview Panel */}
          <Card className="shadow-lg border-0 bg-white/80 backdrop-blur-sm">
            <CardHeader className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-t-lg">
              <CardTitle className="flex items-center">
                <FileText className="mr-2 h-5 w-5" />
                Aperçu du document
              </CardTitle>
              <CardDescription className="text-indigo-50">
                Prévisualisez et exportez votre document
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              {currentDocument ? (
                <div className="space-y-6">
                  {/* Document Info */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className="font-bold text-lg text-gray-900">{currentDocument.type_doc.charAt(0).toUpperCase() + currentDocument.type_doc.slice(1)}</h3>
                        <p className="text-gray-600">{currentDocument.matiere} - {currentDocument.niveau}</p>
                        <p className="text-sm text-gray-500">{currentDocument.chapitre}</p>
                      </div>
                      <div className="text-right">
                        <Badge variant="outline" className="mb-1">{currentDocument.difficulte}</Badge>
                        <p className="text-sm text-gray-500">{currentDocument.nb_exercices} exercices</p>
                      </div>
                    </div>
                  </div>

                  {/* Export Buttons */}
                  <div className="grid grid-cols-2 gap-4">
                    <Button 
                      onClick={() => exportPDF('sujet')}
                      disabled={exportingSubject || quotaStatus.quota_exceeded}
                      className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white"
                    >
                      {exportingSubject ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Export...
                        </>
                      ) : (
                        <>
                          <Download className="mr-2 h-4 w-4" />
                          Export Sujet PDF
                        </>
                      )}
                    </Button>
                    
                    <Button 
                      onClick={() => exportPDF('corrige')}
                      disabled={exportingSolution || quotaStatus.quota_exceeded}
                      className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white"
                    >
                      {exportingSolution ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Export...
                        </>
                      ) : (
                        <>
                          <Download className="mr-2 h-4 w-4" />
                          Export Corrigé PDF
                        </>
                      )}
                    </Button>
                  </div>

                  {/* Exercises */}
                  <Tabs defaultValue="sujet" className="w-full">
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="sujet">Sujet</TabsTrigger>
                      <TabsTrigger value="corrige">Corrigé</TabsTrigger>
                    </TabsList>
                    
                    <TabsContent value="sujet" className="space-y-4 mt-4">
                      {currentDocument.exercises.map((exercise, index) => (
                        <Card key={exercise.id} className="border-l-4 border-l-blue-500">
                          <CardContent className="p-4">
                            <div className="flex justify-between items-start mb-3">
                              <div className="flex items-center">
                                <span className="font-bold text-blue-600 mr-2">Exercice {index + 1}</span>
                                <Badge variant="secondary" className="text-xs">{exercise.type}</Badge>
                                <Badge variant="outline" className="text-xs ml-2">{exercise.difficulte}</Badge>
                              </div>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => varyExercise(index)}
                                className="text-gray-500 hover:text-gray-700"
                              >
                                <Shuffle className="h-4 w-4" />
                              </Button>
                            </div>
                            <p className="text-gray-900 whitespace-pre-wrap">{exercise.enonce}</p>
                          </CardContent>
                        </Card>
                      ))}
                    </TabsContent>
                    
                    <TabsContent value="corrige" className="space-y-4 mt-4">
                      {currentDocument.exercises.map((exercise, index) => (
                        <Card key={exercise.id} className="border-l-4 border-l-green-500">
                          <CardContent className="p-4">
                            <div className="flex items-center mb-3">
                              <span className="font-bold text-green-600 mr-2">Exercice {index + 1} - Solution</span>
                            </div>
                            <div className="space-y-2">
                              {exercise.solution.etapes.map((etape, etapeIndex) => (
                                <div key={etapeIndex} className="text-sm">
                                  <span className="font-medium text-gray-700">Étape {etapeIndex + 1}:</span>
                                  <span className="ml-2 text-gray-900">{etape}</span>
                                </div>
                              ))}
                              <div className="mt-3 p-2 bg-green-50 rounded">
                                <strong className="text-green-800">Résultat :</strong> 
                                <span className="ml-2 text-green-900">{exercise.solution.resultat}</span>
                              </div>
                              {exercise.bareme.length > 0 && (
                                <div className="mt-3 p-2 bg-blue-50 rounded">
                                  <strong className="text-blue-800">Barème :</strong>
                                  <ul className="list-disc list-inside mt-1 text-sm">
                                    {exercise.bareme.map((item, i) => (
                                      <li key={i} className="text-blue-900">
                                        {item.etape}: {item.points} pts
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </TabsContent>
                  </Tabs>
                </div>
              ) : (
                <div className="text-center py-12">
                  <FileText className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Aucun document généré</h3>
                  <p className="text-gray-500">
                    Utilisez le panneau de gauche pour créer votre premier document
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Recent Documents */}
        {documents.length > 0 && (
          <Card className="mt-8 shadow-lg border-0 bg-white/80 backdrop-blur-sm">
            <CardHeader className="bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-t-lg">
              <CardTitle>Documents récents</CardTitle>
              <CardDescription className="text-purple-50">
                Vos derniers documents générés
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {documents.slice(0, 6).map((doc) => (
                  <Card key={doc.id} className="cursor-pointer hover:shadow-md transition-shadow border border-gray-200">
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start mb-2">
                        <h4 className="font-semibold text-gray-900">{doc.type_doc}</h4>
                        <Badge variant="outline" className="text-xs">{doc.difficulte}</Badge>
                      </div>
                      <p className="text-sm text-gray-600 mb-1">{doc.matiere} - {doc.niveau}</p>
                      <p className="text-xs text-gray-500 mb-3">{doc.chapitre}</p>
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-400">
                          {doc.nb_exercices} exercices
                        </span>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => setCurrentDocument(doc)}
                          className="text-blue-600 hover:text-blue-700"
                        >
                          Ouvrir
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Signup Modal */}
        <Dialog open={showSignupModal} onOpenChange={setShowSignupModal}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center">
                <User className="mr-2 h-5 w-5" />
                Créer un compte gratuit
              </DialogTitle>
              <DialogDescription>
                Débloquez les exports illimités et sauvegardez vos documents
              </DialogDescription>
            </DialogHeader>
            
            {signupSuccess ? (
              <div className="text-center py-6">
                <CheckCircle className="mx-auto h-12 w-12 text-green-600 mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Lien envoyé !
                </h3>
                <p className="text-gray-600">
                  Vérifiez votre boîte email et cliquez sur le lien de connexion.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <Label htmlFor="email">Adresse email *</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="votre@email.fr"
                    value={signupData.email}
                    onChange={(e) => setSignupData(prev => ({...prev, email: e.target.value}))}
                  />
                </div>
                <div>
                  <Label htmlFor="nom">Nom (optionnel)</Label>
                  <Input
                    id="nom"
                    placeholder="Votre nom"
                    value={signupData.nom}
                    onChange={(e) => setSignupData(prev => ({...prev, nom: e.target.value}))}
                  />
                </div>
                <div>
                  <Label htmlFor="etablissement">Établissement (optionnel)</Label>
                  <Input
                    id="etablissement"
                    placeholder="Nom de votre établissement"
                    value={signupData.etablissement}
                    onChange={(e) => setSignupData(prev => ({...prev, etablissement: e.target.value}))}
                  />
                </div>
                
                <Button 
                  onClick={handleSignup}
                  disabled={signupLoading}
                  className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
                >
                  {signupLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Inscription...
                    </>
                  ) : (
                    <>
                      <Mail className="mr-2 h-4 w-4" />
                      Envoyer le lien de connexion
                    </>
                  )}
                </Button>
                
                <p className="text-xs text-gray-500 text-center">
                  Aucun mot de passe requis. Connexion par lien magique.
                </p>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}

export default App;