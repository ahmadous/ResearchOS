import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Chip, IconButton, MenuItem, Stack,
  TextField, Tooltip, Typography,
} from '@mui/material'
import { AutoAwesome, DeleteSweep, Refresh } from '@mui/icons-material'
import Page from '../components/Page'
import { errMsg } from '../api/client'
import { useGraph, useExtractGraph, useClearGraph, useDocuments } from '../hooks/useApi'

const TYPE_COLOR = {
  author: '#6366f1', institution: '#22d3ee', dataset: '#34d399',
  algorithm: '#f59e0b', method: '#f472b6', concept: '#94a3b8',
}
const color = (t) => TYPE_COLOR[t] || TYPE_COLOR.concept
const W = 900, H = 560

// Petite simulation force-directed (répulsion + ressorts + centrage).
function useForceLayout(nodes, edges) {
  const pos = useRef(new Map())
  const [, tick] = useState(0)
  const alpha = useRef(1)
  const raf = useRef(null)
  const drag = useRef(null)

  // (Ré)initialise les positions des nouveaux nœuds ; conserve les existantes.
  useEffect(() => {
    const p = pos.current
    nodes.forEach((n, i) => {
      if (!p.has(n.id)) {
        const a = (i / Math.max(1, nodes.length)) * Math.PI * 2
        p.set(n.id, { x: W / 2 + Math.cos(a) * 180, y: H / 2 + Math.sin(a) * 140, vx: 0, vy: 0 })
      }
    })
    for (const id of [...p.keys()]) if (!nodes.find((n) => n.id === id)) p.delete(id)
    alpha.current = 1
  }, [nodes])

  useEffect(() => {
    const step = () => {
      const p = pos.current
      const arr = nodes.map((n) => n.id)
      const k = 90
      // répulsion
      for (let i = 0; i < arr.length; i++) {
        const a = p.get(arr[i])
        for (let j = i + 1; j < arr.length; j++) {
          const b = p.get(arr[j])
          let dx = a.x - b.x, dy = a.y - b.y
          let d2 = dx * dx + dy * dy || 0.01
          const f = (k * k) / d2
          const d = Math.sqrt(d2)
          const fx = (dx / d) * f, fy = (dy / d) * f
          a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy
        }
      }
      // ressorts (arêtes)
      edges.forEach((e) => {
        const a = p.get(e.source), b = p.get(e.target)
        if (!a || !b) return
        let dx = b.x - a.x, dy = b.y - a.y
        const d = Math.sqrt(dx * dx + dy * dy) || 0.01
        const f = (d - 140) * 0.02
        const fx = (dx / d) * f, fy = (dy / d) * f
        a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy
      })
      // centrage + intégration
      arr.forEach((id) => {
        const n = p.get(id)
        if (drag.current === id) return
        n.vx += (W / 2 - n.x) * 0.005
        n.vy += (H / 2 - n.y) * 0.005
        n.vx *= 0.85; n.vy *= 0.85
        n.x += n.vx * alpha.current; n.y += n.vy * alpha.current
        n.x = Math.max(30, Math.min(W - 30, n.x))
        n.y = Math.max(30, Math.min(H - 30, n.y))
      })
      alpha.current *= 0.99
      tick((t) => t + 1)
      raf.current = requestAnimationFrame(step)
    }
    raf.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf.current)
  }, [nodes, edges])

  const reheat = () => (alpha.current = Math.max(alpha.current, 0.6))
  return { pos: pos.current, drag, reheat }
}

