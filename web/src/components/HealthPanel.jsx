import React, { useState, useEffect } from 'react'
import { getHealth } from '../services/api'
import '../styles/Panel.css'

function HealthPanel() {
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const fetchHealth = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await getHealth()
      setHealth(data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch health status')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHealth()
  }, [])

  useEffect(() => {
    let interval
    if (autoRefresh) {
      interval = setInterval(fetchHealth, 3000) // Refresh every 3 seconds
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [autoRefresh])

  const formatUptime = (seconds) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)

    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`
    } else {
      return `${secs}s`
    }
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>💚 Service Health</h2>
        <p className="description">
          Monitor service health status, uptime, and system information.
        </p>
        <div className="header-actions">
          <button onClick={fetchHealth} className="refresh-btn" disabled={loading}>
            {loading ? '⏳ Checking...' : '🔄 Refresh'}
          </button>
          <label className="auto-refresh-label">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh (3s)
          </label>
        </div>
      </div>

      {error && (
        <div className="error-box">
          <div className="error-header">
            <span className="status-badge error">🔴 Service Offline</span>
          </div>
          <p>Unable to connect to the API server. Please ensure the backend is running at http://localhost:8000</p>
          <pre className="error-details">{error}</pre>
          <div className="error-help">
            <h4>To start the service:</h4>
            <code>uvicorn api.main:app --reload</code>
          </div>
        </div>
      )}

      {health && (
        <div className="health-dashboard">
          {/* Overall Status */}
          <div className="health-status">
            <div className={`status-circle ${health.status}`}>
              <span className="status-icon">
                {health.status === 'healthy' && '✅'}
                {health.status === 'degraded' && '⚠️'}
                {health.status === 'unhealthy' && '❌'}
              </span>
              <span className="status-label">{health.status.toUpperCase()}</span>
            </div>
          </div>

          {/* Service Info */}
          <div className="health-section">
            <h3>📋 Service Information</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-icon">🏷️</span>
                <div className="info-content">
                  <div className="info-label">Version</div>
                  <div className="info-value">{health.version}</div>
                </div>
              </div>

              <div className="info-item">
                <span className="info-icon">⏱️</span>
                <div className="info-content">
                  <div className="info-label">Uptime</div>
                  <div className="info-value">{formatUptime(health.uptime_seconds)}</div>
                </div>
              </div>

              <div className="info-item">
                <span className="info-icon">🌐</span>
                <div className="info-content">
                  <div className="info-label">API Base URL</div>
                  <div className="info-value">http://localhost:8000</div>
                </div>
              </div>

              <div className="info-item">
                <span className="info-icon">📚</span>
                <div className="info-content">
                  <div className="info-label">Documentation</div>
                  <div className="info-value">
                    <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">
                      Swagger UI
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Endpoints Status */}
          <div className="health-section">
            <h3>🔌 API Endpoints</h3>
            <div className="endpoints-list">
              <div className="endpoint-item">
                <span className="endpoint-method post">POST</span>
                <span className="endpoint-path">/transcribe</span>
                <span className="endpoint-status active">✅ Active</span>
              </div>
              <div className="endpoint-item">
                <span className="endpoint-method post">POST</span>
                <span className="endpoint-path">/analyze</span>
                <span className="endpoint-status active">✅ Active</span>
              </div>
              <div className="endpoint-item">
                <span className="endpoint-method post">POST</span>
                <span className="endpoint-path">/subtitle</span>
                <span className="endpoint-status active">✅ Active</span>
              </div>
              <div className="endpoint-item">
                <span className="endpoint-method get">GET</span>
                <span className="endpoint-path">/metrics</span>
                <span className="endpoint-status active">✅ Active</span>
              </div>
              <div className="endpoint-item">
                <span className="endpoint-method get">GET</span>
                <span className="endpoint-path">/health</span>
                <span className="endpoint-status active">✅ Active</span>
              </div>
            </div>
          </div>

          {/* System Requirements */}
          <div className="health-section">
            <h3>⚙️ System Requirements</h3>
            <div className="requirements-list">
              <div className="requirement-item">
                <span className="req-icon">🐍</span>
                <span className="req-label">Python Version:</span>
                <span className="req-value">3.10+ required</span>
              </div>
              <div className="requirement-item">
                <span className="req-icon">🎮</span>
                <span className="req-label">GPU (Optional):</span>
                <span className="req-value">NVIDIA with CUDA 12.1+</span>
              </div>
              <div className="requirement-item">
                <span className="req-icon">💾</span>
                <span className="req-label">VRAM:</span>
                <span className="req-value">6GB+ for large models</span>
              </div>
              <div className="requirement-item">
                <span className="req-icon">📦</span>
                <span className="req-label">Dependencies:</span>
                <span className="req-value">faster-whisper, openai-whisper, librosa</span>
              </div>
            </div>
          </div>

          {/* Quick Links */}
          <div className="health-section">
            <h3>🔗 Quick Links</h3>
            <div className="links-grid">
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="link-card"
              >
                <span className="link-icon">📖</span>
                <div className="link-content">
                  <div className="link-title">Swagger UI</div>
                  <div className="link-desc">Interactive API docs</div>
                </div>
              </a>

              <a
                href="http://localhost:8000/redoc"
                target="_blank"
                rel="noopener noreferrer"
                className="link-card"
              >
                <span className="link-icon">📚</span>
                <div className="link-content">
                  <div className="link-title">ReDoc</div>
                  <div className="link-desc">Alternative docs</div>
                </div>
              </a>

              <a
                href="http://localhost:8000/"
                target="_blank"
                rel="noopener noreferrer"
                className="link-card"
              >
                <span className="link-icon">🏠</span>
                <div className="link-content">
                  <div className="link-title">API Root</div>
                  <div className="link-desc">Service info</div>
                </div>
              </a>

              <a
                href="http://localhost:8000/metrics"
                target="_blank"
                rel="noopener noreferrer"
                className="link-card"
              >
                <span className="link-icon">📊</span>
                <div className="link-content">
                  <div className="link-title">Raw Metrics</div>
                  <div className="link-desc">JSON response</div>
                </div>
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default HealthPanel
