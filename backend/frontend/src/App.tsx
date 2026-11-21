import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { AuthPage } from './pages/AuthPage'
import { LandingPage } from './pages/LandingPage'
import { DashboardPage } from './pages/DashboardPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { SkillGapPage } from './pages/SkillGapPage'
import { InterviewPrepPage } from './pages/InterviewPrepPage'
import { ResumeAnalyzerPage } from './pages/ResumeAnalyzerPage'
import { JobMatchingPage } from './pages/JobMatchingPage'
import { ProfileSettingsPage } from './pages/ProfileSettingsPage'
import { RecruiterDashboardPage } from './pages/RecruiterDashboardPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/register" element={<AuthPage mode="register" />} />
      <Route element={<AppLayout />}>
        <Route path="/dashboard" element={sessionStorage.getItem('careerlens_role') === 'RECRUITER' ? <RecruiterDashboardPage /> : <DashboardPage />} />
        <Route path="/app" element={<Navigate to="/dashboard" replace />} />
        <Route element={<CandidateOnly />}>
          <Route path="/resume-analyzer" element={<ResumeAnalyzerPage />} />
          <Route path="/job-matching" element={<JobMatchingPage />} />
          <Route path="/skill-gaps" element={<SkillGapPage />} />
          <Route path="/interview-prep" element={<InterviewPrepPage />} />
          <Route path="/profile-settings" element={<ProfileSettingsPage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

function CandidateOnly() {
  return sessionStorage.getItem('careerlens_role') === 'CANDIDATE'
    ? <Outlet />
    : <Navigate to="/dashboard" replace />
}

export default App
