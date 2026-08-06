import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { Box, CircularProgress } from '@mui/material'
import { useAuth } from './store/AuthContext'
import AppLayout from './layouts/AppLayout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import LLMManager from './pages/LLMManager'
import Chat from './pages/Chat'
import Agents from './pages/Agents'
import Documents from './pages/Documents'
import Scholar from './pages/Scholar'
import WorkflowBuilder from './pages/WorkflowBuilder'
import KnowledgeGraph from './pages/KnowledgeGraph'

function Protected({ children }) {
  const { token, loading } = useAuth()
  if (loading)
    return (
      <Box sx={{ display: 'grid', placeItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    )
  return token ? children : <Navigate to="/login" replace />
}

export default function App() {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <Protected>
              <AppLayout />
            </Protected>
          }
        >
          <Route path="/" element={<Dashboard />} />
          <Route path="/llm" element={<LLMManager />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/workflows" element={<WorkflowBuilder />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/graph" element={<KnowledgeGraph />} />
          <Route path="/scholar" element={<Scholar />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  )
}
