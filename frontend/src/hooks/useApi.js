import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

const get = (url) => () => api.get(url).then((r) => r.data)

// --- LLM Manager ---
export const useModels = () =>
  useQuery({ queryKey: ['models'], queryFn: get('/llm/models') })

export const useProviders = () =>
  useQuery({ queryKey: ['providers'], queryFn: get('/llm/providers') })

export const useAvailableProviders = () =>
  useQuery({ queryKey: ['providers-available'], queryFn: get('/llm/providers/available') })

export const useOllama = () =>
  useQuery({ queryKey: ['ollama'], queryFn: get('/llm/ollama'), refetchInterval: 15000 })

export const useConsumption = () =>
  useQuery({ queryKey: ['consumption'], queryFn: get('/llm/consumption') })

export const useAddProvider = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body) => api.post('/llm/providers', body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['providers'] })
      qc.invalidateQueries({ queryKey: ['models'] })
    },
  })
}

export const useDeleteProvider = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => api.delete(`/llm/providers/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['providers'] })
      qc.invalidateQueries({ queryKey: ['models'] })
    },
  })
}

export const useTestModel = () =>
  useMutation({ mutationFn: (model) => api.post('/llm/test', { model }).then((r) => r.data) })

// --- Chat ---
export const useChat = () =>
  useMutation({ mutationFn: (body) => api.post('/chat/complete', body).then((r) => r.data) })

// --- Memory Engine ---
export const useMemories = (scope) =>
  useQuery({ queryKey: ['memories', scope || 'all'],
             queryFn: get(`/memory${scope ? `?scope=${scope}` : ''}`) })

export const useAddMemory = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body) => api.post('/memory', body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['memories'] }),
  })
}

export const useDeleteMemory = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => api.delete(`/memory/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['memories'] }),
  })
}

export const useRecallMemory = () =>
  useMutation({ mutationFn: (body) => api.post('/memory/recall', body).then((r) => r.data) })

// --- Évaluation (fact-check) ---
export const useEvaluate = () =>
  useMutation({ mutationFn: (body) => api.post('/evaluate', body).then((r) => r.data) })

// --- Agents ---
export const useAgents = () =>
  useQuery({ queryKey: ['agents'], queryFn: get('/agents') })
export const useRunAgent = () =>
  useMutation({
    mutationFn: ({ name, task, goal }) =>
      api.post(`/agents/${name}/run`, { task, goal }).then((r) => r.data),
  })

// --- RAG ---
export const useDocuments = () =>
  useQuery({ queryKey: ['documents'], queryFn: get('/rag/documents') })
export const useIngest = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body) => api.post('/rag/documents', body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['documents'] }),
  })
}
export const useRagQuery = () =>
  useMutation({ mutationFn: (body) => api.post('/rag/query', body).then((r) => r.data) })

// --- Knowledge Graph ---
export const useGraph = () =>
  useQuery({ queryKey: ['graph'], queryFn: get('/graph') })

export const useExtractGraph = () =>
  useMutation({ mutationFn: (body) => api.post('/graph/extract', body).then((r) => r.data) })

export const useClearGraph = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.delete('/graph'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['graph'] }),
  })
}

// --- Workflows ---
export const useWorkflows = () =>
  useQuery({ queryKey: ['workflows'], queryFn: get('/workflows') })

export const useSaveWorkflow = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, name, graph }) =>
      (id ? api.put(`/workflows/${id}`, { name, graph })
          : api.post('/workflows', { name, graph })).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workflows'] }),
  })
}

export const useRunWorkflow = () =>
  useMutation({ mutationFn: (id) => api.post(`/workflows/${id}/run`).then((r) => r.data) })

// --- Scholar ---
export const useScholarSearch = () =>
  useMutation({ mutationFn: (body) => api.post('/scholar/search', body).then((r) => r.data) })
export const useImportPaper = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (paper) => api.post('/scholar/import', paper).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['documents'] }),
  })
}
