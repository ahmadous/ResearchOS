import { useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Chip, Divider, IconButton, LinearProgress,
  Link, List, ListItem, ListItemText, Stack, TextField, Typography, CircularProgress,
} from '@mui/material'
import {
  Mail as MailIcon, AutoAwesome, Delete, Refresh, LinkOff, FiberManualRecord,
} from '@mui/icons-material'
import Page from '../components/Page'
import { errMsg } from '../api/client'
import {
  useMailAccount, useConnectMail, useDeleteMail, useInbox, useTriage,
} from '../hooks/useApi'

const impColor = (i) => (i >= 70 ? 'error' : i >= 40 ? 'warning' : 'default')

export default function Mail() {
  const { data: accData } = useMailAccount()
  const connect = useConnectMail()
  const disconnect = useDeleteMail()
  const triage = useTriage()
  const account = accData?.account
  const { data: inboxData, refetch, isFetching, error: inboxError } = useInbox(!!account)

  const [form, setForm] = useState({ email: '', password: '', imap_host: 'imap.gmail.com' })
  const [error, setError] = useState('')
  const [sorted, setSorted] = useState(null)   // résultat du tri IA

  const emails = sorted || inboxData?.emails || []

  const doConnect = async () => {
    setError('')
    try { await connect.mutateAsync(form) } catch (e) { setError(errMsg(e)) }
  }
  const doTriage = async () => {
    setError('')
    try {
      const r = await triage.mutateAsync({ emails: inboxData?.emails || [] })
      setSorted(r.emails)
    } catch (e) { setError(errMsg(e)) }
  }

  // --- Écran de connexion ---
  if (!account) {
    return (
      <Page title="Mail" subtitle="Connectez votre boîte (IMAP, lecture seule) pour trier vos mails avec l'IA">
        <Card sx={{ maxWidth: 560 }}>
          <CardContent>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            <Alert severity="info" sx={{ mb: 2 }}>
              Pour Gmail : activez la validation en 2 étapes, puis créez un
              <b> mot de passe d'application</b> (Compte Google → Sécurité → Mots de passe
              des applications) et collez-le ci-dessous. L'accès est en <b>lecture seule</b> —
              aucun mail n'est envoyé, le mot de passe est <b>chiffré</b>.
            </Alert>
            <Stack gap={2}>
              <TextField label="Adresse email" type="email" value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })} />
              <TextField label="Mot de passe d'application" type="password" value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })} />
              <TextField label="Serveur IMAP" value={form.imap_host}
                onChange={(e) => setForm({ ...form, imap_host: e.target.value })}
                helperText="Gmail : imap.gmail.com · Outlook : outlook.office365.com" />
              <Button variant="contained" startIcon={connect.isPending ? <CircularProgress size={16} /> : <MailIcon />}
                onClick={doConnect} disabled={connect.isPending || !form.email || !form.password}>
                Connecter
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Page>
    )
  }

  // --- Boîte de réception ---
  return (
    <Page
      title="Mail"
      subtitle={`${account.email} · lecture seule`}
      action={
        <Stack direction="row" gap={1}>
          <Button variant="contained"
            startIcon={triage.isPending ? <CircularProgress size={16} color="inherit" /> : <AutoAwesome />}
            onClick={doTriage} disabled={triage.isPending || !emails.length}>
            Trier avec l'IA
          </Button>
          <IconButton onClick={() => { setSorted(null); refetch() }} title="Rafraîchir"><Refresh /></IconButton>
          <IconButton onClick={() => disconnect.mutate()} title="Déconnecter" color="error"><LinkOff /></IconButton>
        </Stack>
      }
    >
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
      {inboxError && <Alert severity="warning" sx={{ mb: 2 }}>{errMsg(inboxError)}</Alert>}
      {(isFetching || triage.isPending) && <LinearProgress sx={{ mb: 2 }} />}
      {sorted && <Alert severity="success" sx={{ mb: 2 }}>Trié par importance · les mails « à répondre » sont signalés.</Alert>}

      <Card>
        <CardContent sx={{ p: 0 }}>
          <List disablePadding>
            {emails.map((e, i) => (
              <Box key={e.uid || i}>
                <ListItem alignItems="flex-start" sx={{ py: 1.2 }}>
                  <Box sx={{ mr: 1.5, mt: 0.5 }}>
                    {e.unread ? <FiberManualRecord color="primary" sx={{ fontSize: 12 }} />
                              : <FiberManualRecord sx={{ fontSize: 12, color: 'transparent' }} />}
                  </Box>
                  <ListItemText
                    primary={
                      <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">
                        <Typography variant="body2" fontWeight={e.unread ? 700 : 500} noWrap sx={{ maxWidth: 460 }}>
                          {e.subject || '(sans objet)'}
                        </Typography>
                        {e.importance != null && (
                          <Chip size="small" color={impColor(e.importance)} label={`${e.importance}`} />
                        )}
                        {e.needs_reply && <Chip size="small" color="warning" variant="outlined" label="à répondre" />}
                        {e.category && <Chip size="small" variant="outlined" label={e.category} />}
                      </Stack>
                    }
                    secondary={
                      <>
                        <Typography variant="caption" color="text.secondary">
                          {e.from}{e.date ? ` · ${new Date(e.date).toLocaleString()}` : ''}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" display="block"
                          sx={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                          {e.summary || e.snippet}
                        </Typography>
                      </>
                    }
                  />
                </ListItem>
                {i < emails.length - 1 && <Divider component="li" />}
              </Box>
            ))}
            {emails.length === 0 && !isFetching && (
              <Typography color="text.secondary" sx={{ p: 3, textAlign: 'center' }}>
                Boîte vide ou inaccessible.
              </Typography>
            )}
          </List>
        </CardContent>
      </Card>
    </Page>
  )
}