export default function KnowledgeGraph() {
  const { data: graph, refetch, isFetching } = useGraph()
  const { data: docs } = useDocuments()
  const extract = useExtractGraph()
  const clear = useClearGraph()
  const svgRef = useRef(null)

  const [text, setText] = useState('')
  const [docId, setDocId] = useState('')
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)

  const nodes = graph?.nodes || []
  const edges = graph?.edges || []
  const { pos, drag, reheat } = useForceLayout(nodes, edges)

  const typesPresent = useMemo(() => [...new Set(nodes.map((n) => n.type))], [nodes])

  const doExtract = async () => {
    setError('')
    try {
      await extract.mutateAsync(docId ? { document_id: docId } : { text })
      setText('')
      // Le graphe se rafraîchit à la fin de la tâche (event WebSocket -> invalidation).
    } catch (e) { setError(errMsg(e)) }
  }

  // Drag des nœuds (coordonnées SVG).
  const toSvg = (e) => {
    const r = svgRef.current.getBoundingClientRect()
    return { x: ((e.clientX - r.left) / r.width) * W, y: ((e.clientY - r.top) / r.height) * H }
  }
  useEffect(() => {
    const move = (e) => {
      if (!drag.current) return
      const { x, y } = toSvg(e)
      const n = pos.get(drag.current)
      if (n) { n.x = x; n.y = y; n.vx = 0; n.vy = 0 }
    }
    const up = () => { drag.current = null }
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', up)
    return () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up) }
  }, []) // eslint-disable-line

  return (
    <Page
      title="Knowledge Graph"
      subtitle="Entités et relations extraites automatiquement de vos documents"
      action={
        <Stack direction="row" gap={1}>
          <Tooltip title="Rafraîchir"><IconButton onClick={() => refetch()}><Refresh /></IconButton></Tooltip>
          <Button color="error" variant="outlined" startIcon={<DeleteSweep />}
            onClick={() => clear.mutate()} disabled={!nodes.length}>Vider</Button>
        </Stack>
      }
    >
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      {/* Extraction */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Stack direction={{ xs: 'column', md: 'row' }} gap={1.5} alignItems="stretch">
            <TextField select size="small" label="Depuis un document" value={docId}
              onChange={(e) => setDocId(e.target.value)} sx={{ minWidth: 220 }}>
              <MenuItem value="">— texte libre —</MenuItem>
              {(docs?.documents || []).map((d) => <MenuItem key={d.id} value={d.id}>{d.title}</MenuItem>)}
            </TextField>
            <TextField size="small" fullWidth placeholder="…ou collez du texte à analyser"
              value={text} onChange={(e) => setText(e.target.value)} disabled={!!docId} />
            <Button variant="contained" startIcon={<AutoAwesome />} onClick={doExtract}
              disabled={extract.isPending || (!text && !docId)}>Extraire</Button>
          </Stack>
        </CardContent>
      </Card>

      {/* Légende */}
      {typesPresent.length > 0 && (
        <Stack direction="row" gap={1} mb={1.5} flexWrap="wrap">
          {typesPresent.map((t) => (
            <Chip key={t} size="small" label={t}
              sx={{ bgcolor: color(t), color: '#fff', textTransform: 'capitalize' }} />
          ))}
          <Box flex={1} />
          <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center' }}>
            {nodes.length} entités · {edges.length} relations
          </Typography>
        </Stack>
      )}

      {/* Graphe */}
      <Card>
        <CardContent sx={{ p: 1 }}>
          {nodes.length === 0 ? (
            <Stack alignItems="center" justifyContent="center" height={360}>
              <Typography color="text.secondary">
                {isFetching ? 'Chargement…' : 'Extrayez un premier document pour bâtir le graphe.'}
              </Typography>
            </Stack>
          ) : (
            <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: '62vh' }}>
              {edges.map((e, i) => {
                const a = pos.get(e.source), b = pos.get(e.target)
                if (!a || !b) return null
                return (
                  <g key={i}>
                    <line x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                      stroke="rgba(148,163,184,0.4)" strokeWidth={Math.min(1 + e.weight, 4)} />
                    <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2} fontSize="9"
                      fill="rgba(148,163,184,0.9)" textAnchor="middle">{e.label}</text>
                  </g>
                )
              })}
              {nodes.map((n) => {
                const p = pos.get(n.id)
                if (!p) return null
                const r = 8 + Math.min(n.mentions, 6) * 2
                const isSel = selected?.id === n.id
                return (
                  <g key={n.id} transform={`translate(${p.x},${p.y})`}
                    style={{ cursor: 'grab' }}
                    onPointerDown={(ev) => { ev.preventDefault(); drag.current = n.id; reheat() }}
                    onClick={() => setSelected(n)}>
                    <circle r={r} fill={color(n.type)}
                      stroke={isSel ? '#fff' : 'rgba(0,0,0,0.25)'} strokeWidth={isSel ? 2.5 : 1} />
                    <text y={r + 12} fontSize="11" textAnchor="middle"
                      fill="currentColor" style={{ pointerEvents: 'none' }}>{n.name}</text>
                  </g>
                )
              })}
            </svg>
          )}
        </CardContent>
      </Card>

      {selected && (
        <Alert severity="info" sx={{ mt: 1 }} onClose={() => setSelected(null)}>
          <b>{selected.name}</b> — type <i>{selected.type}</i>, {selected.mentions} mention(s)
        </Alert>
      )}
    </Page>
  )
}
