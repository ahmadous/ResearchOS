import { useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Chip, Divider, Grid, IconButton,
  List, ListItem, ListItemText, Paper, Stack, TextField, Typography,
} from '@mui/material'
import { Delete, Send, UploadFile } from '@mui/icons-material'
import Page from '../components/Page'
import { api, errMsg } from '../api/client'
import { useDocuments, useIngest, useRagQuery } from '../hooks/useApi'
import { useQueryClient } from '@tanstack/react-query'

export default function Documents() {
  const { data } = useDocuments()
  const ingest = useIngest()
  const ragQuery = useRagQuery()
  const qc = useQueryClient()

  const [form, setForm] = useState({ title: '', text: '' })
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState(null)
  const [error, setError] = useState('')

  const doIngest = async () => {
    setError('')
    try {
      await ingest.mutateAsync(form)
      setForm({ title: '', text: '' })
    } catch (e) { setError(errMsg(e)) }
  }

  const ask = async () => {
    if (!question.trim()) return
    setAnswer({ loading: true })
    try {
      setAnswer(await ragQuery.mutateAsync({ question }))
    } catch (e) { setAnswer({ error: errMsg(e) }) }
  }

  const del = async (id) => {
    await api.delete(`/rag/documents/${id}`)
    qc.invalidateQueries({ queryKey: ['documents'] })
  }

  return (
    <Page title="Documents (RAG)" subtitle="Importez du texte et interrogez-le avec citations">
      <Grid container spacing={2.5}>
        {/* Import */}
        <Grid item xs={12} md={5}>
          <Card>
            <CardContent>
              <Typography variant="h6" mb={2}>Importer un document</Typography>
              {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
              <Stack gap={2}>
                <TextField label="Titre" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
                <TextField label="Contenu" multiline minRows={6} value={form.text}
                  onChange={(e) => setForm({ ...form, text: e.target.value })} />
                <Button variant="contained" startIcon={<UploadFile />} onClick={doIngest} disabled={ingest.isPending || !form.text}>
                  Indexer
                </Button>
              </Stack>

              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle2" mb={1}>Documents indexés ({data?.documents?.length ?? 0})</Typography>
              <List dense>
                {(data?.documents || []).map((d) => (
                  <ListItem key={d.id}
                    secondaryAction={<IconButton size="small" onClick={() => del(d.id)}><Delete fontSize="small" /></IconButton>}>
                    <ListItemText
                      primary={d.title}
                      secondary={`${d.source_type} · ${d.n_chunks} chunks`}
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Interrogation */}
        <Grid item xs={12} md={7}>
          <Card>
            <CardContent>
              <Typography variant="h6" mb={2}>Interroger (réponse sourcée)</Typography>
              <Stack direction="row" gap={1} mb={2}>
                <TextField fullWidth size="small" placeholder="Votre question…" value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && ask()} />
                <IconButton color="primary" onClick={ask} disabled={ragQuery.isPending}><Send /></IconButton>
              </Stack>

              {answer?.loading && <Typography color="text.secondary">Recherche…</Typography>}
              {answer?.error && <Alert severity="warning">{answer.error}</Alert>}
              {answer?.answer && (
                <Stack gap={2}>
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="body2" whiteSpace="pre-wrap">{answer.answer}</Typography>
                  </Paper>
                  <Box>
                    <Typography variant="subtitle2" mb={1}>Références ({answer.references.length})</Typography>
                    <Stack gap={1}>
                      {answer.references.map((r) => (
                        <Paper key={r.marker} variant="outlined" sx={{ p: 1.5 }}>
                          <Stack direction="row" gap={1} alignItems="center" mb={0.5}>
                            <Chip size="small" color="primary" label={`[${r.marker}]`} />
                            <Typography variant="caption" color="text.secondary">{r.title} · score {r.score}</Typography>
                          </Stack>
                          <Typography variant="caption">{r.snippet}…</Typography>
                        </Paper>
                      ))}
                    </Stack>
                  </Box>
                </Stack>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Page>
  )
}
