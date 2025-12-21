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

  const response = await api.post('/subtitle/', formData, {
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

// ============ Audio Separator API ============

// Submit audio separation job
export const submitSeparatorJob = async (file, options) => {
  const formData = new FormData()
  formData.append('audio_file', file)

  Object.keys(options).forEach(key => {
    if (options[key] !== null && options[key] !== undefined && options[key] !== '') {
      formData.append(key, options[key])
    }
  })

  const response = await api.post('/separator/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return response.data // { job_id, status, message }
}

// Get separator job status
export const getSeparatorJobStatus = async (jobId) => {
  const response = await api.get(`/separator/jobs/${jobId}`)
  return response.data
}

// Download audio file from base64
export const downloadAudio = (base64Data, filename, format) => {
  const binaryString = atob(base64Data)
  const bytes = new Uint8Array(binaryString.length)
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i)
  }

  const mimeTypes = {
    mp3: 'audio/mpeg',
    wav: 'audio/wav',
    flac: 'audio/flac',
  }

  const blob = new Blob([bytes], { type: mimeTypes[format] || 'audio/mpeg' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

// ============ TTS API ============

// Get available TTS voices
export const getTTSVoices = async () => {
  const response = await api.get('/tts/voices')
  return response.data
}

// Get available TTS engines
export const getTTSEngines = async () => {
  const response = await api.get('/tts/engines')
  return response.data
}

// Get TTS presets
export const getTTSPresets = async () => {
  const response = await api.get('/tts/presets')
  return response.data
}

// Synthesize text to speech
export const synthesizeTTS = async (options) => {
  const response = await api.post('/tts/synthesize', options)
  return response.data
}

// Play audio from base64
export const playAudioFromBase64 = (base64Data, format = 'mp3') => {
  const mimeTypes = {
    mp3: 'audio/mpeg',
    wav: 'audio/wav',
  }

  const audioSrc = `data:${mimeTypes[format] || 'audio/mpeg'};base64,${base64Data}`
  const audio = new Audio(audioSrc)
  return audio
}

// Download TTS audio
export const downloadTTSAudio = (base64Data, filename, format = 'mp3') => {
  const binaryString = atob(base64Data)
  const bytes = new Uint8Array(binaryString.length)
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i)
  }

  const mimeTypes = {
    mp3: 'audio/mpeg',
    wav: 'audio/wav',
  }

  const blob = new Blob([bytes], { type: mimeTypes[format] || 'audio/mpeg' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export default api
