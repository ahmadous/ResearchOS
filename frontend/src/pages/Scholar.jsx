import { useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Chip, IconButton, InputAdornment,
  Stack, TextField, Tooltip, Typography,
} from '@mui/material'
import { Search, LibraryAdd, OpenInNew, CheckCircle } from '@mui/icons-material'
import Page from '../components/Page'
import { errMsg } from '../api/client'
import { useScholarSearch, useImportPaper } from '../hooks/useApi'

export default function Scholar() {
  const search = useScholarSearch()
  const importPaper = useImportPaper()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [imported, setImported] = useState({})
  const [error, setError] = useState('')

  const run = async () => {
    if (query.trim().length < 2) return
    setError('')
    setResults({ loading: true })
    try {
      setResults(await search.mutateAsync({ query }))
    } catch (e) { setError(errMsg(e)); setResults(null) }
  }

  const doImport = async (paper, i) => {
    try {
      await importPaper.mutateAsync(paper)
      setImported((s) => ({ ...s, [i]: true }))
    } catch (e) { setError(errMsg(e)) }
  }

  return (
    <Page title="Recherche scientifique" subtitle="arXiv · OpenAlex · Semantic Scholar · CrossRef · HAL">
      <Stack direction="row" gap={1} mb={3}>
        <TextField
          fullWidth placeholder="Ex : transformer attention mechanism" value={query}
          onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && run()}
          InputProps={{ startAdornment: <InputAdornment position="start"><Search /></InputAdornment> }}
        />
        <Button variant="contained" onClick={run} disabled={search.isPending}>Rechercher</Button>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {results?.loading && <Typography color="text.secondary">Interrogation des bases…</Typography>}
      {results?.count === 0 && <Alert severity="info">Aucun résultat.</Alert>}

      <Stack gap={1.5}>
        {(results?.results || []).map((p, i) => (
          <Card key={i}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={2}>
                <Box>
                  <Typography fontWeight={600}>{p.title}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {(p.authors || []).slice(0, 4).join(', ')}{p.authors?.length > 4 ? ' et al.' : ''}
                    {p.year ? ` · ${p.year}` : ''}{p.venue ? ` · ${p.venue}` : ''}
                  </Typography>
                  {p.abstract && (
                    <Typography variant="body2" color="text.secondary" mt={1}
                      sx={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {p.abstract}
                    </Typography>
                  )}
                  <Stack direction="row" gap={0.5} mt={1}>
                    <Chip size="small" variant="outlined" label={p.source} />
                    {p.citations != null && <Chip size="small" variant="outlined" label={`${p.citations} cit.`} />}
                    {p.doi && <Chip size="small" variant="outlined" label={p.doi} />}
                  </Stack>
                </Box>
                <Stack gap={0.5} alignItems="center">
                  {p.url && (
                    <Tooltip title="Ouvrir">
                      <IconButton size="small" component="a" href={p.url} target="_blank"><OpenInNew fontSize="small" /></IconButton>
                    </Tooltip>
                  )}
                  <Tooltip title="Indexer dans le RAG">
                    <span>
                      <IconButton size="small" color={imported[i] ? 'success' : 'primary'}
                        onClick={() => doImport(p, i)} disabled={imported[i]}>
                        {imported[i] ? <CheckCircle fontSize="small" /> : <LibraryAdd fontSize="small" />}
                      </IconButton>
                    </span>
                  </Tooltip>
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Stack>
    </Page>
  )
}
