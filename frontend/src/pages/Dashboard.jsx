import { Card, CardContent, Grid, Stack, Typography, Box, useTheme } from '@mui/material'
import { BarChart, Bar, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from 'recharts'
import { Memory, MenuBook, Paid, Hub } from '@mui/icons-material'
import Page from '../components/Page'
import { useConsumption, useModels, useDocuments, useProviders } from '../hooks/useApi'

function Stat({ icon, label, value, color }) {
  return (
    <Card>
      <CardContent>
        <Stack direction="row" alignItems="center" gap={2}>
          <Box sx={{ p: 1.2, borderRadius: 2, bgcolor: `${color}.main`, color: '#fff', display: 'flex' }}>
            {icon}
          </Box>
          <Box>
            <Typography variant="h5">{value}</Typography>
            <Typography variant="body2" color="text.secondary">{label}</Typography>
          </Box>
        </Stack>
      </CardContent>
    </Card>
  )
}

export default function Dashboard() {
  const theme = useTheme()
  const { data: cons } = useConsumption()
  const { data: models } = useModels()
  const { data: docs } = useDocuments()
  const { data: providers } = useProviders()

  const summary = cons?.summary || {}
  const byModel = (cons?.by_model || []).map((m) => ({ name: m.model, cost: m.cost_usd, calls: m.calls }))

  return (
    <Page title="Dashboard" subtitle="Vue d'ensemble de votre espace de recherche">
      <Grid container spacing={2.5}>
        <Grid item xs={12} sm={6} md={3}>
          <Stat icon={<Memory />} color="primary" label="Modèles disponibles" value={models?.models?.length ?? '—'} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Stat icon={<Hub />} color="secondary" label="Fournisseurs" value={providers?.length ?? '—'} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Stat icon={<MenuBook />} color="success" label="Documents indexés" value={docs?.documents?.length ?? '—'} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Stat icon={<Paid />} color="warning" label="Coût cumulé (USD)" value={(summary.total_cost_usd ?? 0).toFixed(4)} />
        </Grid>

        <Grid item xs={12} md={8}>
          <Card sx={{ height: 360 }}>
            <CardContent sx={{ height: '100%' }}>
              <Typography variant="h6" mb={2}>Coût par modèle</Typography>
              {byModel.length ? (
                <ResponsiveContainer width="100%" height="85%">
                  <BarChart data={byModel}>
                    <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
                    <XAxis dataKey="name" tick={{ fontSize: 11, fill: theme.palette.text.secondary }} />
                    <YAxis tick={{ fontSize: 11, fill: theme.palette.text.secondary }} />
                    <Tooltip contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }} />
                    <Bar dataKey="cost" fill={theme.palette.primary.main} radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Stack height="80%" alignItems="center" justifyContent="center">
                  <Typography color="text.secondary">Aucun appel enregistré pour l'instant.</Typography>
                </Stack>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card sx={{ height: 360 }}>
            <CardContent>
              <Typography variant="h6" mb={2}>Activité</Typography>
              <Stack gap={1.5}>
                <Row label="Appels LLM" value={summary.calls ?? 0} />
                <Row label="Tokens cumulés" value={(summary.total_tokens ?? 0).toLocaleString()} />
                <Row label="Latence moyenne" value={`${(summary.avg_latency_ms ?? 0).toFixed(0)} ms`} />
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Page>
  )
}

const Row = ({ label, value }) => (
  <Stack direction="row" justifyContent="space-between">
    <Typography color="text.secondary">{label}</Typography>
    <Typography fontWeight={600}>{value}</Typography>
  </Stack>
)
