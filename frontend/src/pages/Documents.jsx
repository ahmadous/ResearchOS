import { useRef, useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Chip, Divider, Grid, IconButton,
  List, ListItem, ListItemAvatar, ListItemText, Avatar, Paper, Stack,
  TextField, Typography, LinearProgress,
} from '@mui/material'
import {
  Delete, Send, UploadFile, PictureAsPdf, Description, TableChart, Image as ImageIcon,
  Movie, Article, InsertDriveFile,
} from '@mui/icons-material'
import Page from '../components/Page'
import { api, errMsg } from '../api/client'
import { useDocuments, useIngest, useRagQuery, useUploadFile } from '../hooks/useApi'
import { useQueryClient } from '@tanstack/react-query'

const ICONS = {
  pdf: <PictureAsPdf color="error" />, word: <Description color="primary" />,
  excel: <TableChart color="success" />, image: <ImageIcon color="secondary" />,
  video: <Movie color="warning" />, markdown: <Article />, text: <Article />,
  paper: <Article color="info" />,
}
const iconFor = (t) => ICONS[t] || <InsertDriveFile />
const ACCEPT = '.pdf,.doc,.docx,.xls,.xlsx,.csv,.md,.txt,.tex,.bib,.png,.jpg,.jpeg,.gif,.webp,.mp4,.mov,.webm,.mkv'

export default function Documents() {
  const { data } = useDocuments()
  const ingest = useIngest()
  const upload = useUploadFile()
  const ragQuery = useRagQuery()
  const qc = useQueryClient()
  const fileInput = useRef(null)

  const [form, setForm] = useState({ title: '', text: '' })
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [dragOver, setDragOver] = useState(false)

  const doIngest = async () => {
    setError('')
    try {
      await ingest.mutateAsync(form)
      setForm({ title: '', text: '' })
    } catch (e) { setError(errMsg(e)) }
  }

  const uploadFiles = async (files) => {
    setError(''); setNotice('')
    for (const file of files) {
      try {
        const r = await upload.mutateAsync(file)
        setNotice(r.indexed ? `« ${r.title} » indexé (${r.n_chunks} chunks).`
                            : `« ${r.title} » ajouté (${r.note || 'pièce jointe'}).`)
      } catch (e) { setError(`${file.name} : ${errMsg(e)}`) }
    }
  }
  const onDrop = (e) => {
    e.preventDefault(); setDragOver(false)
    if (e.dataTransfer.files?.length) uploadFiles([...e.dataTransfer.files])
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
              <Typography variant="h6" mb={2}>Importer</Typography>
              {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
              {notice && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setNotice('')}>{notice}</Alert>}

              {/* Zone glisser-déposer / sélection de fichiers */}
              <Box
                onClick={() => fileInput.current?.click()}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onDrop={onDrop}
                sx={{
                  border: '2px dashed', borderColor: dragOver ? 'primary.main' : 'divider',
                  borderRadius: 2, p: 3, textAlign: 'center', cursor: 'pointer',
                  bgcolor: dragOver ? 'action.hover' : 'transparent', mb: 2,
                }}
              >
                <UploadFile color="primary" />
                <Typography variant="body2" mt={0.5}>Glissez un fichier ou cliquez</Typography>
                <Typography variant="caption" color="text.secondary">
                  PDF · Word · Excel · Markdown · images · vidéos
                </Typography>
                <input ref={fileInput} type="file" hidden multiple accept={ACCEPT}
                  onChange={(e) => { uploadFiles([...e.target.files]); e.target.value = '' }} />
              </Box>
              {upload.isPending && <LinearProgress sx={{ mb: 2 }} />}

              <Divider>ou coller du texte</Divider>
              <Stack gap={1.5} mt={2}>
                <TextField label="Titre" size="small" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
                <TextField label="Contenu" multiline minRows={3} maxRows={16} value={form.text}
                  onChange={(e) => setForm({ ...form, text: e.target.value })} />
                <Button variant="outlined" onClick={doIngest} disabled={ingest.isPending || !form.text}>
                  Indexer le texte
                </Button>
              </Stack>

              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle2" mb={1}>Bibliothèque ({data?.documents?.length ?? 0})</Typography>
              <List dense>
                {(data?.documents || []).map((d) => (
                  <ListItem key={d.id}
                    secondaryAction={<IconButton size="small" onClick={() => del(d.id)}><Delete fontSize="small" /></IconButton>}>
                    <ListItemAvatar>
                      <Avatar variant="rounded" sx={{ bgcolor: 'action.hover' }}>{iconFor(d.source_type)}</Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={d.title}
                      secondary={d.is_attachment
                        ? `${d.source_type} · pièce jointe`
                        : `${d.source_type} · ${d.n_chunks} chunks`}
                      primaryTypographyProps={{ noWrap: true, fontSize: 14 }} />
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
              <Stack direction="row" gap={1} mb={2} alignItems="flex-end">
                <TextField fullWidth size="small" placeholder="Votre question…" value={question}
                  multiline maxRows={6}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask() } }} />
                <IconButton color="primary" onClick={ask} disabled={ragQuery.isPending} sx={{ mb: 0.25 }}><Send /></IconButton>
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
