import { useEffect, useRef, useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Chip, Divider, LinearProgress, List,
  ListItemButton, ListItemText, MenuItem, Paper, Stack, TextField, Typography,
} from '@mui/material'
import { AutoAwesome, Download, Article } from '@mui/icons-material'
import Page from '../components/Page'
import { TOKEN_KEY, errMsg } from '../api/client'
import { useReports, useGenerateReport, downloadReportPdf, useModels } from '../hooks/useApi'
import { useRealtime } from '../store/RealtimeProvider'
import { useQueryClient } from '@tanstack/react-query'

export default function Reports() {
  const { data: reportsData } = useReports()
  const { data: modelsData } = useModels()
  const generate = useGenerateReport()
  const { socket } = useRealtime()
  const qc = useQueryClient()

  const [query, setQuery] = useState('')
  const [pinned, setPinned] = useState('')
  const [taskId, setTaskId] = useState(null)
  const [progress, setProgress] = useState(null)   // { pct, message }
  const [current, setCurrent] = useState(null)      // rapport affiché
  const [error, setError] = useState('')
  const taskRef = useRef(null)

  const reports = reportsData?.reports || []
  const models = modelsData?.models || []

  // Suivi de la génération (progression + résultat) via WebSocket.
  useEffect(() => {
    if (!socket) return
    const onProg = (e) => { if (e.task_id === taskRef.current) setProgress({ pct: e.progress, message: e.message }) }
    const onDone = (e) => {
      if (e.task_id !== taskRef.current) return
      setProgress(null); setTaskId(null); taskRef.current = null
      if (e.result) setCurrent(e.result)
      qc.invalidateQueries({ queryKey: ['reports'] })
    }
    const onFail = (e) => {
      if (e.task_id !== taskRef.current) return
      setProgress(null); setTaskId(null); taskRef.current = null
      setError(e.error || 'Échec de la génération')
    }
    socket.on('task_progress', onProg)
    socket.on('task_completed', onDone)
    socket.on('task_failed', onFail)
    return () => { socket.off('task_progress', onProg); socket.off('task_completed', onDone); socket.off('task_failed', onFail) }
  }, [socket]) // eslint-disable-line

  const run = async () => {
    if (query.trim().length < 3) return
    setError(''); setCurrent(null); setProgress({ pct: 5, message: 'démarrage…' })
    try {
      const task = await generate.mutateAsync({ query, pinned_model: pinned || undefined })
      setTaskId(task.id); taskRef.current = task.id
    } catch (e) { setError(errMsg(e)); setProgress(null) }
  }

  const open = async (id) => {
    const { api } = await import('../api/client')
    setCurrent((await api.get(`/reports/${id}`)).data)
  }

  return (
    <Page
      title="Rapports"
      subtitle="Recherche d'articles réelle → état de l'art → PDF"
      action={
        <Stack direction="row" gap={1}>
          <TextField select size="small" value={pinned} onChange={(e) => setPinned(e.target.value)}
            sx={{ minWidth: 150 }} SelectProps={{ displayEmpty: true }}>
            <MenuItem value=""><em>Auto (qualité)</em></MenuItem>
            {models.map((m) => <MenuItem key={m.id} value={m.id}>{m.id}{m.input_cost === 0 ? ' ⚡' : ''}</MenuItem>)}
          </TextField>
        </Stack>
      }
    >
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Stack direction={{ xs: 'column', sm: 'row' }} gap={1}>
            <TextField fullWidth size="small" placeholder="Sujet de recherche (ex : détection d'inondations par satellite au Sénégal)"
              value={query} onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && run()} disabled={!!taskId} />
            <Button variant="contained" startIcon={<AutoAwesome />} onClick={run}
              disabled={!!taskId || query.trim().length < 3}>Générer</Button>
          </Stack>
          {progress && (
            <Box mt={2}>
              <Stack direction="row" justifyContent="space-between" mb={0.5}>
                <Typography variant="caption" color="text.secondary">{progress.message}</Typography>
                <Typography variant="caption" color="text.secondary">{progress.pct}%</Typography>
              </Stack>
              <LinearProgress variant="determinate" value={progress.pct} />
            </Box>
          )}
        </CardContent>
      </Card>

      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2.5} alignItems="flex-start">
        {/* Rapport courant */}
        <Card sx={{ flex: 1, width: '100%' }}>
          <CardContent>
            {!current ? (
              <Stack alignItems="center" justifyContent="center" minHeight={200}>
                <Article color="disabled" />
                <Typography color="text.secondary" mt={1}>
                  Lancez une génération ou ouvrez un rapport existant.
                </Typography>
              </Stack>
            ) : (
              <>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1}>
                  <Typography variant="h6">{current.title}</Typography>
                  <Button variant="outlined" size="small" startIcon={<Download />}
                    onClick={() => downloadReportPdf(current.id)}>PDF</Button>
                </Stack>
                <Chip size="small" sx={{ my: 1 }} label={`${current.n_sources} sources`} />
                <Typography variant="body2" whiteSpace="pre-wrap" mt={1}>{current.content}</Typography>
                {current.references?.length > 0 && (
                  <>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="subtitle2" mb={1}>Références</Typography>
                    <Stack gap={0.5}>
                      {current.references.map((r, i) => (
                        <Typography key={i} variant="caption" color="text.secondary">
                          [{i + 1}] {(r.authors || []).slice(0, 3).join(', ')} — {r.title} ({r.year || 's.d.'})
                        </Typography>
                      ))}
                    </Stack>
                  </>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* Historique */}
        <Card sx={{ width: { xs: '100%', md: 300 }, flexShrink: 0 }}>
          <CardContent>
            <Typography variant="subtitle2" mb={1}>Rapports ({reports.length})</Typography>
            <List dense>
              {reports.map((r) => (
                <ListItemButton key={r.id} onClick={() => open(r.id)}
                  secondaryAction={<Button size="small" startIcon={<Download />}
                    onClick={(e) => { e.stopPropagation(); downloadReportPdf(r.id) }}>PDF</Button>}>
                  <ListItemText primary={r.query} secondary={`${r.n_sources} sources`}
                    primaryTypographyProps={{ noWrap: true, fontSize: 13 }} />
                </ListItemButton>
              ))}
              {reports.length === 0 && <Typography variant="caption" color="text.secondary">Aucun rapport.</Typography>}
            </List>
          </CardContent>
        </Card>
      </Stack>
    </Page>
  )
}
