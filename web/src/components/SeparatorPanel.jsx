import React, { useState, useRef } from 'react'
import { submitSeparatorJob, getSeparatorJobStatus, downloadAudio } from '../services/api'
import '../styles/Panel.css'

// Setting descriptions
const DESCRIPTIONS = {
  vocal_volume: 'Âm lượng vocal (0.0 = tắt tiếng, 1.0 = giữ nguyên, 2.0 = gấp đôi). Đặt 0 để tạo nhạc nền/karaoke.',
  instrumental_volume: 'Âm lượng nhạc nền (0.0 = tắt tiếng, 1.0 = giữ nguyên, 2.0 = gấp đôi). Đặt 0 để lấy vocal only.',
  output_format: 'Định dạng file xuất. MP3 nhỏ gọn, WAV chất lượng cao, FLAC nén không mất chất lượng.',
  model: 'Chọn model tách âm thanh. Fast nhanh nhất, Quality chất lượng cao nhất.',
}

// Separation models
const MODELS = [
  {
    id: 'fast',
    name: 'Fast',
    description: '~5-10 giây, chất lượng ổn',
    icon: '⚡',
  },
  {
    id: 'balanced',
    name: 'Balanced',
    description: '~20 giây, chất lượng tốt',
    icon: '⚖️',
  },
  {
    id: 'quality',
    name: 'Quality',
    description: '~2 phút, chất lượng cao nhất',
    icon: '🎵',
  },
]

const POLL_INTERVAL = 5000 // 5 seconds

