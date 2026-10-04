import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { LoadingState } from './components/common/ui';
import Landing from './pages/Landing';
import { Login, Register } from './pages/Auth';
import Cases from './pages/Cases';
import EvidenceDetail from './pages/EvidenceDetail';
import { SettingsPage, HelpPage } from './pages/UtilityPages';
import { AnalysisPage, CaseLayout, CorrelationPage, CustodyPage, Overview, ReportsPage, SearchPage, TimelinePage, Vault } from './pages/CasePages';
import type { ReactNode } from 'react';

function Protected({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth(); const loc = useLocation();
  if (loading) return <LoadingState label="RESTORING SESSION…" />;
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname }} replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/cases" element={<Protected><Cases /></Protected>} />
      <Route path="/cases/:caseId" element={<Protected><CaseLayout /></Protected>}>
        <Route index element={<Navigate to="overview" replace />} />
        <Route path="overview" element={<Overview />} />
        <Route path="evidence" element={<Vault />} />
        <Route path="analysis" element={<AnalysisPage />} />
        <Route path="timeline" element={<TimelinePage />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="correlation" element={<CorrelationPage />} />
        <Route path="custody" element={<CustodyPage />} />
        <Route path="reports" element={<ReportsPage />} />
      </Route>
      <Route path="/evidence/:evidenceId" element={<Protected><EvidenceDetail /></Protected>} />
      <Route path="/settings" element={<Protected><SettingsPage /></Protected>} />
      <Route path="/help" element={<Protected><HelpPage /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
