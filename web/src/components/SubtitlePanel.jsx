import React, { useState, useEffect, useRef } from 'react'
import { submitSubtitleJob, getJobStatus, downloadSubtitle, getPresets } from '../services/api'
import '../styles/Panel.css'

// Setting descriptions
const DESCRIPTIONS = {
  engine: 'faster-whisper tối ưu tốc độ, OpenAI Whisper là bản gốc chính thức.',
  model_size: 'Model lớn hơn chính xác hơn nhưng chậm hơn. Khuyến nghị turbo/large-v3.',
  language: 'Mã ngôn ngữ ISO 639-1 (vd: en, zh, vi). Để trống để tự động nhận diện.',
  max_line_width: 'Số ký tự tối đa mỗi dòng phụ đề.',
  max_line_count: 'Số dòng tối đa mỗi entry phụ đề.',
  adjust_timing: 'Tính lại thời gian bắt đầu dựa trên độ dài text. Sửa phụ đề xuất hiện quá sớm.',
  split_by_punctuation: 'Tách câu dài tại dấu câu (，。？！) để phụ đề ngắn gọn hơn.',
  word_level: 'Mỗi từ một entry phụ đề. Phù hợp cho karaoke.',
  beam_size: 'Số beam cho beam search. Cao hơn = chính xác hơn nhưng chậm hơn.',
  temperature: 'Nhiệt độ sampling. 0 = xác định, cao hơn = ngẫu nhiên hơn.',
  best_of: 'Số ứng viên để chọn kết quả tốt nhất.',
  no_speech_threshold: 'Ngưỡng phát hiện không có giọng nói. Cao hơn = lọc mạnh hơn.',
  compression_ratio_threshold: 'Ngưỡng phát hiện text lặp/hallucination. Thấp hơn = lọc chặt hơn.',
  logprob_threshold: 'Ngưỡng log probability. Segment dưới ngưỡng = độ tin cậy thấp.',
  vad_filter: 'Bộ lọc Voice Activity Detection. Loại bỏ đoạn im lặng.',
  word_timestamps: 'Bật timestamp cho từng từ. Cần cho split_by_punctuation và word_level.',
  condition_on_previous_text: 'Dùng text trước làm ngữ cảnh. Có thể gây lặp trong một số trường hợp.',
  initial_prompt: 'Hướng dẫn model với ngữ cảnh, từ vựng đặc biệt để cải thiện độ chính xác.',
}

const POLL_INTERVAL = 2000 // 2 seconds

