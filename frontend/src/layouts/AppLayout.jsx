import { useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import {
  AppBar, Avatar, Box, Drawer, IconButton, List, ListItemButton, ListItemIcon,
  ListItemText, Stack, Toolbar, Tooltip, Typography,
} from '@mui/material'
import {
  AutoAwesome, Dashboard as DashIcon, Hub, DarkMode, LightMode,
  Logout, MenuBook, Memory, Science, Chat as ChatIcon, AccountTree,
} from '@mui/icons-material'
import { useAuth } from '../store/AuthContext'
import { useRealtime } from '../store/RealtimeProvider'
import { useColorMode } from '../main'

const WIDTH = 248
const NAV = [
  { to: '/', label: 'Dashboard', icon: <DashIcon /> },
  { to: '/llm', label: 'LLM Manager', icon: <Memory /> },
  { to: '/chat', label: 'Chat', icon: <ChatIcon /> },
  { to: '/agents', label: 'Agents', icon: <Hub /> },
  { to: '/workflows', label: 'Workflow Builder', icon: <AccountTree /> },
  { to: '/documents', label: 'Documents (RAG)', icon: <MenuBook /> },
  { to: '/scholar', label: 'Recherche sci.', icon: <Science /> },
]

export default function AppLayout() {
  const { pathname } = useLocation()
  const { user, logout } = useAuth()
  const { connected } = useRealtime()
  const { mode, toggle } = useColorMode()
  const [mobileOpen, setMobileOpen] = useState(false)

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Stack direction="row" alignItems="center" gap={1.2} sx={{ px: 2.5, py: 2.5 }}>
        <AutoAwesome color="primary" />
        <Typography variant="h6" fontWeight={700}>
          ResearchOS
        </Typography>
      </Stack>
      <List sx={{ px: 1.5, flex: 1 }}>
        {NAV.map((n) => {
          const active = pathname === n.to
          return (
            <ListItemButton
              key={n.to}
              component={Link}
              to={n.to}
              selected={active}
              onClick={() => setMobileOpen(false)}
              sx={{
                borderRadius: 2, mb: 0.5,
                '&.Mui-selected': { bgcolor: 'action.selected' },
              }}
            >
              <ListItemIcon sx={{ minWidth: 38, color: active ? 'primary.main' : 'inherit' }}>
                {n.icon}
              </ListItemIcon>
              <ListItemText primaryTypographyProps={{ fontSize: 14, fontWeight: active ? 600 : 500 }}>
                {n.label}
              </ListItemText>
            </ListItemButton>
          )
        })}
      </List>
    </Box>
  )

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar
        position="fixed"
        elevation={0}
        color="transparent"
        sx={{
          width: { md: `calc(100% - ${WIDTH}px)` }, ml: { md: `${WIDTH}px` },
          backdropFilter: 'blur(8px)', borderBottom: 1, borderColor: 'divider',
        }}
      >
        <Toolbar sx={{ justifyContent: 'flex-end', gap: 1 }}>
          <Tooltip title={connected ? 'Temps réel connecté' : 'Temps réel hors ligne'}>
            <Box sx={{
              width: 9, height: 9, borderRadius: '50%', mr: 0.5,
              bgcolor: connected ? 'success.main' : 'text.disabled',
              boxShadow: connected ? '0 0 8px' : 'none', color: 'success.main',
            }} />
          </Tooltip>
          <Tooltip title={mode === 'dark' ? 'Mode clair' : 'Mode sombre'}>
            <IconButton onClick={toggle}>{mode === 'dark' ? <LightMode /> : <DarkMode />}</IconButton>
          </Tooltip>
          <Tooltip title={user?.email || ''}>
            <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main', fontSize: 14 }}>
              {(user?.full_name || user?.email || '?')[0]?.toUpperCase()}
            </Avatar>
          </Tooltip>
          <Tooltip title="Déconnexion">
            <IconButton onClick={logout}>
              <Logout />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { md: WIDTH }, flexShrink: { md: 0 } }}>
        <Drawer
          variant="permanent"
          open
          sx={{
            display: { xs: 'none', md: 'block' },
            '& .MuiDrawer-paper': { width: WIDTH, borderRight: 1, borderColor: 'divider' },
          }}
        >
          {drawer}
        </Drawer>
      </Box>

      <Box component="main" sx={{ flexGrow: 1, p: { xs: 2, md: 4 }, mt: 8, maxWidth: 1200, mx: 'auto', width: '100%' }}>
        <Outlet />
      </Box>
    </Box>
  )
}
