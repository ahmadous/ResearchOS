import { useMemo, useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Chip, Divider,
  IconButton, Link, Stack, Table, TableBody, TableCell, TableHead,
  TableRow, TableSortLabel, TextField, Typography, CircularProgress,
} from '@mui/material'
import { Search, PictureAsPdf, MenuBook, OpenInNew, Science, AutoAwesome } from '@mui/icons-material'
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
      subtitle="Recherche d'articles réelle · tableau comparatif · extraits · liens · export">
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      <Card sx={{ mb: 2 }}>
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
          <Stack alignItems="center" justifyContent="center" minHeight={220}>
            <Science color="disabled" />
            <Typography color="text.secondary" mt={1}>
              Lancez une recherche — les articles réels s'affichent instantanément.
            </Typography>
          </Stack>
        </CardContent></Card>
      ) : (
        <Card><CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={1} mb={1}>
            <Typography variant="h6">{data.count} articles · « {data.query} »</Typography>
            <Stack direction="row" gap={1}>
              <Button size="small" variant="outlined"
                startIcon={synth.isPending ? <CircularProgress size={14} /> : <AutoAwesome />}
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

          {synth.isPending && (
            <Alert severity="info" icon={<CircularProgress size={16} />} sx={{ mb: 2 }}>
              Génération de la synthèse en cours (peut prendre 1-2 min sur un modèle local)…
            </Alert>
          )}
          {synthesis && (
            <Alert severity="info" icon={false} sx={{ mb: 2, whiteSpace: 'pre-wrap' }}>
              <b>Synthèse IA</b>{'\n'}{synthesis}
            </Alert>
          )}

          {data.count === 0 ? (
            <Typography color="text.secondary">Aucun article trouvé pour cette requête.</Typography>
          ) : (
            <>
              {/* Tableau comparatif — trois colonnes triables */}
              <Box sx={{ overflowX: 'auto' }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>#</TableCell>
                      <TableCell sortDirection="desc">
                        <TableSortLabel active={sortBy === 'title'} direction="asc" onClick={() => setSortBy('title')}>Titre</TableSortLabel>
                      </TableCell>
                      <TableCell>Auteurs</TableCell>
                      <TableCell align="right">
                        <TableSortLabel active={sortBy === 'year'} direction="desc" onClick={() => setSortBy('year')}>Année</TableSortLabel>
                      </TableCell>
                      <TableCell align="right">
                        <TableSortLabel active={sortBy === 'citations'} direction="desc" onClick={() => setSortBy('citations')}>Cit.</TableSortLabel>
                      </TableCell>
                      <TableCell>Source</TableCell>
                      <TableCell>Lien</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rows.map((r, i) => (
                      <TableRow key={i} hover>
                        <TableCell>{i + 1}</TableCell>
                        <TableCell sx={{ maxWidth: 360 }}>
                          {r.url ? <Link href={r.url} target="_blank" underline="hover">{r.title}</Link>
                                 : <Typography variant="body2">{r.title}</Typography>}
                        </TableCell>
                        <TableCell><Typography variant="caption">
                          {(r.authors || []).slice(0, 2).join(', ')}{r.authors?.length > 2 ? ' et al.' : ''}</Typography></TableCell>
                        <TableCell align="right">{r.year || '—'}</TableCell>
                        <TableCell align="right">{r.citations ?? '—'}</TableCell>
                        <TableCell><Chip size="small" variant="outlined" label={r.source} /></TableCell>
                        <TableCell>
                          {r.url && <IconButton size="small" component="a" href={r.url} target="_blank"><OpenInNew fontSize="inherit" /></IconButton>}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>

              {/* Extraits */}
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle2" mb={1}>Extraits</Typography>
              <Stack gap={1.5}>
                {rows.map((r, i) => (
                  <Box key={i}>
                    <Link href={r.url} target="_blank" underline="hover" variant="body2" fontWeight={600}>
                      [{i + 1}] {r.title}
                    </Link>
                    <Typography variant="caption" color="text.secondary" display="block">
                      {(r.authors || []).slice(0, 4).join(', ')}{r.year ? ` · ${r.year}` : ''}{r.venue ? ` · ${r.venue}` : ''}
                    </Typography>
                    <Typography variant="caption" color="text.secondary"
                      sx={{ display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden', mt: 0.3 }}>
                      {r.abstract || '(pas de résumé)'}
                    </Typography>
                  </Box>
                ))}
              </Stack>
            </>
          )}
        </CardContent></Card>
      )}
    </Page>
  )
}
