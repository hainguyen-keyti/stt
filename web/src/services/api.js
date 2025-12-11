import axios from 'axios'

// In production, API is served from same origin
// In development, Vite proxy handles routing
const API_BASE_URL = ''

const api = axios.create({
  baseURL: API_BASE_URL,
})

// Submit subtitle generation job
export const submitSubtitleJob = async (file, options) => {
  const formData = new FormData()
  formData.append('audio_file', file)

  Object.keys(options).forEach(key => {
    if (options[key] !== null && options[key] !== undefined && options[key] !== '') {
      formData.append(key, options[key])
    }
  })

  const response = await api.post('/subtitle', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return response.data // { job_id, status, message }
}

// Get job status
export const getJobStatus = async (jobId) => {
  const response = await api.get(`/subtitle/jobs/${jobId}`)
  return response.data
}

// List all jobs
export const listJobs = async () => {
  const response = await api.get('/subtitle/jobs')
  return response.data
}

// Download subtitle file
export const downloadSubtitle = (content, filename) => {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

// Presets API - returns full preset data
export const getPresets = async () => {
  const response = await api.get('/presets/')
  return response.data
}

// Metrics API
export const getMetrics = async () => {
  const response = await api.get('/metrics')
  return response.data
}

// Health API
export const getHealth = async () => {
  const response = await api.get('/health')
  return response.data
}

export default api
