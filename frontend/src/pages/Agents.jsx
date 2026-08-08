import { useEffect, useRef, useState } from 'react'
import {
  Box, Button, Card, CardActionArea, CardContent, Chip, Grid, MenuItem, Paper,
  Stack, TextField, Typography,
} from '@mui/material'
import { PlayArrow, Hub } from '@mui/icons-material'
import Page from '../components/Page'
import { TOKEN_KEY } from '../api/client'
import { useAgents, useModels } from '../hooks/useApi'
import { useRealtime } from '../store/RealtimeProvider'
import { getLang } from '../store/lang'

export default function Agents() {
  const { data } = useAgents()
  const { data: modelsData } = useModels()
  const { socket } = useRealtime()
  const [selected, setSelected] = useState(null)
  const [task, setTask] = useState('')
  const [pinned, setPinned] = useState('')
  const [result, setResult] = useState(null)     // { content, model, running, error }
  const t0 = useRef(0)

  const models = modelsData?.models || []

  // Streaming de la sortie de l'agent.
  useEffect(() => {
    if (!socket) return
    const onStart = (e) => setResult({ content: '', model: e.model, running: true })
    const onToken = (e) => setResult((r) => ({ ...r, content: (r?.content || '') + e.text }))
    const onDone = () => setResult((r) => ({ ...r, running: false, ms: Math.round(performance.now() - t0.current) }))
    const onErr = (e) => setResult({ error: e.message, running: false })
    socket.on('agent_start', onStart)
    socket.on('agent_token', onToken)
    socket.on('agent_done', onDone)
    socket.on('agent_error', onErr)
    return () => {
      socket.off('agent_start', onStart); socket.off('agent_token', onToken)
      socket.off('agent_done', onDone); socket.off('agent_error', onErr)
    }
  }, [socket])

  const launch = () => {
    if (!selected || !task.trim() || !socket) return
    setResult({ content: '', running: true })
    t0.current = performance.now()
    socket.emit('agent_stream', {
      token: localStorage.getItem(TOKEN_KEY),
      agent: selected.name, task, pinned_model: pinned || undefined, lang: getLang(),
    })
  }

  return (
    <Page title="Agents" subtitle="14 agents spécialisés — exécution en streaming">
      <Grid container spacing={2.5}>
        <Grid item xs={12} md={5}>
          <Grid container spacing={1.5}>
            {(data?.agents || []).map((a) => (
              <Grid item xs={6} key={a.name}>
                <Card sx={{ borderColor: selected?.name === a.name ? 'primary.main' : 'divider' }}>
                  <CardActionArea onClick={() => setSelected(a)} sx={{ p: 0.5 }}>
                    <CardContent>
                      <Stack direction="row" gap={1} alignItems="center" mb={0.5}>
                        <Hub fontSize="small" color="primary" />
                        <Typography fontWeight={600} textTransform="capitalize">{a.name.replace('_', ' ')}</Typography>
                      </Stack>
                      <Typography variant="caption" color="text.secondary">{a.description}</Typography>
                      <Box mt={1}><Chip size="small" variant="outlined" label={a.strategy} /></Box>
                    </CardContent>
                  </CardActionArea>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Grid>

        <Grid item xs={12} md={7}>
          <Card sx={{ position: 'sticky', top: 88 }}>
            <CardContent>
              <Typography variant="h6" mb={2}>
                {selected ? `Agent : ${selected.name}` : 'Sélectionnez un agent'}
              </Typography>
              <Stack gap={2}>
                <TextField label="Tâche" multiline minRows={2} maxRows={14} value={task}
                  onChange={(e) => setTask(e.target.value)} disabled={!selected}
                  placeholder="Décrivez la tâche à confier à l'agent…" />
                <Stack direction="row" gap={1}>
                  <TextField select size="small" label="Modèle" value={pinned}
                    onChange={(e) => setPinned(e.target.value)} sx={{ minWidth: 170 }}
                    SelectProps={{ displayEmpty: true }}>
                    <MenuItem value=""><em>Auto ({selected?.strategy || 'stratégie'})</em></MenuItem>
                    {models.map((m) => (
                      <MenuItem key={m.id} value={m.id}>{m.id}{m.input_cost === 0 ? ' ⚡' : ''}</MenuItem>
                    ))}
                  </TextField>
                  <Button variant="contained" startIcon={<PlayArrow />} onClick={launch}
                    disabled={!selected || result?.running || !socket}>
                    Exécuter
                  </Button>
                </Stack>

                {result?.running && !result.content && (
                  <Typography color="text.secondary">Génération…</Typography>
                )}
                {result?.error && <Typography color="error.main">{result.error}</Typography>}
                {(result?.content || (result?.running && result.content === '')) && !result.error && (
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Stack direction="row" gap={0.5} mb={1}>
                      {result.model && <Chip size="small" label={result.model} variant="outlined" />}
                      {result.ms != null && <Chip size="small" label={`${result.ms} ms`} variant="outlined" />}
                      {result.running && <Chip size="small" color="warning" label="en cours…" />}
                    </Stack>
                    <Typography variant="body2" whiteSpace="pre-wrap">
                      {result.content || '…'}
                    </Typography>
                  </Paper>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Page>
  )
}