function SubtitlePanel() {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  // Job state
  const [jobId, setJobId] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [progress, setProgress] = useState(0)
  const pollIntervalRef = useRef(null)

  // Presets state
  const [presets, setPresets] = useState([])
  const [selectedPreset, setSelectedPreset] = useState('')
  const [presetsLoading, setPresetsLoading] = useState(true)

  // Default settings optimized for dialogue transcription
  const [options, setOptions] = useState({
    format: 'srt',
    engine: 'openai-whisper',
    model_size: 'turbo',
    language: '',
    word_level: false,
    max_line_width: 18,
    max_line_count: 1,
    vad_filter: true,
    word_timestamps: true,
    batch_size: 16,
    beam_size: 10,
    temperature: 0.0,
    best_of: 5,
    condition_on_previous_text: false,
    no_speech_threshold: 0.6,
    compression_ratio_threshold: 2.4,
    logprob_threshold: -1.0,
    initial_prompt: '',
    adjust_timing: true,
    split_by_punctuation: true,
  })

  // Load presets on mount
  useEffect(() => {
    loadPresets()
    return () => {
      // Cleanup polling on unmount
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [])

  const loadPresets = async () => {
    try {
      setPresetsLoading(true)
      const data = await getPresets()
      setPresets(data)
    } catch (err) {
      console.error('Failed to load presets:', err)
    } finally {
      setPresetsLoading(false)
    }
  }

  const startPolling = (jobId) => {
    // Clear any existing polling
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
    }

    pollIntervalRef.current = setInterval(async () => {
      try {
        const status = await getJobStatus(jobId)
        setJobStatus(status.status)
        setProgress(status.progress || 0)

        if (status.status === 'completed') {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
          setLoading(false)

          // Process result
          if (status.result) {
            if (status.result.type === 'srt') {
              setResult({
                format: 'srt',
                content: status.result.content,
                filename: status.result.filename,
                metadata: status.result.metadata,
              })
            } else if (status.result.type === 'json') {
              setResult({
                format: 'json',
                content: JSON.stringify(status.result.data, null, 2),
                data: status.result.data,
                filename: 'transcription.json',
              })
            }
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

  const handlePresetChange = (presetId) => {
    setSelectedPreset(presetId)
    if (!presetId) return

    const preset = presets.find(p => p.id === presetId)
    if (!preset) return

    setOptions(prev => ({
      ...prev,
      // Engine
      engine: preset.engine || prev.engine,
      // Transcription settings
      model_size: preset.transcription?.model_size || prev.model_size,
      language: preset.transcription?.language || '',
      word_timestamps: preset.transcription?.word_timestamps ?? prev.word_timestamps,
      vad_filter: preset.transcription?.vad_filter ?? prev.vad_filter,
      beam_size: preset.transcription?.beam_size ?? prev.beam_size,
      temperature: preset.transcription?.temperature ?? prev.temperature,
      best_of: preset.transcription?.best_of ?? prev.best_of,
      condition_on_previous_text: preset.transcription?.condition_on_previous_text ?? prev.condition_on_previous_text,
      no_speech_threshold: preset.transcription?.no_speech_threshold ?? prev.no_speech_threshold,
      compression_ratio_threshold: preset.transcription?.compression_ratio_threshold ?? prev.compression_ratio_threshold,
      logprob_threshold: preset.transcription?.logprob_threshold ?? prev.logprob_threshold,
      initial_prompt: preset.transcription?.initial_prompt || '',
      // Formatter settings
      max_line_width: preset.formatter?.max_line_width ?? prev.max_line_width,
      max_line_count: preset.formatter?.max_line_count ?? prev.max_line_count,
      adjust_timing: preset.formatter?.adjust_timing ?? prev.adjust_timing,
      split_by_punctuation: preset.formatter?.split_by_punctuation ?? prev.split_by_punctuation,
      word_level: preset.formatter?.word_level ?? prev.word_level,
    }))

    setResult(null)
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
      const response = await submitSubtitleJob(file, options)
      setJobId(response.job_id)
      setJobStatus(response.status)
      startPolling(response.job_id)
    } catch (err) {
      setLoading(false)
      setError(err.response?.data?.detail || err.message || 'Failed to submit job')
    }
  }

  const handleDownload = () => {
    if (result && result.content) {
      downloadSubtitle(result.content, result.filename)
    }
  }

  const handleCopy = async () => {
    if (result && result.content) {
      try {
        await navigator.clipboard.writeText(result.content)
        alert('Copied to clipboard!')
      } catch (err) {
        console.error('Failed to copy:', err)
        alert('Failed to copy to clipboard')
      }
    }
  }

  const getStatusText = () => {
    switch (jobStatus) {
      case 'pending':
        return 'Waiting to start...'
      case 'processing':
        if (progress <= 20) return 'Loading model...'
        if (progress <= 30) return 'Preparing...'
        if (progress <= 80) return 'Transcribing audio...'
        return 'Formatting output...'
      case 'completed':
        return 'Completed!'
      case 'failed':
        return 'Failed'
      default:
        return 'Processing...'
    }
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Subtitle Generation</h2>
        <p className="description">
          Generate subtitle files (SRT or JSON) from audio.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="form">
        {/* Preset Selection */}
        <div className="form-section">
          <h3>Quick Presets</h3>
          <div className="preset-selector">
            <select
              value={selectedPreset}
              onChange={(e) => handlePresetChange(e.target.value)}
              disabled={presetsLoading || loading}
              className="preset-select"
            >
              <option value="">-- Select a preset --</option>
              {presets.map(preset => (
                <option key={preset.id} value={preset.id}>
                  {preset.title} ({preset.engine})
                </option>
              ))}
            </select>
            {selectedPreset && presets.find(p => p.id === selectedPreset) && (
              <p className="preset-description">
                {presets.find(p => p.id === selectedPreset)?.description}
              </p>
            )}
          </div>
        </div>

        {/* File Upload */}
        <div className="form-section">
          <h3>Audio File</h3>
          <div className="file-upload">
            <input
              type="file"
              accept=".mp3,.wav,.m4a,.flac,.ogg,.opus,.webm"
              onChange={handleFileChange}
              id="subtitle-file"
              disabled={loading}
            />
            <label htmlFor="subtitle-file" className="file-label">
              {file ? file.name : 'Choose Audio File'}
            </label>
            <p className="hint">Supported: MP3, WAV, M4A, FLAC, OGG, OPUS, WebM (Max: 500MB)</p>
          </div>
        </div>

        {/* Format Selection */}
        <div className="form-section">
          <h3>Output Format</h3>
          <div className="format-grid">
            <label className={`format-card ${options.format === 'srt' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="format"
                value="srt"
                checked={options.format === 'srt'}
                onChange={(e) => handleOptionChange('format', e.target.value)}
                disabled={loading}
              />
              <div className="format-content">
                <div className="format-icon">SRT</div>
                <div className="format-name">SubRip</div>
                <div className="format-desc">Most compatible</div>
              </div>
            </label>

            <label className={`format-card ${options.format === 'json' ? 'selected' : ''}`}>
              <input
                type="radio"
                name="format"
                value="json"
                checked={options.format === 'json'}
                onChange={(e) => handleOptionChange('format', e.target.value)}
                disabled={loading}
              />
              <div className="format-content">
                <div className="format-icon">JSON</div>
                <div className="format-name">Full Data</div>
                <div className="format-desc">With metadata</div>
              </div>
            </label>
          </div>
        </div>

        {/* Transcription Settings */}
        <div className="form-section">
          <h3>Transcription Engine</h3>
          <div className="form-grid">
            <div className="form-group">
              <label>Engine</label>
              <select
                value={options.engine}
                onChange={(e) => handleOptionChange('engine', e.target.value)}
                disabled={loading}
              >
                <option value="faster-whisper">faster-whisper (Fast)</option>
                <option value="openai-whisper">OpenAI Whisper (Official)</option>
              </select>
              <p className="field-desc">{DESCRIPTIONS.engine}</p>
            </div>

            <div className="form-group">
              <label>Model Size</label>
              <select
                value={options.model_size}
                onChange={(e) => handleOptionChange('model_size', e.target.value)}
                disabled={loading}
              >
                {options.engine === 'openai-whisper' ? (
                  <>
                    <option value="tiny">tiny</option>
                    <option value="base">base</option>
                    <option value="small">small</option>
                    <option value="medium">medium</option>
                    <option value="large-v3">large-v3</option>
                    <option value="turbo">turbo (Recommended)</option>
                  </>
                ) : (
                  <>
                    <option value="tiny">tiny</option>
                    <option value="base">base</option>
                    <option value="small">small</option>
                    <option value="medium">medium</option>
                    <option value="large-v3">large-v3 (Recommended)</option>
                    <option value="distil-large-v3">distil-large-v3 (Fast)</option>
                  </>
                )}
              </select>
              <p className="field-desc">{DESCRIPTIONS.model_size}</p>
            </div>

            <div className="form-group">
              <label>Language</label>
              <input
                type="text"
                placeholder="Auto (e.g., en, vi, zh)"
                value={options.language}
                onChange={(e) => handleOptionChange('language', e.target.value)}
                maxLength={2}
                disabled={loading}
              />
              <p className="field-desc">{DESCRIPTIONS.language}</p>
            </div>
          </div>
        </div>

        {/* SRT Formatting Options */}
        {options.format === 'srt' && (
          <div className="form-section">
            <h3>SRT Formatting</h3>
            <div className="form-grid">
              <div className="form-group">
                <label>Max Line Width</label>
                <input
                  type="number"
                  min="10"
                  max="100"
                  value={options.max_line_width}
                  onChange={(e) => handleOptionChange('max_line_width', parseInt(e.target.value))}
                  disabled={loading}
                />
                <p className="field-desc">{DESCRIPTIONS.max_line_width}</p>
              </div>

              <div className="form-group">
                <label>Max Lines</label>
                <select
                  value={options.max_line_count}
                  onChange={(e) => handleOptionChange('max_line_count', parseInt(e.target.value))}
                  disabled={loading}
                >
                  <option value="1">1 line</option>
                  <option value="2">2 lines</option>
                  <option value="3">3 lines</option>
                </select>
                <p className="field-desc">{DESCRIPTIONS.max_line_count}</p>
              </div>
            </div>

            <div className="checkbox-group" style={{ marginTop: '1rem' }}>
              <div className="checkbox-item">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={options.adjust_timing}
                    onChange={(e) => handleOptionChange('adjust_timing', e.target.checked)}
                    disabled={loading}
                  />
                  <span>Adjust Timing</span>
                </label>
                <p className="field-desc">{DESCRIPTIONS.adjust_timing}</p>
              </div>

              <div className="checkbox-item">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={options.split_by_punctuation}
                    onChange={(e) => handleOptionChange('split_by_punctuation', e.target.checked)}
                    disabled={loading}
                  />
                  <span>Split by Punctuation</span>
                </label>
                <p className="field-desc">{DESCRIPTIONS.split_by_punctuation}</p>
              </div>

              <div className="checkbox-item">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={options.word_level}
                    onChange={(e) => handleOptionChange('word_level', e.target.checked)}
                    disabled={loading}
                  />
                  <span>Word Level</span>
                </label>
                <p className="field-desc">{DESCRIPTIONS.word_level}</p>
              </div>
            </div>
          </div>
        )}

        {/* Advanced Options */}
        <div className="form-section">
          <h3>Advanced Options</h3>
          {/* Row 1: Beam Size, Temperature, Best Of */}
          <div className="form-grid-3">
            <div className="form-group">
              <label>Beam Size</label>
              <input
                type="number"
                min="1"
                max="20"
                value={options.beam_size}
                onChange={(e) => handleOptionChange('beam_size', parseInt(e.target.value))}
                disabled={loading}
              />
              <p className="field-desc">{DESCRIPTIONS.beam_size}</p>
            </div>

            <div className="form-group">
              <label>Temperature</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="1"
                value={options.temperature}
                onChange={(e) => handleOptionChange('temperature', parseFloat(e.target.value))}
                disabled={loading}
              />
              <p className="field-desc">{DESCRIPTIONS.temperature}</p>
            </div>

            <div className="form-group">
              <label>Best Of</label>
              <input
                type="number"
                min="1"
                max="10"
                value={options.best_of}
                onChange={(e) => handleOptionChange('best_of', parseInt(e.target.value))}
                disabled={loading}
              />
              <p className="field-desc">{DESCRIPTIONS.best_of}</p>
            </div>
          </div>

          {/* Row 2: No Speech, Compression Ratio, Logprob */}
          <div className="form-grid-3" style={{ marginTop: '1rem' }}>
            <div className="form-group">
              <label>No Speech Threshold</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="1"
                value={options.no_speech_threshold}
                onChange={(e) => handleOptionChange('no_speech_threshold', parseFloat(e.target.value))}
                disabled={loading}
              />
              <p className="field-desc">{DESCRIPTIONS.no_speech_threshold}</p>
            </div>

            <div className="form-group">
              <label>Compression Ratio</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={options.compression_ratio_threshold}
                onChange={(e) => handleOptionChange('compression_ratio_threshold', parseFloat(e.target.value))}
                disabled={loading}
              />
              <p className="field-desc">{DESCRIPTIONS.compression_ratio_threshold}</p>
            </div>

            <div className="form-group">
              <label>Logprob Threshold</label>
              <input
                type="number"
                step="0.1"
                value={options.logprob_threshold}
                onChange={(e) => handleOptionChange('logprob_threshold', parseFloat(e.target.value))}
                disabled={loading}
              />
              <p className="field-desc">{DESCRIPTIONS.logprob_threshold}</p>
            </div>
          </div>

          <div className="checkbox-group" style={{ marginTop: '1rem' }}>
            <div className="checkbox-item">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={options.vad_filter}
                  onChange={(e) => handleOptionChange('vad_filter', e.target.checked)}
                  disabled={loading}
                />
                <span>VAD Filter</span>
              </label>
              <p className="field-desc">{DESCRIPTIONS.vad_filter}</p>
            </div>

            <div className="checkbox-item">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={options.word_timestamps}
                  onChange={(e) => handleOptionChange('word_timestamps', e.target.checked)}
                  disabled={loading}
                />
                <span>Word Timestamps</span>
              </label>
              <p className="field-desc">{DESCRIPTIONS.word_timestamps}</p>
            </div>

            <div className="checkbox-item">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={options.condition_on_previous_text}
                  onChange={(e) => handleOptionChange('condition_on_previous_text', e.target.checked)}
                  disabled={loading}
                />
                <span>Condition on Previous Text</span>
              </label>
              <p className="field-desc">{DESCRIPTIONS.condition_on_previous_text}</p>
            </div>
          </div>

          <div className="form-group" style={{ marginTop: '1rem' }}>
            <label>Initial Prompt</label>
            <textarea
              placeholder="Nhập ngữ cảnh, tên riêng, từ vựng đặc biệt... (Lưu ý: Prompt nên viết bằng ngôn ngữ gốc của video)"
              value={options.initial_prompt}
              onChange={(e) => handleOptionChange('initial_prompt', e.target.value)}
              rows={2}
              disabled={loading}
              style={{
                width: '100%',
                padding: '0.5rem',
                border: '1px solid #ddd',
                borderRadius: '4px',
                fontSize: '0.9rem',
                resize: 'vertical',
              }}
            />
            <p className="field-desc">{DESCRIPTIONS.initial_prompt}</p>
          </div>
        </div>

        {/* Submit Button */}
        <button type="submit" className="submit-btn" disabled={loading || !file}>
          {loading ? 'Processing...' : 'Generate Subtitle'}
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

      {/* Result Preview */}
      {result && (
        <div className="result-section">
          <div className="result-header">
            <h3>Result ({result.format.toUpperCase()})</h3>
            <div className="result-actions">
              <button onClick={handleCopy} className="copy-btn">
                Copy
              </button>
              <button onClick={handleDownload} className="download-btn">
                Download
              </button>
            </div>
          </div>

          <div className="subtitle-preview">
            <pre className="subtitle-content">{result.content}</pre>
          </div>

          <div className="result-stats">
            <div className="stat-item">
              <span className="stat-label">Format:</span>
              <span className="stat-value">{result.format.toUpperCase()}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Size:</span>
              <span className="stat-value">{(result.content.length / 1024).toFixed(2)} KB</span>
            </div>
            {result.metadata && (
              <div className="stat-item">
                <span className="stat-label">Time:</span>
                <span className="stat-value">{(result.metadata.total_time_ms / 1000).toFixed(1)}s</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default SubtitlePanel
