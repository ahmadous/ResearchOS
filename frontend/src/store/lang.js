// Préférence de langue de réponse (persistée). 'auto' = détection automatique.
export const LANGS = [
  { code: 'auto', label: 'Auto (détecter)' },
  { code: 'fr', label: 'Français' },
  { code: 'en', label: 'English' },
  { code: 'es', label: 'Español' },
  { code: 'it', label: 'Italiano' },
  { code: 'de', label: 'Deutsch' },
  { code: 'pt', label: 'Português' },
  { code: 'ar', label: 'العربية' },
  { code: 'wo', label: 'Wolof' },
]

export const getLang = () => localStorage.getItem('researchos_lang') || 'auto'
export const setLang = (code) => localStorage.setItem('researchos_lang', code)
