import { useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent,
  DialogTitle, Grid, IconButton, MenuItem, Stack, Table, TableBody, TableCell,
  TableHead, TableRow, TextField, Tooltip, Typography, LinearProgress,
} from '@mui/material'
import { Add, Delete, PlayArrow, CheckCircle, Cloud, Computer, Refresh, Circle } from '@mui/icons-material'
import Page from '../components/Page'
import { errMsg } from '../api/client'
import {
  useModels, useProviders, useAvailableProviders, useAddProvider,
  useDeleteProvider, useTestModel, useOllama,
} from '../hooks/useApi'

// Carte dédiée : état du démon Ollama local + modèles installés sur la machine.
function OllamaCard() {
  const { data, isFetching, refetch } = useOllama()
  const up = data?.up
  return (
    <Card sx={{ mb: 3, borderColor: up ? 'success.main' : 'divider' }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
          <Stack direction="row" gap={1} alignItems="center">
            <Computer color={up ? 'success' : 'disabled'} />
            <Typography variant="h6">Ollama (local)</Typography>
            <Chip size="small" icon={<Circle sx={{ fontSize: '10px !important' }} />}
              color={up ? 'success' : 'default'}
              label={up ? `en ligne · ${data.count} modèle(s)` : 'hors ligne'} />
          </Stack>
          <IconButton size="small" onClick={() => refetch()} disabled={isFetching}>
            <Refresh fontSize="small" />
          </IconButton>
        </Stack>
        <Typography variant="caption" color="text.secondary">{data?.base_url}</Typography>

        {up ? (
          <Stack direction="row" gap={1} flexWrap="wrap" mt={1.5}>
            {data.models.map((m) => (
              <Chip key={m.id} label={`${m.id}`} variant="outlined"
                icon={<Computer sx={{ fontSize: '16px !important' }} />} />
            ))}
            {data.count === 0 && (
              <Typography variant="body2" color="text.secondary">
                Aucun modèle installé — lancez <code>ollama pull llama3.2</code>.
              </Typography>
            )}
          </Stack>
        ) : (
          <Alert severity="warning" sx={{ mt: 1.5 }}>
            {data?.hint || 'Démon Ollama injoignable. Lancez `ollama serve`.'}
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}

export default function LLMManager() {
  const { data: models } = useModels()
  const { data: providers } = useProviders()
  const { data: available } = useAvailableProviders()
  const addProvider = useAddProvider()
  const delProvider = useDeleteProvider()
  const testModel = useTestModel()

  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ provider_key: 'ollama', api_key: '', base_url: '', label: 'default' })
  const [error, setError] = useState('')
  const [testResult, setTestResult] = useState(null)

  const submit = async () => {
    setError('')
    try {
      await addProvider.mutateAsync(form)
      setOpen(false)
      setForm({ provider_key: 'ollama', api_key: '', base_url: '', label: 'default' })
    } catch (e) {
      setError(errMsg(e))
    }
  }

  const runTest = async (model) => {
    setTestResult({ model, loading: true })
    try {
      const r = await testModel.mutateAsync(model)
      setTestResult({ ...r, loading: false })
    } catch (e) {
      setTestResult({ model, error: errMsg(e), loading: false })
    }
  }

  return (
    <Page
      title="LLM Manager"
      subtitle="Fournisseurs, modèles disponibles, coûts et latence"
      action={<Button variant="contained" startIcon={<Add />} onClick={() => setOpen(true)}>Ajouter un fournisseur</Button>}
    >
      {/* Ollama local : modèles installés sur la machine */}
      <OllamaCard />

      {/* Fournisseurs configurés */}
      <Grid container spacing={2} mb={3}>
        {(providers || []).length === 0 && (
          <Grid item xs={12}>
            <Alert severity="info">
              Aucun fournisseur cloud configuré — ResearchOS utilise Ollama en local par défaut.
            </Alert>
          </Grid>
        )}
        {(providers || []).map((p) => (
          <Grid item xs={12} sm={6} md={4} key={p.id}>
            <Card>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Stack direction="row" gap={1} alignItems="center">
                    <Typography fontWeight={600} textTransform="capitalize">{p.provider_key}</Typography>
                    <Chip size="small" label={p.label} variant="outlined" />
                    {p.is_default && <Chip size="small" color="primary" label="défaut" />}
                  </Stack>
                  <IconButton size="small" onClick={() => delProvider.mutate(p.id)}><Delete fontSize="small" /></IconButton>
                </Stack>
                <Typography variant="body2" color="text.secondary" mt={1}>
                  {p.api_key_masked || 'sans clé (local)'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Résultat de test */}
      {testResult && (
        <Alert
          severity={testResult.error ? 'error' : testResult.loading ? 'info' : 'success'}
          sx={{ mb: 2 }}
          onClose={() => setTestResult(null)}
        >
          {testResult.loading
            ? `Test de ${testResult.model}…`
            : testResult.error
              ? `${testResult.model} : ${testResult.error}`
              : `${testResult.model} OK — ${testResult.latency_ms} ms, ${testResult.tokens} tokens, $${testResult.cost_usd}`}
        </Alert>
      )}

      {/* Catalogue de modèles */}
      <Card>
        <CardContent>
          <Typography variant="h6" mb={1}>Modèles disponibles ({models?.models?.length ?? 0})</Typography>
          {!models && <LinearProgress />}
          <Box sx={{ overflowX: 'auto' }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Modèle</TableCell>
                  <TableCell>Fournisseur</TableCell>
                  <TableCell align="center">Confid.</TableCell>
                  <TableCell align="right">Contexte</TableCell>
                  <TableCell align="right">$/1M in</TableCell>
                  <TableCell align="center">Qualité</TableCell>
                  <TableCell align="center">Vitesse</TableCell>
                  <TableCell align="right">Test</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(models?.models || []).map((m) => (
                  <TableRow key={m.id} hover>
                    <TableCell><Typography variant="body2" fontWeight={600}>{m.display_name}</Typography></TableCell>
                    <TableCell><Typography variant="body2" color="text.secondary">{m.provider}</Typography></TableCell>
                    <TableCell align="center">
                      {m.privacy === 'local'
                        ? <Tooltip title="Local"><Computer fontSize="small" color="success" /></Tooltip>
                        : <Tooltip title="Cloud"><Cloud fontSize="small" color="disabled" /></Tooltip>}
                    </TableCell>
                    <TableCell align="right">{(m.context_window / 1000).toFixed(0)}k</TableCell>
                    <TableCell align="right">{m.input_cost === 0 ? 'gratuit' : `$${m.input_cost}`}</TableCell>
                    <TableCell align="center"><Bar v={m.quality} /></TableCell>
                    <TableCell align="center"><Bar v={m.speed} /></TableCell>
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => runTest(m.id)}><PlayArrow fontSize="small" /></IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </CardContent>
      </Card>

      {/* Dialog ajout fournisseur */}
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Ajouter un fournisseur IA</DialogTitle>
        <DialogContent>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <Stack gap={2} mt={1}>
            <TextField select label="Fournisseur" value={form.provider_key}
              onChange={(e) => setForm({ ...form, provider_key: e.target.value })}>
              {(available?.providers || ['ollama']).map((p) => (
                <MenuItem key={p} value={p}>{p}</MenuItem>
              ))}
            </TextField>
            {form.provider_key === 'ollama' && (
              <Alert severity="info">
                Ollama local est <b>déjà actif automatiquement</b> — inutile de l'ajouter.
                Ajoutez-le seulement pour un Ollama <b>distant</b> (renseignez la Base URL).
              </Alert>
            )}
            <TextField label="Clé API" type="password" value={form.api_key}
              onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              helperText="Laisser vide pour Ollama (local)" />
            <TextField label="Base URL (optionnel)" value={form.base_url}
              onChange={(e) => setForm({ ...form, base_url: e.target.value })} />
            <TextField label="Label" value={form.label}
              onChange={(e) => setForm({ ...form, label: e.target.value })} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Annuler</Button>
          <Button variant="contained" startIcon={<CheckCircle />} onClick={submit} disabled={addProvider.isPending}>
            Ajouter
          </Button>
        </DialogActions>
      </Dialog>
    </Page>
  )
}

const Bar = ({ v }) => (
  <Box sx={{ width: 46, height: 6, borderRadius: 3, bgcolor: 'action.hover', mx: 'auto' }}>
    <Box sx={{ width: `${Math.round(v * 100)}%`, height: '100%', borderRadius: 3, bgcolor: 'primary.main' }} />
  </Box>
)
