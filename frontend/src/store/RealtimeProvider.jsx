import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { io } from 'socket.io-client'
import { Alert, Snackbar } from '@mui/material'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from './AuthContext'
import { TOKEN_KEY } from '../api/client'

// Connexion Socket.IO : rejoint la room privée de l'utilisateur et transforme
// les événements de tâches en toasts + invalidations de cache React Query.
const RealtimeContext = createContext({ connected: false, lastEvent: null })
export const useRealtime = () => useContext(RealtimeContext)

export function RealtimeProvider({ children }) {
  const { token } = useAuth()
  const qc = useQueryClient()
  const socketRef = useRef(null)
  const [connected, setConnected] = useState(false)
  const [lastEvent, setLastEvent] = useState(null)
  const [socket, setSocket] = useState(null)
  const [snack, setSnack] = useState(null)

  useEffect(() => {
    if (!token) return
    const socket = io('/', { path: '/socket.io', transports: ['websocket', 'polling'] })
    socketRef.current = socket
    setSocket(socket)

    socket.on('connect', () => {
      setConnected(true)
      socket.emit('join', { token: localStorage.getItem(TOKEN_KEY) })
    })
    socket.on('disconnect', () => setConnected(false))

    socket.on('task_started', (e) => setLastEvent({ type: 'started', ...e }))
    socket.on('task_progress', (e) => setLastEvent({ type: 'progress', ...e }))
    socket.on('task_completed', (e) => {
      setLastEvent({ type: 'completed', ...e })
      setSnack({ severity: 'success', msg: 'Tâche terminée ✓' })
      qc.invalidateQueries() // rafraîchit documents/conso/etc.
    })
    socket.on('task_failed', (e) => {
      setLastEvent({ type: 'failed', ...e })
      setSnack({ severity: 'error', msg: `Tâche échouée : ${e.error || ''}` })
    })
    socket.on('notification', (e) =>
      setSnack({ severity: e.level || 'info', msg: e.title }))

    return () => { socket.close(); setSocket(null) }
  }, [token]) // eslint-disable-line

  return (
    <RealtimeContext.Provider value={{ connected, lastEvent, socket }}>
      {children}
      <Snackbar
        open={!!snack}
        autoHideDuration={4000}
        onClose={() => setSnack(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        {snack ? (
          <Alert severity={snack.severity} variant="filled" onClose={() => setSnack(null)}>
            {snack.msg}
          </Alert>
        ) : undefined}
      </Snackbar>
    </RealtimeContext.Provider>
  )
}
