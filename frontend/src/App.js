import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";
import { BrowserRouter, Routes, Route, useSearchParams, useNavigate, useLocation } from "react-router-dom";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./components/ui/select";
import { Badge } from "./components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { Separator } from "./components/ui/separator";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "./components/ui/dialog";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import { Alert, AlertDescription } from "./components/ui/alert";
import { BookOpen, FileText, Download, Shuffle, Loader2, GraduationCap, AlertCircle, CheckCircle, Crown, CreditCard, LogIn, LogOut, Mail } from "lucide-react";
import TemplateSettings from "./components/TemplateSettings";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Payment Success Component
function PaymentSuccess() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [checkingStatus, setCheckingStatus] = useState(true);
  const [paymentStatus, setPaymentStatus] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const sessionId = searchParams.get('session_id');
    if (!sessionId) {
      setError("Session ID manquant");
      setCheckingStatus(false);
      return;
    }

    pollPaymentStatus(sessionId);
  }, [searchParams]);

  const pollPaymentStatus = async (sessionId, attempts = 0) => {
    const maxAttempts = 5;
    const pollInterval = 2000; // 2 seconds

    if (attempts >= maxAttempts) {
      setError('Vérification du paiement expirée. Veuillez contacter le support.');
      setCheckingStatus(false);
      return;
    }

    try {
      const response = await axios.get(`${API}/checkout/status/${sessionId}`);
      
      if (response.data.payment_status === 'paid') {
        setPaymentStatus('success');
        setCheckingStatus(false);
        
        // Redirect to main app after 3 seconds
        setTimeout(() => {
          navigate('/');
        }, 3000);
        return;
      } else if (response.data.status === 'expired') {
        setError('Session de paiement expirée. Veuillez réessayer.');
        setCheckingStatus(false);
        return;
      }

      // Continue polling if payment is still pending
      setTimeout(() => pollPaymentStatus(sessionId, attempts + 1), pollInterval);
    } catch (error) {
      console.error('Error checking payment status:', error);
      setError('Erreur lors de la vérification du paiement.');
      setCheckingStatus(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <GraduationCap className="mx-auto h-12 w-12 text-blue-600 mb-4" />
          <CardTitle>Le Maître Mot - Paiement</CardTitle>
        </CardHeader>
        <CardContent className="text-center">
          {checkingStatus ? (
            <div>
              <Loader2 className="mx-auto h-8 w-8 animate-spin text-blue-600 mb-4" />
              <p>Vérification du paiement en cours...</p>
            </div>
          ) : error ? (
            <div>
              <AlertCircle className="mx-auto h-8 w-8 text-red-600 mb-4" />
              <p className="text-red-600 mb-4">{error}</p>
              <Button onClick={() => navigate('/')} variant="outline">
                Retour à l'accueil
              </Button>
            </div>
          ) : paymentStatus === 'success' ? (
            <div>
              <CheckCircle className="mx-auto h-8 w-8 text-green-600 mb-4" />
              <h3 className="text-lg font-semibold mb-2">Paiement réussi !</h3>
              <p className="text-gray-600 mb-2">Votre abonnement Pro est maintenant actif</p>
              <p className="text-sm text-gray-500 mb-4">
                Vous avez accès aux exports illimités
              </p>
              <p className="text-sm text-gray-500">
                Redirection automatique vers l'accueil...
              </p>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

// Payment Cancel Component
function PaymentCancel() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <GraduationCap className="mx-auto h-12 w-12 text-blue-600 mb-4" />
          <CardTitle>Le Maître Mot - Paiement Annulé</CardTitle>
        </CardHeader>
        <CardContent className="text-center">
          <AlertCircle className="mx-auto h-8 w-8 text-orange-600 mb-4" />
          <h3 className="text-lg font-semibold mb-2">Paiement annulé</h3>
          <p className="text-gray-600 mb-4">
            Votre paiement a été annulé. Vous pouvez réessayer à tout moment.
          </p>
          <Button onClick={() => navigate('/')} className="w-full">
            Retour à l'accueil
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

// Login Verification Component (for magic link)
function LoginVerify() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [verifying, setVerifying] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setError("Token manquant");
      setVerifying(false);
      return;
    }

    verifyLogin(token);
  }, [searchParams]);

  const verifyLogin = async (token) => {
    try {
      // Generate device ID
      const deviceId = localStorage.getItem('lemaitremot_device_id') || generateDeviceId();
      localStorage.setItem('lemaitremot_device_id', deviceId);

      const response = await axios.post(`${API}/auth/verify-login`, {
        token: token,
        device_id: deviceId
      });

      // Store session token and user info
      localStorage.setItem('lemaitremot_session_token', response.data.session_token);
      localStorage.setItem('lemaitremot_user_email', response.data.email);
      localStorage.setItem('lemaitremot_login_method', 'session');

      setSuccess(true);
      setTimeout(() => {
        navigate('/');
      }, 2000);

    } catch (error) {
      console.error('Error verifying login:', error);
      setError(error.response?.data?.detail || 'Erreur lors de la vérification');
    } finally {
      setVerifying(false);
    }
  };

  const generateDeviceId = () => {
    return 'device_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex items-center justify-center mb-4">
            <GraduationCap className="h-8 w-8 text-blue-600 mr-2" />
            <h1 className="text-2xl font-bold text-gray-900">Le Maître Mot</h1>
          </div>
          <CardTitle>Connexion en cours</CardTitle>
        </CardHeader>
        <CardContent className="text-center">
          {verifying ? (
            <div className="space-y-4">
              <Loader2 className="h-8 w-8 text-blue-600 animate-spin mx-auto" />
              <p className="text-gray-600">Vérification de votre connexion...</p>
            </div>
          ) : error ? (
            <div className="space-y-4">
              <AlertCircle className="h-8 w-8 text-red-600 mx-auto" />
              <p className="text-red-600">{error}</p>
              <Button 
                onClick={() => navigate('/')}
                variant="outline"
                className="w-full"
              >
                Retour à l'accueil
              </Button>
            </div>
          ) : success ? (
            <div className="space-y-4">
              <CheckCircle className="h-8 w-8 text-green-600 mx-auto" />
              <p className="text-green-600">✅ Connexion réussie !</p>
              <p className="text-sm text-gray-500">Redirection en cours...</p>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

function MainApp() {
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
  
  // Guest and quota management (new logic)
  const [guestId, setGuestId] = useState("");
  const [quotaStatus, setQuotaStatus] = useState({ 
    exports_remaining: 3, 
    quota_exceeded: false,
    exports_used: 0,
    max_exports: 3
  });
  const [quotaLoaded, setQuotaLoaded] = useState(false);
  
  // Pro status management
  const [userEmail, setUserEmail] = useState("");
  const [isPro, setIsPro] = useState(false);
  const [proStatusChecked, setProStatusChecked] = useState(false);
  const [sessionToken, setSessionToken] = useState("");
  
  // Template states
  const [userTemplate, setUserTemplate] = useState(null);
  const [templateUpdated, setTemplateUpdated] = useState(false);
  
  // Payment modal
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [pricing, setPricing] = useState({});
  const [paymentEmail, setPaymentEmail] = useState("");
  const [paymentLoading, setPaymentLoading] = useState(false);
  
  // Login modal for existing Pro users
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [loginEmail, setLoginEmail] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginSuccess, setLoginSuccess] = useState(false);
  const [loginEmailSent, setLoginEmailSent] = useState(false);
  
  // Export states
  const [exportingSubject, setExportingSubject] = useState(false);
  const [exportingSolution, setExportingSolution] = useState(false);
  
  // Export style selection
  const [exportStyles, setExportStyles] = useState({});
  const [selectedExportStyle, setSelectedExportStyle] = useState("classique");

  // Initialize guest ID and check Pro status
  useEffect(() => {
    let storedGuestId = localStorage.getItem('lemaitremot_guest_id');
    if (!storedGuestId) {
      storedGuestId = 'guest_' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('lemaitremot_guest_id', storedGuestId);
    }
    setGuestId(storedGuestId);
    
    // Check if user has a stored email (Pro user)
    const storedEmail = localStorage.getItem('lemaitremot_user_email');
    if (storedEmail) {
      console.log('Found stored email, checking Pro status for:', storedEmail);
      setUserEmail(storedEmail);
      setPaymentEmail(storedEmail); // Pre-fill payment form
      checkProStatus(storedEmail);
    } else {
      setProStatusChecked(true);
    }
    
    console.log('Guest ID:', storedGuestId, 'Stored email:', storedEmail);
  }, []);

  const checkProStatus = async (email) => {
    try {
      const response = await axios.get(`${API}/user/status/${encodeURIComponent(email)}`);
      const isProUser = response.data.is_pro;
      
      setIsPro(isProUser);
      setProStatusChecked(true);
      
      console.log('Pro status check:', { email, isPro: isProUser });
      
      if (isProUser) {
        console.log('✅ User is Pro - unlimited exports');
      }
    } catch (error) {
      console.error('Error checking Pro status:', error);
      setIsPro(false);
      setProStatusChecked(true);
    }
  };

  const fetchCatalog = async () => {
    try {
      const response = await axios.get(`${API}/catalog`);
      setCatalog(response.data.catalog);
    } catch (error) {
      console.error("Erreur lors du chargement du catalogue:", error);
    }
  };

  const fetchPricing = async () => {
    try {
      const response = await axios.get(`${API}/pricing`);
      setPricing(response.data.packages);
    } catch (error) {
      console.error("Erreur lors du chargement des prix:", error);
    }
  };

  const fetchQuotaStatus = async () => {
    // Pro users have unlimited exports
    if (isPro) {
      setQuotaStatus({
        exports_remaining: 999,
        quota_exceeded: false,
        exports_used: 0,
        max_exports: 999,
        is_pro: true
      });
      setQuotaLoaded(true);
      console.log('Pro user - unlimited quota set');
      return;
    }
    
    if (!guestId) return;
    try {
      const response = await axios.get(`${API}/quota/check?guest_id=${guestId}`);
      setQuotaStatus(response.data);
      setQuotaLoaded(true);
      console.log('Guest quota status:', response.data);
    } catch (error) {
      console.error("Erreur lors du chargement du quota:", error);
      // Set safe defaults on error
      setQuotaStatus({ 
        exports_remaining: 3, 
        quota_exceeded: false,
        exports_used: 0,
        max_exports: 3
      });
      setQuotaLoaded(true);
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

  const fetchExportStyles = async () => {
    try {
      const config = {};
      
      // Include session token if available
      if (sessionToken) {
        config.headers = {
          'X-Session-Token': sessionToken
        };
      }
      
      const response = await axios.get(`${API}/export/styles`, config);
      setExportStyles(response.data.styles || {});
      console.log('📊 Export styles loaded:', response.data);
      
      // If user is not Pro and current selection is Pro-only, reset to classique
      if (!response.data.user_is_pro && response.data.styles[selectedExportStyle]?.pro_only) {
        setSelectedExportStyle("classique");
      }
    } catch (error) {
      console.error("Erreur lors du chargement des styles d'export:", error);
      // Set safe default
      setExportStyles({
        "classique": {
          "name": "Classique",
          "description": "Style traditionnel élégant",
          "pro_only": false
        }
      });
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
      }, {
        timeout: 30000  // 30 seconds timeout
      });
      
      setCurrentDocument(response.data.document);
      await fetchDocuments();
    } catch (error) {
      console.error("Erreur lors de la génération:", error);
      if (error.code === 'ECONNABORTED') {
        alert("La génération prend trop de temps. Veuillez réessayer avec moins d'exercices.");
      } else {
        alert("Erreur lors de la génération du document");
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const exportPDF = async (exportType) => {
    if (!currentDocument) return;

    console.log('📄 Export PDF requested:', {
      exportType,
      isPro,
      hasSessionToken: !!sessionToken,
      userEmail,
      sessionTokenPreview: sessionToken ? sessionToken.substring(0, 20) + '...' : 'none'
    });

    const setLoading = exportType === 'sujet' ? setExportingSubject : setExportingSolution;
    setLoading(true);

    try {
      const requestData = {
        document_id: currentDocument.id,
        export_type: exportType,
        template_style: selectedExportStyle
      };
      
      // Pro users don't need guest_id, regular users do
      if (!isPro) {
        requestData.guest_id = guestId;
      }
      
      const requestConfig = {
        responseType: 'blob'
      };
      
      // Send session token if available (let backend determine Pro status)
      if (sessionToken) {
        requestConfig.headers = {
          'X-Session-Token': sessionToken
        };
        console.log('🔐 Sending session token with export request:', sessionToken.substring(0, 20) + '...');
      } else {
        console.log('⚠️ No session token available for export request');
      }

      console.log('📤 Making export request with config:', {
        url: `${API}/export`,
        hasHeaders: !!requestConfig.headers,
        requestData
      });

      const response = await axios.post(`${API}/export`, requestData, requestConfig);

      console.log('✅ Export response received:', {
        status: response.status,
        contentType: response.headers['content-type'],
        size: response.data.size
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `LeMaitremot_${currentDocument.type_doc}_${currentDocument.matiere}_${currentDocument.niveau}_${exportType}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      // Refresh quota
      await fetchQuotaStatus();
      
    } catch (error) {
      console.error("Erreur lors de l'export:", error);
      
      // Handle session expiry/invalidity (someone else logged in)
      if (error.response?.status === 401 || error.response?.status === 402) {
        if (sessionToken && isPro) {
          console.log('Session invalidated - user may have been logged out by another device');
          // Clear ALL session data completely
          localStorage.removeItem('lemaitremot_session_token');
          localStorage.removeItem('lemaitremot_user_email');
          localStorage.removeItem('lemaitremot_login_method');
          
          setSessionToken("");
          setUserEmail("");
          setIsPro(false);
          setProStatusChecked(true);
          
          alert('Votre session a expiré ou a été fermée depuis un autre appareil. Veuillez vous reconnecter.');
          setShowLoginModal(true);
          return;
        } else if (error.response?.status === 402) {
          const errorData = error.response.data;
          if (errorData.action === "upgrade_required") {
            setShowPaymentModal(true);
          } else {
            alert("Quota d'exports dépassé");
          }
        }
      } else {
        alert("Erreur lors de l'export PDF");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUpgradeClick = async (packageId) => {
    if (!paymentEmail || !paymentEmail.includes('@')) {
      alert('Veuillez saisir une adresse email valide');
      return;
    }
    
    setPaymentLoading(true);
    
    try {
      const originUrl = window.location.origin;
      
      const response = await axios.post(`${API}/checkout/session`, {
        package_id: packageId,
        origin_url: originUrl,
        email: paymentEmail
      });

      if (response.data.url) {
        // Store email for when user returns
        localStorage.setItem('lemaitremot_user_email', paymentEmail);
        localStorage.setItem('lemaitremot_pending_payment', 'true');
        
        // Redirect to Stripe Checkout
        window.location.href = response.data.url;
      } else {
        throw new Error('Aucune URL de checkout reçue');
      }
    } catch (error) {
      console.error('Erreur lors du paiement:', error);
      
      // Handle duplicate subscription error
      if (error.response?.status === 409) {
        const errorData = error.response.data;
        if (errorData.error === "already_subscribed") {
          alert(`⚠️ Abonnement existant détecté\n\n${errorData.message}\n\nSi vous souhaitez modifier votre abonnement, veuillez nous contacter.`);
        } else {
          alert('Cette adresse email dispose déjà d\'un abonnement actif.');
        }
      } else {
        alert('Erreur lors de la création de la session de paiement');
      }
    } finally {
      setPaymentLoading(false);
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

  // Initialize authentication on load and set up session monitoring
  useEffect(() => {
    initializeAuth();
    fetchCatalog();
    fetchPricing();
    fetchExportStyles();
    
    // Set up periodic session validation for Pro users
    const sessionCheckInterval = setInterval(() => {
      if (sessionToken) {
        validateSession(sessionToken, true); // silent validation
      }
    }, 60000); // Check every minute
    
    // Check if user just returned from payment
    const pendingPayment = localStorage.getItem('lemaitremot_pending_payment');
    if (pendingPayment && userEmail) {
      console.log('User returned from payment, checking Pro status...');
      localStorage.removeItem('lemaitremot_pending_payment');
      
      // Wait a bit for webhook processing, then check status
      setTimeout(() => {
        checkProStatus(userEmail);
      }, 3000);
    }
    
    // Cleanup interval on unmount
    return () => {
      clearInterval(sessionCheckInterval);
    };
  }, [sessionToken]);

  const initializeAuth = () => {
    // Check for session token (new method)
    const storedSessionToken = localStorage.getItem('lemaitremot_session_token');
    const storedEmail = localStorage.getItem('lemaitremot_user_email');
    const loginMethod = localStorage.getItem('lemaitremot_login_method');
    
    if (storedSessionToken && storedEmail && loginMethod === 'session') {
      setSessionToken(storedSessionToken);
      setUserEmail(storedEmail);
      validateSession(storedSessionToken);
    } else if (storedEmail && loginMethod !== 'session') {
      // Legacy method (email only)
      setUserEmail(storedEmail);
      checkProStatus(storedEmail);
    } else {
      setProStatusChecked(true);
    }
  };

  const validateSession = async (token, silent = false) => {
    try {
      const response = await axios.get(`${API}/auth/session/validate`, {
        headers: {
          'X-Session-Token': token
        }
      });
      
      setUserEmail(response.data.email);
      setIsPro(true);
      setProStatusChecked(true);
      
      if (!silent) {
        console.log('✅ Session valid - user is Pro:', response.data.email);
      }
      
    } catch (error) {
      if (!silent) {
        console.error('Session validation failed:', error);
      }
      
      // Clear ALL invalid session data (complete cleanup)
      localStorage.removeItem('lemaitremot_session_token');
      localStorage.removeItem('lemaitremot_user_email');
      localStorage.removeItem('lemaitremot_login_method');
      
      setSessionToken("");
      setUserEmail("");  // Added: Clear email state
      setIsPro(false);
      setProStatusChecked(true);
      
      // If it was session expired/invalid during active use (not silent check)
      if (error.response?.status === 401) {
        if (!silent) {
          console.log('Session expired - user needs to login again');
          alert('Votre session a expiré. Vous avez peut-être été déconnecté depuis un autre appareil.');
          setShowLoginModal(true);
        } else {
          console.log('Session invalidated silently (probably from another device)');
        }
      }
    }
  };

  const requestLogin = async (email) => {
    setLoginLoading(true);
    try {
      await axios.post(`${API}/auth/request-login`, {
        email: email
      });
      
      setLoginEmailSent(true);
      console.log('✅ Magic link sent to:', email);
      
    } catch (error) {
      console.error('Error requesting login:', error);
      const errorMsg = error.response?.data?.detail || 'Erreur lors de l\'envoi du lien de connexion';
      alert(errorMsg);
    } finally {
      setLoginLoading(false);
    }
  };

  const logout = async () => {
    try {
      if (sessionToken) {
        await axios.post(`${API}/auth/logout`, {}, {
          headers: {
            'X-Session-Token': sessionToken
          }
        });
      }
      
      // Clear all auth data
      localStorage.removeItem('lemaitremot_session_token');
      localStorage.removeItem('lemaitremot_user_email');
      localStorage.removeItem('lemaitremot_login_method');
      
      setSessionToken("");
      setUserEmail("");
      setIsPro(false);
      setProStatusChecked(true);
      
      console.log('✅ Logged out successfully');
      
    } catch (error) {
      console.error('Error during logout:', error);
      
      // Clear local data anyway
      localStorage.removeItem('lemaitremot_session_token');
      localStorage.removeItem('lemaitremot_user_email');
      localStorage.removeItem('lemaitremot_login_method');
      
      setSessionToken("");
      setUserEmail("");
      setIsPro(false);
      setProStatusChecked(true);
    }
  };

  useEffect(() => {
    if (guestId && proStatusChecked) {
      fetchQuotaStatus();
      fetchDocuments();
      fetchExportStyles(); // Refresh styles when Pro status changes
    }
  }, [guestId, proStatusChecked, isPro]);

  const availableLevels = catalog.find(m => m.name === selectedMatiere)?.levels || [];
  const availableChapters = availableLevels.find(l => l.name === selectedNiveau)?.chapters || [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-6">
            <GraduationCap className="h-12 w-12 text-blue-600 mr-3" />
            <h1 className="text-4xl font-bold text-gray-900">Le Maître Mot</h1>
          </div>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Générateur de documents pédagogiques personnalisés pour les enseignants français
          </p>
          
          {/* Quota Status */}
          <div className="mt-4">
            {quotaLoaded ? (
              isPro ? (
                <div className="flex flex-col items-center space-y-3">
                  <Alert className="max-w-md mx-auto border-blue-200 bg-blue-50">
                    <Crown className="h-4 w-4 text-blue-600" />
                    <AlertDescription className="text-blue-800">
                      <strong>Le Maître Mot Pro :</strong> Exports illimités
                      {userEmail && <span className="block text-xs mt-1">({userEmail})</span>}
                    </AlertDescription>
                  </Alert>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={logout}
                    className="text-xs flex items-center"
                  >
                    <LogOut className="h-3 w-3 mr-1" />
                    Se déconnecter
                  </Button>
                </div>
              ) : quotaStatus.quota_exceeded ? (
                <div className="flex flex-col items-center space-y-3">
                  <Alert className="max-w-md mx-auto border-orange-200 bg-orange-50">
                    <AlertCircle className="h-4 w-4 text-orange-600" />
                    <AlertDescription className="text-orange-800">
                      <strong>Limite atteinte :</strong> 3 exports gratuits utilisés.
                      <div className="flex gap-2 mt-2">
                        <Button 
                          variant="link" 
                          className="p-0 h-auto text-orange-600 underline" 
                          onClick={() => setShowPaymentModal(true)}
                        >
                          Passer à Pro
                        </Button>
                        <span className="text-orange-600">ou</span>
                        <Button 
                          variant="link" 
                          className="p-0 h-auto text-orange-600 underline" 
                          onClick={() => setShowLoginModal(true)}
                        >
                          Se connecter
                        </Button>
                      </div>
                    </AlertDescription>
                  </Alert>
                </div>
              ) : (
                <div className="flex flex-col items-center space-y-3">
                  <Alert className="max-w-md mx-auto border-green-200 bg-green-50">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <AlertDescription className="text-green-800">
                      <strong>Mode gratuit :</strong> {quotaStatus.exports_remaining} exports restants
                    </AlertDescription>
                  </Alert>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => setShowLoginModal(true)}
                    className="text-xs flex items-center"
                  >
                    <LogIn className="h-3 w-3 mr-1" />
                    Déjà Pro ? Se connecter
                  </Button>
                </div>
              )
            ) : (
              <Alert className="max-w-md mx-auto border-gray-200 bg-gray-50">
                <Loader2 className="h-4 w-4 text-gray-600 animate-spin" />
                <AlertDescription className="text-gray-700">
                  Chargement des quotas...
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

              {/* Template Settings */}
              <TemplateSettings 
                isPro={isPro}
                sessionToken={sessionToken}
                onTemplateChange={(template) => {
                  setUserTemplate(template);
                  setTemplateUpdated(true);
                }}
              />

              <Separator />

              {/* Step 3: Generate Document */}
              <div className="space-y-4">
                <div className="flex items-center mb-3">
                  <div className="bg-green-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold mr-3">3</div>
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
                      disabled={!currentDocument || exportingSubject}
                      className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white disabled:opacity-50"
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
                      disabled={!currentDocument || exportingSolution}
                      className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white disabled:opacity-50"
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

                  {/* Export Style Selection */}
                  {currentDocument && (
                    <div className="border-t pt-4 mt-4">
                      <div className="mb-3">
                        <Label htmlFor="export-style" className="text-sm font-medium text-gray-700 flex items-center">
                          🎨 Style d'export
                          {!isPro && (
                            <Badge variant="outline" className="ml-2 text-xs">
                              Pro requis pour plus de styles
                            </Badge>
                          )}
                        </Label>
                      </div>
                      <Select value={selectedExportStyle} onValueChange={setSelectedExportStyle}>
                        <SelectTrigger>
                          <SelectValue placeholder="Choisir un style" />
                        </SelectTrigger>
                        <SelectContent>
                          {Object.entries(exportStyles).map(([styleId, style]) => (
                            <SelectItem 
                              key={styleId} 
                              value={styleId}
                              disabled={style.pro_only && !isPro}
                            >
                              <div className="flex items-center justify-between w-full">
                                <div>
                                  <div className="font-medium">{style.name}</div>
                                  <div className="text-xs text-gray-500">{style.description}</div>
                                </div>
                                {style.pro_only && (
                                  <Crown className="h-3 w-3 text-yellow-500 ml-2" />
                                )}
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      
                      {/* Style Preview */}
                      {exportStyles[selectedExportStyle] && (
                        <div className="mt-2 text-xs text-gray-600">
                          <p>📋 {exportStyles[selectedExportStyle].description}</p>
                          {exportStyles[selectedExportStyle].pro_only && !isPro && (
                            <p className="text-orange-600 mt-1">
                              ⚠️ Ce style nécessite un compte Pro
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Export Status Info */}
                  {quotaLoaded && (
                    <div className="text-center text-sm text-gray-600">
                      {isPro ? (
                        <p className="text-blue-600">
                          👑 Compte Pro - Exports illimités
                        </p>
                      ) : quotaStatus.quota_exceeded ? (
                        <div>
                          <p className="text-orange-600 mb-2">
                            ⚠️ Quota dépassé - 
                            <Button 
                              variant="link" 
                              className="p-0 h-auto text-orange-600 underline ml-1"
                              onClick={() => setShowPaymentModal(true)}
                            >
                              Passer à Pro
                            </Button>
                          </p>
                          {userEmail && (
                            <Button 
                              variant="outline" 
                              size="sm" 
                              onClick={() => checkProStatus(userEmail)}
                              className="text-xs"
                            >
                              Vérifier mon statut Pro
                            </Button>
                          )}
                        </div>
                      ) : (
                        <p>
                          📄 Exports restants : {quotaStatus.exports_remaining}
                        </p>
                      )}
                    </div>
                  )}

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
                            <div className="text-gray-900 whitespace-pre-wrap" dangerouslySetInnerHTML={{ __html: exercise.enonce }}></div>
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
                                  <span className="ml-2 text-gray-900" dangerouslySetInnerHTML={{ __html: etape }}></span>
                                </div>
                              ))}
                              <div className="mt-3 p-2 bg-green-50 rounded">
                                <strong className="text-green-800">Résultat :</strong> 
                                <span className="ml-2 text-green-900" dangerouslySetInnerHTML={{ __html: exercise.solution.resultat }}></span>
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

        {/* Payment Modal */}
        <Dialog open={showPaymentModal} onOpenChange={setShowPaymentModal}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center text-center">
                <Crown className="mr-2 h-6 w-6 text-yellow-600" />
                Passez à Le Maître Mot Pro
              </DialogTitle>
              <DialogDescription className="text-center">
                Débloquez les exports illimités et accédez à toutes les fonctionnalités
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-6">
              {/* Email Input */}
              <div className="space-y-2">
                <Label htmlFor="payment-email">Adresse email *</Label>
                <Input
                  id="payment-email"
                  type="email"
                  placeholder="votre@email.fr"
                  value={paymentEmail}
                  onChange={(e) => setPaymentEmail(e.target.value)}
                  required
                />
                <p className="text-xs text-gray-500">
                  Cette adresse sera utilisée pour gérer votre abonnement
                </p>
              </div>
              
              {/* Monthly Plan */}
              {pricing.monthly && (
                <Card className="border-2 border-blue-200 hover:border-blue-400 transition-colors cursor-pointer">
                  <CardContent className="p-6">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="text-lg font-bold text-gray-900">Abonnement Mensuel</h3>
                        <p className="text-sm text-gray-600">Parfait pour essayer</p>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-blue-600">{pricing.monthly.amount}€</div>
                        <div className="text-sm text-gray-500">par mois</div>
                      </div>
                    </div>
                    <ul className="space-y-2 mb-4 text-sm text-gray-700">
                      <li className="flex items-center">
                        <CheckCircle className="h-4 w-4 text-green-600 mr-2" />
                        Exports PDF illimités
                      </li>
                      <li className="flex items-center">
                        <CheckCircle className="h-4 w-4 text-green-600 mr-2" />
                        Génération d'exercices sans limite
                      </li>
                      <li className="flex items-center">
                        <CheckCircle className="h-4 w-4 text-green-600 mr-2" />
                        Toutes les matières et niveaux
                      </li>
                    </ul>
                    <Button 
                      onClick={() => handleUpgradeClick('monthly')}
                      disabled={!paymentEmail || paymentLoading}
                      className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                    >
                      {paymentLoading ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <CreditCard className="mr-2 h-4 w-4" />
                      )}
                      Choisir Mensuel
                    </Button>
                  </CardContent>
                </Card>
              )}

              {/* Yearly Plan */}
              {pricing.yearly && (
                <Card className="border-2 border-green-200 hover:border-green-400 transition-colors cursor-pointer relative">
                  <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                    <Badge className="bg-green-600 text-white px-3 py-1">Économisez 16%</Badge>
                  </div>
                  <CardContent className="p-6">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="text-lg font-bold text-gray-900">Abonnement Annuel</h3>
                        <p className="text-sm text-gray-600">Le meilleur rapport qualité/prix</p>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-green-600">{pricing.yearly.amount}€</div>
                        <div className="text-sm text-gray-500">par an</div>
                        <div className="text-xs text-green-600">Soit {(pricing.yearly.amount / 12).toFixed(2)}€/mois</div>
                      </div>
                    </div>
                    <ul className="space-y-2 mb-4 text-sm text-gray-700">
                      <li className="flex items-center">
                        <CheckCircle className="h-4 w-4 text-green-600 mr-2" />
                        Exports PDF illimités
                      </li>
                      <li className="flex items-center">
                        <CheckCircle className="h-4 w-4 text-green-600 mr-2" />
                        Génération d'exercices sans limite
                      </li>
                      <li className="flex items-center">
                        <CheckCircle className="h-4 w-4 text-green-600 mr-2" />
                        Toutes les matières et niveaux
                      </li>
                      <li className="flex items-center">
                        <CheckCircle className="h-4 w-4 text-green-600 mr-2" />
                        Économisez 20€ par rapport au mensuel
                      </li>
                    </ul>
                    <Button 
                      onClick={() => handleUpgradeClick('yearly')}
                      disabled={!paymentEmail || paymentLoading}
                      className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-50"
                    >
                      {paymentLoading ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <Crown className="mr-2 h-4 w-4" />
                      )}
                      Choisir Annuel
                    </Button>
                  </CardContent>
                </Card>
              )}

              <div className="text-center text-xs text-gray-500 mt-4">
                Paiement sécurisé par Stripe • Annulation possible à tout moment
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* Login Modal */}
        <Dialog open={showLoginModal} onOpenChange={(open) => {
          setShowLoginModal(open);
          if (!open) {
            setLoginEmail("");
            setLoginEmailSent(false);
            setLoginLoading(false);
          }
        }}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center text-center">
                <LogIn className="mr-2 h-6 w-6 text-blue-600" />
                Connexion Pro
              </DialogTitle>
              <DialogDescription className="text-center">
                {loginEmailSent 
                  ? "Vérifiez votre boîte email"
                  : "Entrez votre email pour recevoir un lien de connexion"
                }
              </DialogDescription>
            </DialogHeader>
            
            {!loginEmailSent ? (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="login-email">Adresse email de votre compte Pro</Label>
                  <Input
                    id="login-email"
                    type="email"
                    placeholder="votre@email.fr"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                  />
                </div>
                
                <Button 
                  onClick={() => requestLogin(loginEmail)}
                  disabled={!loginEmail || loginLoading}
                  className="w-full bg-blue-600 hover:bg-blue-700"
                >
                  {loginLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Envoi en cours...
                    </>
                  ) : (
                    <>
                      <Mail className="mr-2 h-4 w-4" />
                      Envoyer le lien de connexion
                    </>
                  )}
                </Button>
                
                <div className="text-center">
                  <p className="text-xs text-gray-500 mb-2">
                    Pas encore Pro ?
                  </p>
                  <Button 
                    variant="link" 
                    onClick={() => {
                      setShowLoginModal(false);
                      setShowPaymentModal(true);
                    }}
                    className="text-blue-600 p-0 h-auto"
                  >
                    Créer un compte Pro
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-4 text-center">
                <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
                  <Mail className="h-8 w-8 text-blue-600" />
                </div>
                
                <div>
                  <h3 className="font-semibold text-gray-900 mb-2">Email envoyé !</h3>
                  <p className="text-sm text-gray-600 mb-4">
                    Nous avons envoyé un lien de connexion à <strong>{loginEmail}</strong>
                  </p>
                  <div className="bg-blue-50 p-3 rounded-lg text-xs text-blue-700">
                    💡 <strong>Conseil :</strong> Vérifiez vos spams si vous ne recevez pas l'email dans les 2 minutes.
                  </div>
                </div>
                
                <Button 
                  variant="outline" 
                  onClick={() => {
                    setLoginEmailSent(false);
                    setLoginEmail("");
                  }}
                  className="w-full"
                >
                  Changer d'email
                </Button>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/success" element={<PaymentSuccess />} />
        <Route path="/cancel" element={<PaymentCancel />} />
        <Route path="/login/verify" element={<LoginVerify />} />
        <Route path="/*" element={<MainApp />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;