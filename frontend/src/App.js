import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Welcome from './pages/Welcome';
import Training from './pages/Training';
import IMessagePage from './pages/IMessagePage';
import GmailPage from './pages/GmailPage';
import AutoResponsePage from './pages/AutoResponsePage';
import HowItWorks from './pages/HowItWorks';
import PrivacyPolicy from './pages/PrivacyPolicy';
import TermsOfService from './pages/TermsOfService';
import DownloadApp from './pages/DownloadApp';
import AccountPage from './pages/AccountPage';
import Login from './components/Login';
import Signup from './components/Signup';
import AuthCallback from './components/AuthCallback';
import ProtectedRoute from './components/ProtectedRoute';
import { AuthProvider } from './contexts/AuthContext';
import { PlatformProvider, usePlatform } from './contexts/PlatformContext';
import LandingPage from './pages/LandingPage';

const theme = createTheme({
  palette: {
    primary: {
      main: '#2196f3',
    },
    secondary: {
      main: '#f50057',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 500,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 500,
    },
    h3: {
      fontSize: '1.5rem',
      fontWeight: 500,
    },
  },
});

// Component to handle platform-specific routes
const PlatformRoutes = () => {
  const { isElectron, isWeb } = usePlatform();
  
  // Web-only dashboard component
  const WebDashboard = () => (
    <>
      <Navbar webOnly={true} />
      <div style={{ padding: '2rem' }}>
        <h1>Web Dashboard</h1>
        <p>This content is only visible on the web version.</p>
        <p>Here you can display account information, subscription details, or web-specific features.</p>
        <p>Download the desktop app for full functionality including training, chat, and iMessage integration.</p>
      </div>
      <Footer />
    </>
  );

  return (
    <Routes>
      {/* Public routes - same for both platforms */}
      <Route path="/" element={<><LandingPage /><Footer /></>} />
      <Route path="/login" element={<><Login /><Footer /></>} />
      <Route path="/signup" element={<><Signup /><Footer /></>} />
      <Route path="/auth-callback" element={<><AuthCallback /><Footer /></>} />
      <Route path="/privacy-policy" element={<><PrivacyPolicy /><Footer /></>} />
      <Route path="/terms-of-service" element={<><TermsOfService /><Footer /></>} />
      <Route path="/download" element={<><Navbar /><DownloadApp /><Footer /></>} />
      
      {/* Protected routes with platform-specific behavior */}
      {isWeb ? (
        // Web-specific routes
        <>
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <WebDashboard />
            </ProtectedRoute>
          } />
          <Route path="/account" element={
            <ProtectedRoute>
              <Navbar webOnly={true} />
              <AccountPage />
              <Footer />
            </ProtectedRoute>
          } />
        </>
      ) : (
        // Desktop-specific routes
        <>
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <Navbar />
              <Welcome />
              <Footer />
            </ProtectedRoute>
          } />
          <Route path="/training" element={
            <ProtectedRoute>
              <Navbar />
              <Training />
              <Footer />
            </ProtectedRoute>
          } />
          {/* Chat route removed */}
          <Route path="/imessage" element={
            <ProtectedRoute>
              <Navbar />
              <IMessagePage />
              <Footer />
            </ProtectedRoute>
          } />
          <Route path="/auto-response" element={
            <ProtectedRoute>
              <Navbar />
              <AutoResponsePage />
              <Footer />
            </ProtectedRoute>
          } />
          <Route path="/how-it-works" element={
            <ProtectedRoute>
              <Navbar />
              <HowItWorks />
              <Footer />
            </ProtectedRoute>
          } />
        </>
      )}
    </Routes>
  );
};

function App() {
  return (
    <AuthProvider>
      <PlatformProvider>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <PlatformRoutes />
        </ThemeProvider>
      </PlatformProvider>
    </AuthProvider>
  );
}

export default App;
