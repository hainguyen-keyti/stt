import React, { useState, useEffect } from 'react'
import { getMetrics } from '../services/api'
import '../styles/Panel.css'

function MetricsPanel() {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(false)

  const fetchMetrics = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await getMetrics()
      setMetrics(data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch metrics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMetrics()
  }, [])

  useEffect(() => {
    let interval
    if (autoRefresh) {
      interval = setInterval(fetchMetrics, 5000) // Refresh every 5 seconds
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [autoRefresh])

  const formatNumber = (num) => {
    if (num === null || num === undefined) return 'N/A'
    return num.toLocaleString()
  }

  const getLatencyClass = (p95) => {
    if (p95 < 2000) return 'excellent'
    if (p95 < 5000) return 'good'
    if (p95 < 10000) return 'fair'
    return 'poor'
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>📈 Performance Metrics</h2>
        <p className="description">
          Real-time service performance metrics including request statistics, latency percentiles,
          and resource utilization.
        </p>
        <div className="header-actions">
          <button onClick={fetchMetrics} className="refresh-btn" disabled={loading}>
            {loading ? '⏳ Loading...' : '🔄 Refresh'}
          </button>
          <label className="auto-refresh-label">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh (5s)
          </label>
        </div>
      </div>

      {error && (
        <div className="error-box">
          <h4>❌ Error</h4>
          <pre>{error}</pre>
        </div>
      )}

      {metrics && (
        <div className="metrics-dashboard">
          {/* Request Statistics */}
          <div className="metrics-section">
            <h3>📊 Request Statistics</h3>
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-icon">📝</div>
                <div className="metric-label">Total Requests</div>
                <div className="metric-value">{formatNumber(metrics.requests_total)}</div>
                <div className="metric-desc">Since startup</div>
              </div>

              <div className="metric-card">
                <div className="metric-icon">⏰</div>
                <div className="metric-label">Last Hour</div>
                <div className="metric-value">{formatNumber(metrics.requests_last_hour)}</div>
                <div className="metric-desc">Past 60 minutes</div>
              </div>

              <div className="metric-card">
                <div className="metric-icon">📈</div>
                <div className="metric-label">Request Rate</div>
                <div className="metric-value">{metrics.requests_per_minute.toFixed(2)}</div>
                <div className="metric-desc">Requests per minute</div>
              </div>

              <div className="metric-card error-card">
                <div className="metric-icon">⚠️</div>
                <div className="metric-label">Error Rate</div>
                <div className="metric-value">{(metrics.error_rate * 100).toFixed(2)}%</div>
                <div className="metric-desc">
                  {metrics.error_rate < 0.01 && '✅ Excellent'}
                  {metrics.error_rate >= 0.01 && metrics.error_rate < 0.05 && '⚠️ Acceptable'}
                  {metrics.error_rate >= 0.05 && '🚨 High'}
                </div>
              </div>
            </div>
          </div>

          {/* Latency Statistics */}
          <div className="metrics-section">
            <h3>⏱️ Latency Percentiles</h3>
            <div className="latency-chart">
              <div className="latency-bars">
                <div className="latency-bar">
                  <div className="latency-label">Average</div>
                  <div className="bar-container">
                    <div
                      className="bar-fill excellent"
                      style={{ width: `${Math.min(100, (metrics.avg_inference_time_ms / 10000) * 100)}%` }}
                    ></div>
                  </div>
                  <div className="latency-value">{(metrics.avg_inference_time_ms / 1000).toFixed(2)}s</div>
                </div>

                <div className="latency-bar">
                  <div className="latency-label">P50 (Median)</div>
                  <div className="bar-container">
                    <div
                      className="bar-fill good"
                      style={{ width: `${Math.min(100, (metrics.p50_inference_time_ms / 10000) * 100)}%` }}
                    ></div>
                  </div>
                  <div className="latency-value">{(metrics.p50_inference_time_ms / 1000).toFixed(2)}s</div>
                </div>

                <div className="latency-bar">
                  <div className="latency-label">P95</div>
                  <div className="bar-container">
                    <div
                      className={`bar-fill ${getLatencyClass(metrics.p95_inference_time_ms)}`}
                      style={{ width: `${Math.min(100, (metrics.p95_inference_time_ms / 10000) * 100)}%` }}
                    ></div>
                  </div>
                  <div className="latency-value">{(metrics.p95_inference_time_ms / 1000).toFixed(2)}s</div>
                </div>

                <div className="latency-bar">
                  <div className="latency-label">P99 (Worst)</div>
                  <div className="bar-container">
                    <div
                      className="bar-fill fair"
                      style={{ width: `${Math.min(100, (metrics.p99_inference_time_ms / 10000) * 100)}%` }}
                    ></div>
                  </div>
                  <div className="latency-value">{(metrics.p99_inference_time_ms / 1000).toFixed(2)}s</div>
                </div>
              </div>

              <div className="latency-info">
                <h4>Interpretation</h4>
                <ul>
                  <li><strong>P50:</strong> 50% of requests complete within this time</li>
                  <li><strong>P95:</strong> 95% of requests (typical SLA target)</li>
                  <li><strong>P99:</strong> 99% of requests (outlier detection)</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Resource Utilization */}
          <div className="metrics-section">
            <h3>💻 Resource Utilization</h3>
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-icon">🎮</div>
                <div className="metric-label">GPU Utilization</div>
                <div className="metric-value">
                  {metrics.gpu_utilization_percent !== null
                    ? `${metrics.gpu_utilization_percent.toFixed(1)}%`
                    : 'N/A'}
                </div>
                <div className="metric-desc">
                  {metrics.gpu_utilization_percent === null && 'Not available'}
                  {metrics.gpu_utilization_percent !== null && metrics.gpu_utilization_percent < 50 && 'Low usage'}
                  {metrics.gpu_utilization_percent >= 50 && metrics.gpu_utilization_percent < 80 && 'Moderate'}
                  {metrics.gpu_utilization_percent >= 80 && 'High usage'}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-icon">💾</div>
                <div className="metric-label">VRAM Usage</div>
                <div className="metric-value">
                  {metrics.vram_usage_percent !== null
                    ? `${metrics.vram_usage_percent.toFixed(1)}%`
                    : 'N/A'}
                </div>
                <div className="metric-desc">
                  {metrics.vram_usage_percent === null && 'Not available'}
                  {metrics.vram_usage_percent !== null && metrics.vram_usage_percent < 50 && '✅ Healthy'}
                  {metrics.vram_usage_percent >= 50 && metrics.vram_usage_percent < 80 && '⚠️ Moderate'}
                  {metrics.vram_usage_percent >= 80 && '🚨 High'}
                </div>
                {metrics.vram_usage_percent !== null && (
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${metrics.vram_usage_percent}%`,
                        backgroundColor: metrics.vram_usage_percent >= 80 ? '#f44336' : metrics.vram_usage_percent >= 50 ? '#ff9800' : '#4caf50'
                      }}
                    ></div>
                  </div>
                )}
              </div>

              <div className="metric-card">
                <div className="metric-icon">🗄️</div>
                <div className="metric-label">Cache Hit Rate</div>
                <div className="metric-value">{(metrics.cache_hit_rate * 100).toFixed(1)}%</div>
                <div className="metric-desc">
                  {metrics.cache_hit_rate >= 0.7 && '✅ Excellent'}
                  {metrics.cache_hit_rate >= 0.4 && metrics.cache_hit_rate < 0.7 && '👍 Good'}
                  {metrics.cache_hit_rate < 0.4 && '⚠️ Poor'}
                </div>
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${metrics.cache_hit_rate * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>

          {/* SLA Status */}
          <div className="metrics-section">
            <h3>🎯 SLA Status</h3>
            <div className="sla-checks">
              <div className={`sla-check ${metrics.p95_inference_time_ms < 30000 ? 'pass' : 'fail'}`}>
                <span className="sla-icon">{metrics.p95_inference_time_ms < 30000 ? '✅' : '❌'}</span>
                <span className="sla-text">P95 Latency {'<'} 30s for 13-min audio</span>
                <span className="sla-value">{(metrics.p95_inference_time_ms / 1000).toFixed(2)}s</span>
              </div>

              <div className={`sla-check ${metrics.error_rate < 0.02 ? 'pass' : 'fail'}`}>
                <span className="sla-icon">{metrics.error_rate < 0.02 ? '✅' : '❌'}</span>
                <span className="sla-text">Error Rate {'<'} 2%</span>
                <span className="sla-value">{(metrics.error_rate * 100).toFixed(2)}%</span>
              </div>

              <div className={`sla-check ${metrics.cache_hit_rate >= 0.6 ? 'pass' : 'fail'}`}>
                <span className="sla-icon">{metrics.cache_hit_rate >= 0.6 ? '✅' : '❌'}</span>
                <span className="sla-text">Cache Hit Rate {'>'} 60%</span>
                <span className="sla-value">{(metrics.cache_hit_rate * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default MetricsPanel
