import { useEffect, useRef, useState } from 'react'
import {
  Box, Button, Card, CardContent, Chip, IconButton, MenuItem, Paper, Stack,
  TextField, Typography, ToggleButton, ToggleButtonGroup,
} from '@mui/material'
import { Send, Bolt, FactCheck, Psychology, BookmarkAdd } from '@mui/icons-material'
import Page from '../components/Page'
import { TOKEN_KEY, errMsg } from '../api/client'
import { useModels, useEvaluate, useAddMemory } from '../hooks/useApi'
import { useRealtime } from '../store/RealtimeProvider'

const VERDICT = {
  reliable: { color: 'success', label: 'Fiable' },
  uncertain: { color: 'warning', label: 'Incertain' },
  unreliable: { color: 'error', label: 'Peu fiable' },
}

const STRATEGIES = ['balanced', 'cost', 'speed', 'quality', 'privacy']

export default function Chat() {
  const { socket } = useRealtime()
  const { data: modelsData } = useModels()
  const evaluate = useEvaluate()
  const addMemory = useAddMemory()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [strategy, setStrategy] = useState('balanced')
  const [pinned, setPinned] = useState('')     // '' = routage auto
  const [useMemory, setUseMemory] = useState(true)
  const [streaming, setStreaming] = useState(false)
  const endRef = useRef(null)
  const t0 = useRef(0)

  const models = modelsData?.models || []

  // Abonnement aux événements de streaming.
  useEffect(() => {
    if (!socket) return
    const patchLast = (fn) =>
      setMessages((m) => {
        const copy = [...m]
        const last = copy[copy.length - 1]
        if (last && last.role === 'assistant') copy[copy.length - 1] = fn(last)
        return copy
      })
    const onStart = (e) => patchLast((l) => ({ ...l, model: e.model, provider: e.provider }))
    const onToken = (e) => patchLast((l) => ({ ...l, content: l.content + e.text }))
    const onDone = () => {
      patchLast((l) => ({ ...l, ms: Math.round(performance.now() - t0.current) }))
      setStreaming(false)
    }
    const onErr = (e) => { patchLast((l) => ({ ...l, content: `⚠️ ${e.message}`, error: true })); setStreaming(false) }
    socket.on('chat_start', onStart)
    socket.on('chat_token', onToken)
    socket.on('chat_done', onDone)
    socket.on('chat_error', onErr)
    return () => {
      socket.off('chat_start', onStart); socket.off('chat_token', onToken)
      socket.off('chat_done', onDone); socket.off('chat_error', onErr)
    }
  }, [socket])

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const patchAt = (index, patch) =>
    setMessages((m) => m.map((x, i) => (i === index ? { ...x, ...patch } : x)))

  // Vérifie la fiabilité d'une réponse (question = message user précédent).
  const doEvaluate = async (index) => {
    const answer = messages[index]?.content
    const question = messages.slice(0, index).reverse().find((m) => m.role === 'user')?.content || ''
    patchAt(index, { evaluating: true, evalError: null })
    try {
      const res = await evaluate.mutateAsync({ question, answer, pinned_model: pinned || undefined })
      patchAt(index, { evaluating: false, eval: res })
    } catch (e) {
      patchAt(index, { evaluating: false, evalError: errMsg(e) })
    }
  }

  const send = () => {
    if (!input.trim() || streaming) return
    if (!socket) return
    const history = [...messages, { role: 'user', content: input }]
    setMessages([...history, { role: 'assistant', content: '' }])   // placeholder streamé
    setInput('')
    setStreaming(true)
    t0.current = performance.now()
    socket.emit('chat_stream', {
      token: localStorage.getItem(TOKEN_KEY),
      messages: history.map((m) => ({ role: m.role, content: m.content })),
      strategy,
      pinned_model: pinned || undefined,
      use_memory: useMemory,
    })
  }

  const memorize = (index) => {
    const content = messages[index]?.content
    if (content) addMemory.mutate({ content, kind: 'note' })
  }

  return (
    <Page
      title="Chat"
      subtitle="Réponse en streaming, routée automatiquement (ou modèle imposé)"
      action={
        <Stack direction="row" gap={1} alignItems="center">
          <ToggleButton size="small" value="mem" selected={useMemory}
            onChange={() => setUseMemory((v) => !v)}
            title={useMemory ? 'Mémoire active' : 'Mémoire désactivée'}>
            <Psychology fontSize="small" />
          </ToggleButton>
          <TextField select size="small" value={pinned} onChange={(e) => setPinned(e.target.value)}
            sx={{ minWidth: 150 }}
            SelectProps={{ displayEmpty: true }}>
            <MenuItem value=""><em>Auto ({strategy})</em></MenuItem>
            {models.map((m) => (
              <MenuItem key={m.id} value={m.id}>
                {m.id}{m.input_cost === 0 ? ' ⚡' : ''}
              </MenuItem>
            ))}
          </TextField>
          <ToggleButtonGroup size="small" exclusive value={strategy}
            onChange={(_, v) => v && setStrategy(v)} disabled={!!pinned}>
            {STRATEGIES.map((s) => <ToggleButton key={s} value={s}>{s}</ToggleButton>)}
          </ToggleButtonGroup>
        </Stack>
      }
    >
      <Card sx={{ height: 'calc(100vh - 260px)', display: 'flex', flexDirection: 'column' }}>
        <CardContent sx={{ flex: 1, overflowY: 'auto' }}>
          {messages.length === 0 && (
            <Stack height="100%" alignItems="center" justifyContent="center" gap={1}>
              <Bolt color="primary" />
              <Typography color="text.secondary">
                Posez une question — la réponse s'affiche en direct.
                {pinned ? ` Modèle imposé : ${pinned}.` : ` Routage « ${strategy} ».`}
              </Typography>
            </Stack>
          )}
          <Stack gap={2}>
            {messages.map((m, i) => (
              <Stack key={i} alignItems={m.role === 'user' ? 'flex-end' : 'flex-start'}>
                <Paper variant="outlined" sx={{
                  p: 1.5, px: 2, maxWidth: '80%',
                  bgcolor: m.role === 'user' ? 'primary.main' : 'background.paper',
                  color: m.role === 'user' ? '#fff' : 'text.primary',
                  borderColor: m.error ? 'error.main' : 'divider',
                }}>
                  <Typography variant="body2" whiteSpace="pre-wrap">
                    {m.content || (streaming && i === messages.length - 1 ? '…' : '')}
                  </Typography>
                </Paper>
                {m.role === 'assistant' && m.model && (
                  <Stack gap={0.5} mt={0.5} maxWidth="80%">
                    <Stack direction="row" gap={0.5} alignItems="center" flexWrap="wrap">
                      <Chip size="small" variant="outlined" label={m.model} />
                      {m.ms != null && <Chip size="small" variant="outlined" label={`${m.ms} ms`} />}
                      {m.ms != null && !m.error && !m.eval && (
                        <Button size="small" startIcon={<FactCheck />} onClick={() => doEvaluate(i)}
                          disabled={m.evaluating} sx={{ minWidth: 0, py: 0 }}>
                          {m.evaluating ? 'Vérification…' : 'Vérifier'}
                        </Button>
                      )}
                      {m.eval && (
                        <Chip size="small" color={VERDICT[m.eval.verdict].color}
                          label={`${VERDICT[m.eval.verdict].label} · ${m.eval.confidence}%`} />
                      )}
                      {m.ms != null && !m.error && (
                        <Button size="small" startIcon={<BookmarkAdd />} onClick={() => memorize(i)}
                          sx={{ minWidth: 0, py: 0 }}>Mémoriser</Button>
                      )}
                    </Stack>
                    {m.evalError && <Typography variant="caption" color="error.main">{m.evalError}</Typography>}
                    {m.eval && (m.eval.issues.length > 0 || m.eval.correction) && (
                      <Paper variant="outlined" sx={{ p: 1, mt: 0.5 }}>
                        {m.eval.issues.length > 0 && (
                          <Box>
                            <Typography variant="caption" fontWeight={600}>Points à vérifier :</Typography>
                            <ul style={{ margin: '2px 0 0', paddingLeft: 18 }}>
                              {m.eval.issues.map((it, k) => (
                                <li key={k}><Typography variant="caption">{it}</Typography></li>
                              ))}
                            </ul>
                          </Box>
                        )}
                        {m.eval.correction && (
                          <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
                            💡 {m.eval.correction}
                          </Typography>
                        )}
                      </Paper>
                    )}
                  </Stack>
                )}
              </Stack>
            ))}
            <div ref={endRef} />
          </Stack>
        </CardContent>
        <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
          <Stack direction="row" gap={1}>
            <TextField fullWidth size="small" placeholder="Votre message…" value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send())} />
            <IconButton color="primary" onClick={send} disabled={streaming || !socket}><Send /></IconButton>
          </Stack>
        </Box>
      </Card>
    </Page>
  )
}
