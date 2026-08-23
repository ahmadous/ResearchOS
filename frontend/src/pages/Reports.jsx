import { useMemo, useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, MenuItem, Paper, Select,
  Stack, TextField, Typography, CircularProgress,
} from '@mui/material'
import { alpha } from '@mui/material/styles'
import { Search, PictureAsPdf, MenuBook, Science, AutoAwesome } from '@mui/icons-material'
import Page from '../components/Page'
import PaperCard from '../components/PaperCard'
import { errMsg } from '../api/client'
import {
  useReportSearch, useReportSynthesize, exportReportPdf, exportBibtex,
} from '../hooks/useApi'

const SORTS = {
  citations: (a, b) => (b.citations ?? -1) - (a.citations ?? -1),
  year: (a, b) => (b.year ?? 0) - (a.year ?? 0),
  title: (a, b) => (a.title || '').localeCompare(b.title || ''),
}

export default function Reports() {
  const search = useReportSearch()
  const synth = useReportSynthesize()
  const [query, setQuery] = useState('')
  const [data, setData] = useState(null)
  const [synthesis, setSynthesis] = useState('')
  const [sortBy, setSortBy] = useState('citations')
  const [error, setError] = useState('')

  const run = async () => {
    if (query.trim().length < 2) return
    setError(''); setData(null); setSynthesis('')
    try {
      setData(await search.mutateAsync({ query }))   // recherche pure, jamais de LLM
    } catch (e) { setError(errMsg(e)) }
  }

  const doSynthesize = async () => {
    setError('')
    try {
      const r = await synth.mutateAsync({ query: data.query, papers: data.results })
      setSynthesis(r.synthesis)
    } catch (e) { setError(errMsg(e)) }
  }

  const rows = useMemo(() => {
    const r = [...(data?.results || [])]
    r.sort(SORTS[sortBy])
    return r
  }, [data, sortBy])

  return (
    <Page title="Revue de littérature"
      subtitle="Recherche d'articles réelle · cartes comparatives · résumés · export">
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      {/* Barre de recherche */}
      <Card sx={{ mb: 2.5 }}>
        <CardContent>
          <Stack direction={{ xs: 'column', sm: 'row' }} gap={1} alignItems="center">
            <TextField fullWidth size="small" placeholder="Mots-clés (de préférence en anglais : ex « flood detection satellite deep learning »)"
              value={query} onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && run()} disabled={search.isPending}
              InputProps={{ startAdornment: <Search fontSize="small" sx={{ mr: 1, color: 'text.secondary' }} /> }} />
            <Button variant="contained" startIcon={search.isPending ? <CircularProgress size={16} color="inherit" /> : <Search />}
              onClick={run} disabled={search.isPending || query.trim().length < 2}>
              Rechercher
            </Button>
          </Stack>
          <Typography variant="caption" color="text.secondary" mt={1} display="block">
            Recherche par mots-clés dans arXiv, OpenAlex et CrossRef (pas de reformulation IA). La synthèse IA est optionnelle, après les résultats.
          </Typography>
        </CardContent>
      </Card>

      {!data ? (
        <Card><CardContent>
          <Stack alignItems="center" justifyContent="center" minHeight={240} gap={1.2}>
            <Science sx={{ fontSize: 34, color: 'text.disabled' }} />
            <Typography color="text.secondary">
              Lancez une recherche : les articles réels s'affichent instantanément.
            </Typography>
          </Stack>
        </CardContent></Card>
      ) : (
        <>
          {/* Barre d'actions + tri */}
          <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={1.5} mb={2}>
            <Box>
              <Typography variant="h6" sx={{ lineHeight: 1.2 }}>
                {data.count} article{data.count > 1 ? 's' : ''}
              </Typography>
              <Typography variant="caption" color="text.secondary">« {data.query} »</Typography>
            </Box>
            <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">
              {data.count > 0 && (
                <Select size="small" value={sortBy} onChange={(e) => setSortBy(e.target.value)}
                  sx={{ fontSize: 13, minWidth: 150 }}>
                  <MenuItem value="citations">Trier : citations</MenuItem>
                  <MenuItem value="year">Trier : année</MenuItem>
                  <MenuItem value="title">Trier : titre</MenuItem>
                </Select>
              )}
              <Button size="small" variant="contained"
                startIcon={synth.isPending ? <CircularProgress size={14} color="inherit" /> : <AutoAwesome />}
                onClick={doSynthesize} disabled={!data.count || synth.isPending}>
                Synthèse IA
              </Button>
              <Button size="small" variant="outlined" startIcon={<PictureAsPdf />}
                onClick={() => exportReportPdf({ query: data.query, papers: data.results, synthesis })}
                disabled={!data.count}>PDF</Button>
              <Button size="small" variant="outlined" startIcon={<MenuBook />}
                onClick={() => exportBibtex(data.bibtex)} disabled={!data.count}>BibTeX</Button>
            </Stack>
          </Stack>

          {/* Panneau de synthèse dédié (plus un Alert détourné) */}
          {synth.isPending && (
            <Paper elevation={0} sx={{
              p: 2, mb: 2.5, borderRadius: 2.5, border: 1, borderColor: 'divider',
              display: 'flex', alignItems: 'center', gap: 1.5,
            }}>
              <CircularProgress size={18} />
              <Typography variant="body2" color="text.secondary">
                Génération de la synthèse (peut prendre 1-2 min sur un modèle local ; instantané avec Groq)…
              </Typography>
            </Paper>
          )}
          {synthesis && (
            <Paper elevation={0} sx={{
              position: 'relative', p: 2.5, pl: 3, mb: 2.5, borderRadius: 2.5,
              border: 1, borderColor: (t) => alpha(t.palette.primary.main, 0.25),
              bgcolor: (t) => alpha(t.palette.primary.main, 0.05),
              '&::before': {
                content: '""', position: 'absolute', left: 0, top: 0, bottom: 0, width: 4,
                borderRadius: '10px 0 0 10px',
                background: 'linear-gradient(180deg,#6366f1,#a855f7)',
              },
            }}>
              <Stack direction="row" alignItems="center" gap={0.75} mb={1}>
                <AutoAwesome sx={{ fontSize: 18, color: 'primary.main' }} />
                <Typography sx={{ fontWeight: 700, letterSpacing: '0.02em' }}>Synthèse IA</Typography>
              </Stack>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.65, color: 'text.primary' }}>
                {synthesis}
              </Typography>
            </Paper>
          )}

          {/* Cartes-articles */}
          {data.count === 0 ? (
            <Card><CardContent>
              <Typography color="text.secondary">Aucun article trouvé pour cette requête.</Typography>
            </CardContent></Card>
          ) : (
            <Stack gap={1.5}>
              {rows.map((r, i) => <PaperCard key={r.url || i} paper={r} rank={i + 1} />)}
            </Stack>
          )}
        </>
      )}
    </Page>
  )
}
