import { createContext, useContext, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CssBaseline, ThemeProvider } from '@mui/material'
import { buildTheme } from './theme'
import { AuthProvider } from './store/AuthContext'
import App from './App'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

// Contexte de bascule clair/sombre, persisté dans localStorage.
const ColorModeContext = createContext({ mode: 'dark', toggle: () => {} })
export const useColorMode = () => useContext(ColorModeContext)

function Root() {
  const [mode, setMode] = useState(() => localStorage.getItem('researchos_mode') || 'dark')
  const ctx = useMemo(
    () => ({
      mode,
      toggle: () =>
        setMode((m) => {
          const next = m === 'dark' ? 'light' : 'dark'
          localStorage.setItem('researchos_mode', next)
          return next
        }),
    }),
    [mode],
  )
  const theme = useMemo(() => buildTheme(mode), [mode])

  return (
    <ColorModeContext.Provider value={ctx}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <AuthProvider>
              <App />
            </AuthProvider>
          </BrowserRouter>
        </QueryClientProvider>
      </ThemeProvider>
    </ColorModeContext.Provider>
  )
}

createRoot(document.getElementById('root')).render(<Root />)
