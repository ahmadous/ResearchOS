import { createTheme } from '@mui/material/styles'

// Thème premium inspiré de Linear/Notion : surfaces neutres, bordures subtiles,
// coins arrondis, typographie Inter. Décliné en sombre (défaut) et clair.
const shared = {
  typography: {
    fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
    h4: { fontWeight: 700, letterSpacing: '-0.02em' },
    h5: { fontWeight: 700, letterSpacing: '-0.01em' },
    h6: { fontWeight: 600 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  shape: { borderRadius: 10 },
}

const components = (mode) => ({
  MuiCssBaseline: {
    styleOverrides: {
      '*::-webkit-scrollbar': { width: 8, height: 8 },
      '*::-webkit-scrollbar-thumb': {
        background: mode === 'dark' ? '#2a2f3a' : '#d0d5dd', borderRadius: 8,
      },
    },
  },
  MuiPaper: {
    styleOverrides: {
      root: { backgroundImage: 'none' },
      outlined: {
        borderColor: mode === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
      },
    },
  },
  MuiButton: { defaultProps: { disableElevation: true } },
  MuiCard: { defaultProps: { variant: 'outlined' } },
})

export const buildTheme = (mode = 'dark') =>
  createTheme({
    ...shared,
    palette:
      mode === 'dark'
        ? {
            mode: 'dark',
            primary: { main: '#6366f1' },
            secondary: { main: '#22d3ee' },
            success: { main: '#34d399' },
            background: { default: '#0b0d12', paper: '#12151c' },
            text: { primary: '#e6e9ef', secondary: '#9aa3b2' },
            divider: 'rgba(255,255,255,0.08)',
          }
        : {
            mode: 'light',
            primary: { main: '#4f46e5' },
            secondary: { main: '#0891b2' },
            background: { default: '#f7f8fa', paper: '#ffffff' },
            text: { primary: '#111827', secondary: '#6b7280' },
            divider: 'rgba(0,0,0,0.08)',
          },
    components: components(mode),
  })