function SeparatorPanel() {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  // Job state
  const [jobId, setJobId] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [progress, setProgress] = useState(0)
  const pollIntervalRef = useRef(null)

  // Settings
  const [options, setOptions] = useState({
    vocal_volume: 0.0,
    instrumental_volume: 1.0,
    output_format: 'mp3',
    model: 'fast',
  })

  const startPolling = (jobId) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
    }

    pollIntervalRef.current = setInterval(async () => {
      try {
        const status = await getSeparatorJobStatus(jobId)
        setJobStatus(status.status)
        setProgress(status.progress || 0)

        if (status.status === 'completed') {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
          setLoading(false)

          if (status.result) {
            setResult({
              format: status.result.format,
              filename: status.result.filename,
              data: status.result.data,
              size_bytes: status.result.size_bytes,
              metadata: status.result.metadata,
            })
          }
        } else if (status.status === 'failed') {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
          setLoading(false)
          setError(status.error || 'Job failed')
        }
      } catch (err) {
        console.error('Polling error:', err)
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
        setLoading(false)
        setError('Failed to check job status')
      }
    }, POLL_INTERVAL)
  }

  const handleFileChange = (e) => {
    setFile(e.target.files[0])
    setError(null)
    setResult(null)
    setJobId(null)
    setJobStatus(null)
    setProgress(0)
  }

  const handleOptionChange = (key, value) => {
    setOptions(prev => ({ ...prev, [key]: value }))
    setResult(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) {
      setError('Please select an audio file')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)
    setJobId(null)
    setJobStatus('pending')
    setProgress(0)

    try {
      const response = await submitSeparatorJob(file, options)
      setJobId(response.job_id)
      setJobStatus(response.status)
      startPolling(response.job_id)
    } catch (err) {
      setLoading(false)
      setError(err.response?.data?.detail || err.message || 'Failed to submit job')
    }
  }

  const handleDownload = () => {
    if (result && result.data) {
      downloadAudio(result.data, result.filename, result.format)
    }
  }

  const getStatusText = () => {
    switch (jobStatus) {
      case 'pending':
        return 'Waiting to start...'
      case 'processing':
        if (progress <= 10) return 'Starting...'
        if (progress <= 30) return 'Loading separator model...'
        if (progress <= 90) return 'Separating audio...'
        return 'Mixing output...'
      case 'completed':
        return 'Completed!'
      case 'failed':
        return 'Failed'
      default:
        return 'Processing...'
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Audio Separator</h2>
        <p className="description">
          Tách vocal và instrumental từ audio, điều chỉnh âm lượng và mix lại.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="form">
        {/* File Upload */}
        <div className="form-section">
          <h3>Audio File</h3>
          <div className="file-upload">
            <input
              type="file"
              accept=".mp3,.wav,.m4a,.flac,.ogg,.opus,.webm"
              onChange={handleFileChange}
              id="separator-file"
              disabled={loading}
            />
            <label htmlFor="separator-file" className="file-label">
              {file ? file.name : 'Choose Audio File'}
            </label>
            <p className="hint">Supported: MP3, WAV, M4A, FLAC, OGG, OPUS, WebM (Max: 500MB)</p>
          </div>
        </div>

        {/* Volume Settings */}
        <div className="form-section">
          <h3>Volume Settings</h3>
          <div className="form-grid">
            <div className="form-group">
              <label>Vocal Volume: {options.vocal_volume.toFixed(1)}</label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={options.vocal_volume}
                onChange={(e) => handleOptionChange('vocal_volume', parseFloat(e.target.value))}
                disabled={loading}
                className="slider"
              />
              <div className="slider-labels">
                <span>Mute</span>
                <span>Original</span>
                <span>2x</span>
              </div>
              <p className="field-desc">{DESCRIPTIONS.vocal_volume}</p>
            </div>

            <div className="form-group">
              <label>Instrumental Volume: {options.instrumental_volume.toFixed(1)}</label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={options.instrumental_volume}
                onChange={(e) => handleOptionChange('instrumental_volume', parseFloat(e.target.value))}
                disabled={loading}
                className="slider"
              />
              <div className="slider-labels">
                <span>Mute</span>
                <span>Original</span>
                <span>2x</span>
              </div>
              <p className="field-desc">{DESCRIPTIONS.instrumental_volume}</p>
            </div>
          </div>

          {/* Visual indicator */}
          <div className="volume-preview">
            <div className="volume-bar">
              <div className="volume-label">Vocal</div>
              <div className="volume-indicator">
                <div
                  className="volume-fill vocal"
                  style={{ width: `${Math.min(options.vocal_volume * 50, 100)}%` }}
                />
              </div>
              <div className="volume-value">{(options.vocal_volume * 100).toFixed(0)}%</div>
            </div>
            <div className="volume-bar">
              <div className="volume-label">Instrumental</div>
              <div className="volume-indicator">
                <div
                  className="volume-fill instrumental"
                  style={{ width: `${Math.min(options.instrumental_volume * 50, 100)}%` }}
                />
              </div>
              <div className="volume-value">{(options.instrumental_volume * 100).toFixed(0)}%</div>
            </div>
          </div>
        </div>

        {/* Output Format */}
        <div className="form-section">
          <h3>Output Format</h3>
          <div className="format-grid">
            <label className={`format-card ${options.output_format === 'mp3' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="output_format"
                value="mp3"
                checked={options.output_format === 'mp3'}
                onChange={(e) => handleOptionChange('output_format', e.target.value)}
                disabled={loading}
              />
              <div className="format-content">
                <div className="format-icon">MP3</div>
                <div className="format-name">MP3</div>
                <div className="format-desc">Compact, 320kbps</div>
              </div>
            </label>

            <label className={`format-card ${options.output_format === 'wav' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="output_format"
                value="wav"
                checked={options.output_format === 'wav'}
                onChange={(e) => handleOptionChange('output_format', e.target.value)}
                disabled={loading}
              />
              <div className="format-content">
                <div className="format-icon">WAV</div>
                <div className="format-name">WAV</div>
                <div className="format-desc">Lossless, large</div>
              </div>
            </label>

            <label className={`format-card ${options.output_format === 'flac' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="output_format"
                value="flac"
                checked={options.output_format === 'flac'}
                onChange={(e) => handleOptionChange('output_format', e.target.value)}
                disabled={loading}
              />
              <div className="format-content">
                <div className="format-icon">FLAC</div>
                <div className="format-name">FLAC</div>
                <div className="format-desc">Lossless, compressed</div>
              </div>
            </label>
          </div>
          <p className="field-desc">{DESCRIPTIONS.output_format}</p>
        </div>

        {/* Model Selection */}
        <div className="form-section">
          <h3>Separation Model</h3>
          <div className="format-grid">
            {MODELS.map(model => (
              <label
                key={model.id}
                className={`format-card ${options.model === model.id ? 'selected' : ''}`}
              >
                <input
                  type="radio"
                  name="model"
                  value={model.id}
                  checked={options.model === model.id}
                  onChange={(e) => handleOptionChange('model', e.target.value)}
                  disabled={loading}
                />
                <div className="format-content">
                  <div className="format-icon">{model.icon}</div>
                  <div className="format-name">{model.name}</div>
                  <div className="format-desc">{model.description}</div>
                </div>
              </label>
            ))}
          </div>
          <p className="field-desc">{DESCRIPTIONS.model}</p>
        </div>

        {/* Submit Button */}
        <button type="submit" className="submit-btn" disabled={loading || !file}>
          {loading ? 'Processing...' : 'Process Audio'}
        </button>
      </form>

      {/* Progress Display */}
      {loading && jobId && (
        <div className="progress-section">
          <div className="progress-header">
            <span className="job-id">Job: {jobId}</span>
            <span className="progress-text">{getStatusText()}</span>
          </div>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="progress-percent">{progress}%</div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="error-box">
          <h4>Error</h4>
          <p>{typeof error === 'string' ? error : JSON.stringify(error, null, 2)}</p>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="result-section">
          <div className="result-header">
            <h3>Result</h3>
            <button onClick={handleDownload} className="download-btn">
              Download {result.format.toUpperCase()}
            </button>
          </div>

          <div className="result-stats">
            <div className="stat-item">
              <span className="stat-label">Filename:</span>
              <span className="stat-value">{result.filename}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Format:</span>
              <span className="stat-value">{result.format.toUpperCase()}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Size:</span>
              <span className="stat-value">{formatFileSize(result.size_bytes)}</span>
            </div>
            {result.metadata && (
              <>
                <div className="stat-item">
                  <span className="stat-label">Processing Time:</span>
                  <span className="stat-value">{(result.metadata.processing_time_ms / 1000).toFixed(1)}s</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Vocal Volume:</span>
                  <span className="stat-value">{(result.metadata.vocal_volume * 100).toFixed(0)}%</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Instrumental Volume:</span>
                  <span className="stat-value">{(result.metadata.instrumental_volume * 100).toFixed(0)}%</span>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default SeparatorPanel
