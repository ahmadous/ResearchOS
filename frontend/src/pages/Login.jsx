import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Alert, Box, Button, Card, CardContent, Link, Stack, TextField, Typography,
} from '@mui/material'
import Logo from '../components/Logo'
import { useAuth } from '../store/AuthContext'
import { errMsg } from '../api/client'

export default function Login() {
  const { token, login, register } = useAuth()
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ email: '', password: '', full_name: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (token) return <Navigate to="/" replace />

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (mode === 'login') await login(form.email, form.password)
      else await register(form)
    } catch (err) {
      setError(errMsg(err))
    } finally {
      setBusy(false)
    }
  }

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  return (
    <Box sx={{ display: 'grid', placeItems: 'center', minHeight: '100vh', p: 2, bgcolor: 'background.default' }}>
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <Card variant="outlined" sx={{ width: 400, maxWidth: '92vw' }}>
          <CardContent sx={{ p: 4 }}>
            <Stack alignItems="center" gap={1} mb={3}>
              <Logo size={56} />
              <Typography variant="h5" fontWeight={800} sx={{ letterSpacing: '-0.02em' }}>
                Research<Box component="span" sx={{
                  background: 'linear-gradient(90deg,#4f46e5,#7c3aed)',
                  WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                }}>OS</Box>
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {mode === 'login' ? 'Connectez-vous à votre espace' : 'Créez votre compte'}
              </Typography>
            </Stack>

            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

            <form onSubmit={submit}>
              <Stack gap={2}>
                {mode === 'register' && (
                  <TextField label="Nom complet" value={form.full_name} onChange={set('full_name')} fullWidth />
                )}
                <TextField label="Email" type="email" required value={form.email} onChange={set('email')} fullWidth />
                <TextField label="Mot de passe" type="password" required value={form.password} onChange={set('password')} fullWidth
                  helperText={mode === 'register' ? '8 caractères minimum' : ' '} />
                <Button type="submit" variant="contained" size="large" disabled={busy}>
                  {busy ? '...' : mode === 'login' ? 'Se connecter' : "S'inscrire"}
                </Button>
              </Stack>
            </form>

            <Typography variant="body2" align="center" mt={2} color="text.secondary">
              {mode === 'login' ? 'Pas encore de compte ? ' : 'Déjà inscrit ? '}
              <Link component="button" type="button" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}>
                {mode === 'login' ? 'Créer un compte' : 'Se connecter'}
              </Link>
            </Typography>
          </CardContent>
        </Card>
      </motion.div>
    </Box>
  )
}
