import { motion } from 'framer-motion'
import { Box, Stack, Typography } from '@mui/material'

// Enveloppe animée + en-tête de page réutilisable.
export default function Page({ title, subtitle, action, children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
    >
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        alignItems={{ xs: 'stretch', sm: 'center' }}
        justifyContent="space-between"
        gap={2}
        mb={3}
      >
        <Box>
          <Typography variant="h4">{title}</Typography>
          {subtitle && (
            <Typography variant="body2" color="text.secondary" mt={0.5}>
              {subtitle}
            </Typography>
          )}
        </Box>
        {action && (
          // Sur mobile : les actions passent sous le titre et peuvent aller à la ligne.
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, '& > *': { flexShrink: 0 } }}>
            {action}
          </Box>
        )}
      </Stack>
      {children}
    </motion.div>
  )
}
