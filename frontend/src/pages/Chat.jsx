import { useRef, useState } from 'react'
import {
  Box, Card, CardContent, Chip, IconButton, MenuItem, Paper, Stack,
  TextField, Typography, ToggleButton, ToggleButtonGroup,
} from '@mui/material'
import { Send } from '@mui/icons-material'
import Page from '../components/Page'
import { errMsg } from '../api/client'
import { useChat } from '../hooks/useApi'

const STRATEGIES = ['balanced', 'cost', 'speed', 'quality', 'privacy']

export default function Chat() {
  const chat = useChat()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [strategy, setStrategy] = useState('balanced')
  const endRef = useRef(null)

  const send = async () => {
    if (!input.trim()) return
    const next = [...messages, { role: 'user', content: input }]
    setMessages(next)
    setInput('')
    try {
      const r = await chat.mutateAsync({ messages: next.map((m) => ({ role: m.role, content: m.content })), strategy })
      setMessages([...next, { role: 'assistant', content: r.content, routing: r.routing, usage: r.usage }])
    } catch (e) {
      setMessages([...next, { role: 'assistant', content: `⚠️ ${errMsg(e)}`, error: true }])
    }
    setTimeout(() => endRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
  }

  return (
    <Page
      title="Chat"
      subtitle="Complétion routée automatiquement vers le meilleur modèle"
      action={
        <ToggleButtonGroup size="small" exclusive value={strategy} onChange={(_, v) => v && setStrategy(v)}>
          {STRATEGIES.map((s) => <ToggleButton key={s} value={s}>{s}</ToggleButton>)}
        </ToggleButtonGroup>
      }
    >
      <Card sx={{ height: 'calc(100vh - 260px)', display: 'flex', flexDirection: 'column' }}>
        <CardContent sx={{ flex: 1, overflowY: 'auto' }}>
          {messages.length === 0 && (
            <Stack height="100%" alignItems="center" justifyContent="center">
              <Typography color="text.secondary">Posez une question — le routeur choisira le modèle selon « {strategy} ».</Typography>
            </Stack>
          )}
          <Stack gap={2}>
            {messages.map((m, i) => (
              <Stack key={i} alignItems={m.role === 'user' ? 'flex-end' : 'flex-start'}>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 1.5, px: 2, maxWidth: '80%',
                    bgcolor: m.role === 'user' ? 'primary.main' : 'background.paper',
                    color: m.role === 'user' ? '#fff' : 'text.primary',
                    borderColor: m.error ? 'error.main' : 'divider',
                  }}
                >
                  <Typography variant="body2" whiteSpace="pre-wrap">{m.content}</Typography>
                </Paper>
                {m.routing && (
                  <Stack direction="row" gap={0.5} mt={0.5}>
                    <Chip size="small" variant="outlined" label={`${m.routing.chosen_model}`} />
                    <Chip size="small" variant="outlined" label={`${m.usage.latency_ms} ms`} />
                    <Chip size="small" variant="outlined" label={`$${m.usage.cost_usd}`} />
                  </Stack>
                )}
              </Stack>
            ))}
            <div ref={endRef} />
          </Stack>
        </CardContent>
        <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
          <Stack direction="row" gap={1}>
            <TextField
              fullWidth size="small" placeholder="Votre message…" value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send())}
            />
            <IconButton color="primary" onClick={send} disabled={chat.isPending}><Send /></IconButton>
          </Stack>
        </Box>
      </Card>
    </Page>
  )
}
