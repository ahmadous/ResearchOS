import { useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Chip, IconButton, InputAdornment,
  MenuItem, Paper, Stack, TextField, ToggleButton, ToggleButtonGroup, Typography,
} from '@mui/material'
import { Add, DeleteOutline, Search, Psychology } from '@mui/icons-material'
import Page from '../components/Page'
import { errMsg } from '../api/client'
import { useMemories, useAddMemory, useDeleteMemory, useRecallMemory } from '../hooks/useApi'

const SCOPE_COLOR = { user: 'primary', project: 'secondary', agent: 'warning', global: 'success' }
const SCOPES = ['', 'user', 'project', 'agent', 'global']

export default function Memory() {
  const [scopeFilter, setScopeFilter] = useState('')
  const { data } = useMemories(scopeFilter || undefined)
  const add = useAddMemory()
  const del = useDeleteMemory()
  const recall = useRecallMemory()

  const [form, setForm] = useState({ content: '', scope: 'user', project: '' })
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState(null)
  const [error, setError] = useState('')

  const memories = data?.memories || []

  const doAdd = async () => {
    setError('')
    try {
      await add.mutateAsync({
        content: form.content, scope: form.scope,
        project: form.scope === 'project' ? form.project || 'default' : undefined,
      })
      setForm({ content: '', scope: 'user', project: '' })
    } catch (e) { setError(errMsg(e)) }
  }
  const doRecall = async () => {
    if (query.trim().length < 2) return
    setHits(await recall.mutateAsync({ query }))
  }

  const Item = ({ m, score }) => (
    <Paper variant="outlined" sx={{ p: 1.5 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1}>
        <Box>
          <Typography variant="body2">{m.content}</Typography>
          <Stack direction="row" gap={0.5} mt={0.5} flexWrap="wrap">
            <Chip size="small" color={SCOPE_COLOR[m.scope]} label={m.scope} />
            {m.project && <Chip size="small" variant="outlined" label={m.project} />}
            {score != null && <Chip size="small" variant="outlined" label={`score ${score}`} />}
          </Stack>
        </Box>
        <IconButton size="small" onClick={() => del.mutate(m.id)}><DeleteOutline fontSize="small" /></IconButton>
      </Stack>
    </Paper>
  )

  return (
    <Page title="Mémoire" subtitle="Ce que l'assistant retient entre vos sessions">
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2.5} alignItems="flex-start">
        {/* Ajout + recherche */}
        <Card sx={{ width: { xs: '100%', md: 380 }, flexShrink: 0 }}>
          <CardContent>
            <Typography variant="h6" mb={2}>Mémoriser un fait</Typography>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            <Stack gap={1.5}>
              <TextField label="Contenu" multiline minRows={2} value={form.content}
                onChange={(e) => setForm({ ...form, content: e.target.value })} />
              <Stack direction="row" gap={1}>
                <TextField select size="small" label="Portée" value={form.scope}
                  onChange={(e) => setForm({ ...form, scope: e.target.value })} sx={{ minWidth: 120 }}>
                  {['user', 'project', 'agent', 'global'].map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
                </TextField>
                {form.scope === 'project' && (
                  <TextField size="small" label="Projet" value={form.project}
                    onChange={(e) => setForm({ ...form, project: e.target.value })} fullWidth />
                )}
              </Stack>
              <Button variant="contained" startIcon={<Add />} onClick={doAdd}
                disabled={add.isPending || !form.content}>Mémoriser</Button>
            </Stack>

            <Typography variant="h6" mt={3} mb={1}>Rappel sémantique</Typography>
            <Stack direction="row" gap={1}>
              <TextField fullWidth size="small" placeholder="Que dois-je me rappeler à propos de… ?"
                value={query} onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && doRecall()}
                InputProps={{ startAdornment: <InputAdornment position="start"><Search /></InputAdornment> }} />
              <Button variant="contained" onClick={doRecall} disabled={recall.isPending}>OK</Button>
            </Stack>
            {hits && (
              <Stack gap={1} mt={1.5}>
                {hits.results.length === 0 && <Typography variant="caption" color="text.secondary">Aucun souvenir pertinent.</Typography>}
                {hits.results.map((m) => <Item key={m.id} m={m} score={m.score} />)}
              </Stack>
            )}
          </CardContent>
        </Card>

        {/* Liste */}
        <Card sx={{ flex: 1, width: '100%' }}>
          <CardContent>
            <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
              <Stack direction="row" gap={1} alignItems="center">
                <Psychology color="primary" />
                <Typography variant="h6">Souvenirs ({memories.length})</Typography>
              </Stack>
              <ToggleButtonGroup size="small" exclusive value={scopeFilter}
                onChange={(_, v) => setScopeFilter(v ?? '')}>
                {SCOPES.map((s) => <ToggleButton key={s || 'all'} value={s}>{s || 'tous'}</ToggleButton>)}
              </ToggleButtonGroup>
            </Stack>
            {memories.length === 0 ? (
              <Typography color="text.secondary">Rien en mémoire pour l'instant.</Typography>
            ) : (
              <Stack gap={1}>{memories.map((m) => <Item key={m.id} m={m} />)}</Stack>
            )}
          </CardContent>
        </Card>
      </Stack>
    </Page>
  )
}
