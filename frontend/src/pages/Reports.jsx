import { useMemo, useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Chip, IconButton, Link, MenuItem,
  Paper, Select, Stack, TextField, Typography, CircularProgress,
} from '@mui/material'
import { alpha } from '@mui/material/styles'
import {
  Search, PictureAsPdf, MenuBook, OpenInNew, Science, AutoAwesome,
  FormatQuote, CalendarToday,
} from '@mui/icons-material'
import Page from '../components/Page'
import { errMsg } from '../api/client'
import {
  useReportSearch, useReportSynthesize, exportReportPdf, exportBibtex,
} from '../hooks/useApi'

const SORTS = {
  citations: (a, b) => (b.citations ?? -1) - (a.citations ?? -1),
  year: (a, b) => (b.year ?? 0) - (a.year ?? 0),
  title: (a, b) => (a.title || '').localeCompare(b.title || ''),
}

// Couleur d'accent par source (petite touche d'identité, pas un chip gris générique).
const SOURCE_COLOR = {
  arxiv: '#B31B1B', openalex: '#4F46E5', crossref: '#0E7490', semanticscholar: '#1857B6',
}
const SERIF = '"Charter","Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif'

function CitationBadge({ n }) {
  const has = typeof n === 'number'
  return (
    <Stack alignItems="center" justifyContent="center" sx={{
      minWidth: 62, px: 1, py: 0.75, borderRadius: 2,
      bgcolor: (t) => alpha(t.palette.primary.main, has ? 0.1 : 0.04),
      border: (t) => `1px solid ${alpha(t.palette.primary.main, has ? 0.25 : 0.12)}`,
      flexShrink: 0,
    }}>
      <Stack direction="row" alignItems="center" gap={0.3} sx={{ color: 'primary.main' }}>
        <FormatQuote sx={{ fontSize: 13, opacity: 0.7 }} />
        <Typography sx={{ fontWeight: 700, fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
          {has ? n : '—'}
        </Typography>
      </Stack>
      <Typography sx={{ fontSize: 10, color: 'text.secondary', mt: 0.2 }}>
        {n === 1 ? 'citation' : 'citations'}
      </Typography>
    </Stack>
  )
}

function PaperCard({ r, rank }) {
  const color = SOURCE_COLOR[String(r.source || '').toLowerCase()] || '#6B7280'
  const authors = (r.authors || [])
  return (
    <Paper elevation={0} sx={{
      p: 2, borderRadius: 2.5, border: 1, borderColor: 'divider',
      transition: 'transform .15s ease, border-color .15s ease, box-shadow .15s ease',
      '&:hover': {
        transform: 'translateY(-2px)', borderColor: (t) => alpha(t.palette.primary.main, 0.4),
        boxShadow: (t) => `0 10px 30px -18px ${alpha(t.palette.primary.main, 0.5)}`,
      },
    }}>
      <Stack direction="row" gap={1.5}>
        <Typography sx={{
          fontFamily: SERIF, fontSize: 15, color: 'text.disabled', minWidth: 22,
          fontVariantNumeric: 'tabular-nums', pt: 0.3,
        }}>{rank}</Typography>

        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Link href={r.url || undefined} target="_blank" rel="noopener" underline="none"
            sx={{
              fontFamily: SERIF, fontSize: '1.06rem', fontWeight: 600, lineHeight: 1.3,
              color: 'text.primary', display: 'block',
              '&:hover': { color: 'primary.main' },
            }}>
            {r.title}
          </Link>

          <Stack direction="row" flexWrap="wrap" alignItems="center" gap={0.75} mt={0.6}
            sx={{ color: 'text.secondary', fontSize: 12.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 500 }}>
              {authors.slice(0, 3).join(', ')}{authors.length > 3 ? ' et al.' : ''}
              {authors.length === 0 && 'Auteurs inconnus'}
            </Typography>
            {r.year && (
              <>
                <Box component="span" sx={{ opacity: 0.4 }}>·</Box>
                <Stack direction="row" alignItems="center" gap={0.3}>
                  <CalendarToday sx={{ fontSize: 11 }} />
                  <Typography variant="caption">{r.year}</Typography>
                </Stack>
              </>
            )}
            {r.venue && (
              <>
                <Box component="span" sx={{ opacity: 0.4 }}>·</Box>
                <Typography variant="caption" sx={{ fontStyle: 'italic', maxWidth: 260,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {r.venue}
                </Typography>
              </>
            )}
          </Stack>

          {r.abstract && (
            <Typography variant="body2" color="text.secondary" sx={{
              mt: 1, lineHeight: 1.55,
              display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden',
            }}>
              {r.abstract}
            </Typography>
          )}

          <Stack direction="row" alignItems="center" gap={1} mt={1.25}>
            <Chip size="small" label={r.source}
              sx={{
                height: 22, fontSize: 11, fontWeight: 600, textTransform: 'lowercase',
                color, bgcolor: alpha(color, 0.1), border: `1px solid ${alpha(color, 0.3)}`,
              }} />
            {r.url && (
              <Link href={r.url} target="_blank" rel="noopener" underline="hover"
                sx={{ fontSize: 12.5, display: 'inline-flex', alignItems: 'center', gap: 0.4, color: 'primary.main' }}>
                Ouvrir <OpenInNew sx={{ fontSize: 13 }} />
              </Link>
            )}
          </Stack>
        </Box>

        <CitationBadge n={r.citations} />
      </Stack>
    </Paper>
  )
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
              {rows.map((r, i) => <PaperCard key={r.url || i} r={r} rank={i + 1} />)}
            </Stack>
          )}
        </>
      )}
    </Page>
  )
}
