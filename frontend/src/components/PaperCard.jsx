import { Box, Chip, Link, Paper, Stack, Typography } from '@mui/material'
import { alpha } from '@mui/material/styles'
import { FormatQuote, OpenInNew, CalendarToday } from '@mui/icons-material'

// Carte-article riche, partagée par la Revue de littérature et la Recherche sci.
// Titre en serif (ton académique) qui contraste avec l'UI sans-serif du reste.
const SERIF = '"Charter","Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif'
const SOURCE_COLOR = {
  arxiv: '#B31B1B', openalex: '#4F46E5', crossref: '#0E7490',
  semanticscholar: '#1857B6', 'semantic scholar': '#1857B6', hal: '#C1272D',
}

function CitationBadge({ n }) {
  const has = typeof n === 'number'
  return (
    <Stack alignItems="center" justifyContent="center" sx={{
      minWidth: 62, px: 1, py: 0.75, borderRadius: 2, alignSelf: 'flex-start',
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

export default function PaperCard({ paper: p, rank, actions }) {
  const color = SOURCE_COLOR[String(p.source || '').toLowerCase()] || '#6B7280'
  const authors = p.authors || []
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
        {rank != null && (
          <Typography sx={{
            fontFamily: SERIF, fontSize: 15, color: 'text.disabled', minWidth: 22,
            fontVariantNumeric: 'tabular-nums', pt: 0.3,
          }}>{rank}</Typography>
        )}

        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Link href={p.url || undefined} target="_blank" rel="noopener" underline="none"
            sx={{
              fontFamily: SERIF, fontSize: '1.06rem', fontWeight: 600, lineHeight: 1.3,
              color: 'text.primary', display: 'block',
              '&:hover': { color: 'primary.main' },
            }}>
            {p.title}
          </Link>

          <Stack direction="row" flexWrap="wrap" alignItems="center" gap={0.75} mt={0.6}
            sx={{ color: 'text.secondary' }}>
            <Typography variant="caption" sx={{ fontWeight: 500 }}>
              {authors.slice(0, 3).join(', ')}{authors.length > 3 ? ' et al.' : ''}
              {authors.length === 0 && 'Auteurs inconnus'}
            </Typography>
            {p.year && (
              <>
                <Box component="span" sx={{ opacity: 0.4 }}>·</Box>
                <Stack direction="row" alignItems="center" gap={0.3}>
                  <CalendarToday sx={{ fontSize: 11 }} />
                  <Typography variant="caption">{p.year}</Typography>
                </Stack>
              </>
            )}
            {p.venue && (
              <>
                <Box component="span" sx={{ opacity: 0.4 }}>·</Box>
                <Typography variant="caption" sx={{ fontStyle: 'italic', maxWidth: 260,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {p.venue}
                </Typography>
              </>
            )}
          </Stack>

          {p.abstract && (
            <Typography variant="body2" color="text.secondary" sx={{
              mt: 1, lineHeight: 1.55,
              display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden',
            }}>
              {p.abstract}
            </Typography>
          )}

          <Stack direction="row" alignItems="center" flexWrap="wrap" gap={1} mt={1.25}>
            <Chip size="small" label={p.source}
              sx={{
                height: 22, fontSize: 11, fontWeight: 600, textTransform: 'lowercase',
                color, bgcolor: alpha(color, 0.1), border: `1px solid ${alpha(color, 0.3)}`,
              }} />
            {p.url && (
              <Link href={p.url} target="_blank" rel="noopener" underline="hover"
                sx={{ fontSize: 12.5, display: 'inline-flex', alignItems: 'center', gap: 0.4, color: 'primary.main' }}>
                Ouvrir <OpenInNew sx={{ fontSize: 13 }} />
              </Link>
            )}
            {actions}
          </Stack>
        </Box>

        <CitationBadge n={p.citations} />
      </Stack>
    </Paper>
  )
}
