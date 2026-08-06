import axios from 'axios'

// Client HTTP unique. Le token JWT est injecté automatiquement ; un 401 purge
// la session et renvoie vers /login.
export const TOKEN_KEY = 'researchos_token'

export const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && !location.pathname.startsWith('/login')) {
      localStorage.removeItem(TOKEN_KEY)
      location.href = '/login'
    }
    return Promise.reject(err)
  },
)

// Extrait un message d'erreur lisible depuis une réponse flask-smorest.
export const errMsg = (e) => {
  // Erreur réseau (pas de réponse) = backend injoignable : message actionnable.
  if (e?.code === 'ERR_NETWORK' || e?.message === 'Network Error' || !e?.response) {
    return "Backend injoignable — démarrez-le (port 5000) : `python wsgi.py` dans backend/."
  }
  return (
    e?.response?.data?.message ||
    e?.response?.data?.errors?.json?.[Object.keys(e.response.data.errors.json)[0]]?.[0] ||
    e?.message ||
    'Erreur inconnue'
  )
}
