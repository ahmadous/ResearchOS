import { useState } from 'react'
import {
  Box, Button, Card, CardActionArea, CardContent, Chip, Grid, Paper, Stack,
  TextField, Typography,
} from '@mui/material'
import { PlayArrow, Hub } from '@mui/icons-material'
import Page from '../components/Page'
import { errMsg } from '../api/client'
import { useAgents, useRunAgent } from '../hooks/useApi'

export default function Agents() {
  const { data } = useAgents()
  const run = useRunAgent()
  const [selected, setSelected] = useState(null)
  const [task, setTask] = useState('')
  const [result, setResult] = useState(null)

  const launch = async () => {
    if (!selected || !task.trim()) return
    setResult({ loading: true })
    try {
      const r = await run.mutateAsync({ name: selected.name, task })
      setResult(r)
    } catch (e) {
      setResult({ error: errMsg(e) })
    }
  }

  return (
    <Page title="Agents" subtitle="14 agents spécialisés, orchestrés sur le routeur local">
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
                <TextField
                  label="Tâche" multiline minRows={3} value={task}
                  onChange={(e) => setTask(e.target.value)} disabled={!selected}
                  placeholder="Décrivez la tâche à confier à l'agent…"
                />
                <Button variant="contained" startIcon={<PlayArrow />} onClick={launch}
                  disabled={!selected || run.isPending}>
                  Exécuter
                </Button>
                {result?.loading && <Typography color="text.secondary">Exécution…</Typography>}
                {result?.error && <Typography color="error.main">{result.error}</Typography>}
                {result?.content && (
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Stack direction="row" gap={0.5} mb={1}>
                      <Chip size="small" label={result.model} variant="outlined" />
                      <Chip size="small" label={`${result.total_tokens} tokens`} variant="outlined" />
                    </Stack>
                    <Typography variant="body2" whiteSpace="pre-wrap">{result.content}</Typography>
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
