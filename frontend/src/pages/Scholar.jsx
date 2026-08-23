import { useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, InputAdornment,
  Stack, TextField, Typography, CircularProgress,
} from '@mui/material'
import { Search, LibraryAdd, CheckCircle, TravelExplore } from '@mui/icons-material'
import Page from '../components/Page'
import PaperCard from '../components/PaperCard'
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

  const papers = results?.results || []

  return (
    <Page title="Recherche scientifique" subtitle="arXiv · OpenAlex · Semantic Scholar · CrossRef · HAL">
      <Card sx={{ mb: 2.5 }}>
        <CardContent>
          <Stack direction={{ xs: 'column', sm: 'row' }} gap={1} alignItems="center">
            <TextField fullWidth size="small" placeholder="Ex : transformer attention mechanism"
              value={query} onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && run()} disabled={search.isPending}
              InputProps={{ startAdornment: <InputAdornment position="start"><Search fontSize="small" /></InputAdornment> }} />
            <Button variant="contained" onClick={run} disabled={search.isPending || query.trim().length < 2}
              startIcon={search.isPending ? <CircularProgress size={16} color="inherit" /> : <Search />}>
              Rechercher
            </Button>
          </Stack>
          <Typography variant="caption" color="text.secondary" mt={1} display="block">
            Recherche multi-sources. Indexez un article dans le RAG pour ensuite l'interroger dans Documents.
          </Typography>
        </CardContent>
      </Card>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      {results?.loading ? (
        <Card><CardContent>
          <Stack direction="row" alignItems="center" gap={1.5} justifyContent="center" minHeight={180}>
            <CircularProgress size={20} />
            <Typography color="text.secondary">Interrogation des bases scientifiques…</Typography>
          </Stack>
        </CardContent></Card>
      ) : !results ? (
        <Card><CardContent>
          <Stack alignItems="center" justifyContent="center" minHeight={240} gap={1.2}>
            <TravelExplore sx={{ fontSize: 34, color: 'text.disabled' }} />
            <Typography color="text.secondary">
              Cherchez un sujet : les articles s'affichent, prêts à indexer dans votre base RAG.
            </Typography>
          </Stack>
        </CardContent></Card>
      ) : papers.length === 0 ? (
        <Card><CardContent>
          <Typography color="text.secondary">Aucun résultat pour cette requête.</Typography>
        </CardContent></Card>
      ) : (
        <>
          <Typography variant="h6" mb={2}>
            {papers.length} article{papers.length > 1 ? 's' : ''}
          </Typography>
          <Stack gap={1.5}>
            {papers.map((p, i) => (
              <PaperCard key={p.url || i} paper={p} rank={i + 1}
                actions={
                  <Button size="small"
                    variant={imported[i] ? 'text' : 'outlined'}
                    color={imported[i] ? 'success' : 'primary'}
                    disabled={imported[i] || importPaper.isPending}
                    startIcon={imported[i] ? <CheckCircle sx={{ fontSize: 16 }} /> : <LibraryAdd sx={{ fontSize: 16 }} />}
                    onClick={() => doImport(p, i)}
                    sx={{ ml: 'auto', minWidth: 0 }}>
                    {imported[i] ? 'Indexé' : 'Indexer (RAG)'}
                  </Button>
                } />
            ))}
          </Stack>
        </>
      )}
    </Page>
  )
}
