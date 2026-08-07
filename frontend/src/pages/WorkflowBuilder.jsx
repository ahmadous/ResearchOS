import { useEffect, useRef, useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Chip, IconButton, MenuItem, Paper,
  Stack, TextField, Tooltip, Typography,
} from '@mui/material'
import {
  Add, DeleteOutline, PlayArrow, Save, Link as LinkIcon, Close, Hub,
} from '@mui/icons-material'
import Page from '../components/Page'
import { errMsg } from '../api/client'
import { useAgents, useWorkflows, useSaveWorkflow, useRunWorkflow } from '../hooks/useApi'
import { useRealtime } from '../store/RealtimeProvider'

const NODE_W = 190
const STATUS_COLOR = { running: 'warning.main', done: 'success.main', failed: 'error.main' }

export default function WorkflowBuilder() {
  const { data: agentsData } = useAgents()
  const { data: wfData } = useWorkflows()
  const save = useSaveWorkflow()
  const run = useRunWorkflow()
  const { socket } = useRealtime()

  const [wf, setWf] = useState({ id: null, name: 'Nouveau workflow' })
  const [nodes, setNodes] = useState([])
  const [edges, setEdges] = useState([])
  const [linkFrom, setLinkFrom] = useState(null)
  const [status, setStatus] = useState({})      // node_id -> running|done|failed
  const [error, setError] = useState('')
  const canvasRef = useRef(null)
  const drag = useRef(null)

  // Écoute la progression par nœud pendant l'exécution.
  useEffect(() => {
    if (!socket) return
    const onNode = (e) => setStatus((s) => ({ ...s, [e.node_id]: e.status }))
    const onDone = () => setError('')
    socket.on('workflow_node', onNode)
    socket.on('task_completed', onDone)
    return () => { socket.off('workflow_node', onNode); socket.off('task_completed', onDone) }
  }, [socket])

  // --- Manipulation du graphe ---
  const addNode = (agent) => {
    const id = `n${Date.now().toString(36)}`
    const count = nodes.length
    setNodes((n) => [...n, {
      id, agent, task: '',
      x: 40 + (count % 3) * 220, y: 30 + Math.floor(count / 3) * 150,
    }])
  }
  const removeNode = (id) => {
    setNodes((n) => n.filter((x) => x.id !== id))
    setEdges((e) => e.filter((x) => x.source !== id && x.target !== id))
  }
  const setTask = (id, task) => setNodes((n) => n.map((x) => (x.id === id ? { ...x, task } : x)))

  const clickNode = (id) => {
    if (!linkFrom) return
    if (linkFrom !== id && !edges.some((e) => e.source === linkFrom && e.target === id)) {
      setEdges((e) => [...e, { source: linkFrom, target: id }])
    }
    setLinkFrom(null)
  }

  // --- Drag & drop des nœuds ---
  const onPointerDown = (e, node) => {
    if (linkFrom) return
    const rect = canvasRef.current.getBoundingClientRect()
    drag.current = { id: node.id, dx: e.clientX - rect.left - node.x, dy: e.clientY - rect.top - node.y }
  }
  useEffect(() => {
    const move = (e) => {
      if (!drag.current) return
      const rect = canvasRef.current.getBoundingClientRect()
      const x = Math.max(0, e.clientX - rect.left - drag.current.dx)
      const y = Math.max(0, e.clientY - rect.top - drag.current.dy)
      setNodes((n) => n.map((nd) => (nd.id === drag.current.id ? { ...nd, x, y } : nd)))
    }
    const up = () => (drag.current = null)
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', up)
    return () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up) }
  }, [])

  // --- Persistance / exécution ---
  const graph = () => ({ nodes, edges })
  const doSave = async () => {
    setError('')
    try {
      const saved = await save.mutateAsync({ id: wf.id, name: wf.name, graph: graph() })
      setWf({ id: saved.id, name: saved.name })
    } catch (e) { setError(errMsg(e)) }
  }
  const doRun = async () => {
    if (!wf.id) { setError('Enregistrez d\'abord le workflow.'); return }
    setStatus({})
    try { await run.mutateAsync(wf.id) } catch (e) { setError(errMsg(e)) }
  }
  const load = (w) => {
    setWf({ id: w.id, name: w.name })
    setNodes(w.graph.nodes || [])
    setEdges(w.graph.edges || [])
    setStatus({})
  }

  const nodeById = (id) => nodes.find((n) => n.id === id)

  return (
    <Page
      title="Workflow Builder"
      subtitle="Construisez un pipeline d'agents en drag & drop"
      action={
        <Stack direction="row" gap={1}>
          <TextField size="small" value={wf.name}
            onChange={(e) => setWf({ ...wf, name: e.target.value })} sx={{ width: 200 }} />
          <Button variant="outlined" startIcon={<Save />} onClick={doSave} disabled={save.isPending}>
            Enregistrer
          </Button>
          <Button variant="contained" startIcon={<PlayArrow />} onClick={doRun} disabled={!nodes.length}>
            Exécuter
          </Button>
        </Stack>
      }
    >
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
      {linkFrom ? (
        <Alert severity="info" sx={{ mb: 2 }}
          action={<IconButton size="small" onClick={() => setLinkFrom(null)}><Close fontSize="small" /></IconButton>}>
          Cliquez le nœud <b>cible</b> pour créer la liaison.
        </Alert>
      ) : nodes.length === 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <b>Comment ça marche :</b> 1) cliquez un agent dans la palette pour l'ajouter ·
          2) écrivez sa tâche dans le nœud · 3) reliez les nœuds avec l'icône 🔗 (l'ordre
          d'exécution suit les flèches) · 4) <b>Enregistrer</b> puis <b>Exécuter</b>. La
          progression s'affiche en direct (nœud orange = en cours, vert = terminé).
        </Alert>
      )}

      <Stack direction="row" gap={2}>
        {/* Palette d'agents */}
        <Card sx={{ width: 210, flexShrink: 0, maxHeight: '70vh', overflowY: 'auto' }}>
          <CardContent>
            <Typography variant="subtitle2" mb={1}>Agents</Typography>
            <Stack gap={0.5}>
              {(agentsData?.agents || []).map((a) => (
                <Button key={a.name} size="small" variant="text" startIcon={<Add />}
                  onClick={() => addNode(a.name)} sx={{ justifyContent: 'flex-start' }}>
                  {a.name.replace('_', ' ')}
                </Button>
              ))}
            </Stack>
          </CardContent>
        </Card>

        {/* Canvas */}
        <Box
          ref={canvasRef}
          sx={{
            position: 'relative', flex: 1, minHeight: '70vh',
            border: 1, borderColor: 'divider', borderRadius: 2,
            bgcolor: 'background.paper', overflow: 'hidden',
            backgroundImage: 'radial-gradient(circle, rgba(128,128,128,0.15) 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }}
        >
          {/* Arêtes (SVG) */}
          <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
            {edges.map((e, i) => {
              const s = nodeById(e.source), t = nodeById(e.target)
              if (!s || !t) return null
              const x1 = s.x + NODE_W / 2, y1 = s.y + 118
              const x2 = t.x + NODE_W / 2, y2 = t.y + 6
              const my = (y1 + y2) / 2
              return (
                <path key={i} d={`M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`}
                  stroke="#6366f1" strokeWidth="2" fill="none" markerEnd="url(#arrow)" />
              )
            })}
            <defs>
              <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                <path d="M0,0 L6,3 L0,6 Z" fill="#6366f1" />
              </marker>
            </defs>
          </svg>

          {/* Nœuds */}
          {nodes.map((n) => (
            <Paper
              key={n.id}
              elevation={0}
              onPointerDown={(e) => onPointerDown(e, n)}
              onClick={() => clickNode(n.id)}
              sx={{
                position: 'absolute', left: n.x, top: n.y, width: NODE_W,
                p: 1, cursor: linkFrom ? 'pointer' : 'grab', userSelect: 'none',
                border: 2, borderRadius: 2,
                borderColor: status[n.id] ? STATUS_COLOR[status[n.id]]
                  : linkFrom === n.id ? 'primary.main' : 'divider',
                boxShadow: status[n.id] === 'running' ? '0 0 12px rgba(245,158,11,0.5)' : 'none',
              }}
            >
              <Stack direction="row" alignItems="center" justifyContent="space-between">
                <Stack direction="row" gap={0.5} alignItems="center">
                  <Hub fontSize="small" color="primary" />
                  <Typography variant="body2" fontWeight={600} textTransform="capitalize">
                    {n.agent.replace('_', ' ')}
                  </Typography>
                </Stack>
                <IconButton size="small" onClick={(ev) => { ev.stopPropagation(); removeNode(n.id) }}>
                  <DeleteOutline sx={{ fontSize: 16 }} />
                </IconButton>
              </Stack>
              <TextField
                variant="standard" placeholder="tâche…" fullWidth value={n.task}
                onChange={(e) => setTask(n.id, e.target.value)}
                onPointerDown={(e) => e.stopPropagation()}
                InputProps={{ disableUnderline: true, sx: { fontSize: 12 } }}
              />
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Tooltip title="Relier vers un autre nœud">
                  <IconButton size="small" onClick={(ev) => { ev.stopPropagation(); setLinkFrom(n.id) }}>
                    <LinkIcon sx={{ fontSize: 16 }} />
                  </IconButton>
                </Tooltip>
                {status[n.id] && <Chip size="small" label={status[n.id]}
                  sx={{ height: 18, fontSize: 10, bgcolor: STATUS_COLOR[status[n.id]], color: '#fff' }} />}
              </Stack>
            </Paper>
          ))}

          {nodes.length === 0 && (
            <Stack alignItems="center" justifyContent="center" height="100%">
              <Typography color="text.secondary">
                Ajoutez des agents depuis la palette, reliez-les, puis exécutez.
              </Typography>
            </Stack>
          )}
        </Box>
      </Stack>

      {/* Workflows enregistrés */}
      {(wfData?.workflows || []).length > 0 && (
        <Stack direction="row" gap={1} mt={2} flexWrap="wrap">
          <Typography variant="body2" color="text.secondary" sx={{ alignSelf: 'center' }}>
            Ouvrir :
          </Typography>
          {wfData.workflows.map((w) => (
            <Chip key={w.id} label={w.name} variant={wf.id === w.id ? 'filled' : 'outlined'}
              color={wf.id === w.id ? 'primary' : 'default'} onClick={() => load(w)} />
          ))}
        </Stack>
      )}
    </Page>
  )
}
