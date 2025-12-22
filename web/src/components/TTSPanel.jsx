import { useState, useEffect, useRef } from 'react'
import { getTTSVoices, synthesizeTTS, playAudioFromBase64, downloadTTSAudio } from '../services/api'
import '../styles/Panel.css'

// Setting descriptions
const DESCRIPTIONS = {
  text: 'Nhập văn bản cần chuyển thành giọng nói (tối đa 5000 ký tự).',
  voice: 'Chọn giọng nói. CapCut TTS tự nhiên, Edge TTS chất lượng cao, gTTS ổn định.',
  pitch: 'Điều chỉnh cao độ giọng nói. Giá trị dương = giọng cao hơn (cute), giá trị âm = giọng trầm hơn.',
  speed: 'Tốc độ nói. 1.0 = bình thường, <1.0 = chậm hơn, >1.0 = nhanh hơn.',
  targetDuration: 'Thời gian mục tiêu (ms). Audio sẽ tự động điều chỉnh tốc độ để khớp thời gian này.',
  minSpeed: 'Tốc độ tối thiểu khi dùng Time Adjust (tránh quá chậm).',
  maxSpeed: 'Tốc độ tối đa khi dùng Time Adjust (tránh quá nhanh).',
}

function TTSPanel() {
  // State
  const [text, setText] = useState('Xin chào, tôi là trợ lý ảo.')
  const [voices, setVoices] = useState([])
  const [selectedVoice, setSelectedVoice] = useState('vi-VN-HoaiMyNeural')
  const [pitch, setPitch] = useState(0)
  const [speed, setSpeed] = useState(1.0)
  // Speed adjustment mode: 'speed' or 'time'
  const [speedMode, setSpeedMode] = useState('speed')
  const [targetDuration, setTargetDuration] = useState(2000)
  const [minSpeed, setMinSpeed] = useState(0.5) // Range: 0.3 - 1.0
  const [maxSpeed, setMaxSpeed] = useState(2.0)
  const [loading, setLoading] = useState(false)
  const [loadingVoices, setLoadingVoices] = useState(true)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  // Audio ref
  const audioRef = useRef(null)

  // Load voices on mount
  useEffect(() => {
    loadVoices()
  }, [])

  const loadVoices = async () => {
    setLoadingVoices(true)
    try {
      const data = await getTTSVoices()
      setVoices(data.voices || [])
    } catch (err) {
      setError('Failed to load voices: ' + err.message)
    } finally {
      setLoadingVoices(false)
    }
  }

  // Handle synthesis
  const handleSynthesize = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const requestData = {
        text,
        voice_id: selectedVoice,
        pitch,
        output_format: 'mp3',
      }

      // Add speed params based on mode
      if (speedMode === 'speed') {
        requestData.speed = speed
      } else {
        // Time adjust mode
        requestData.target_duration_ms = targetDuration
        if (minSpeed > 0) requestData.min_speed = minSpeed
        if (maxSpeed > 0) requestData.max_speed = maxSpeed
      }

      const response = await synthesizeTTS(requestData)

      if (response.success) {
        setResult(response)
        // Auto-play
        playAudio(response.audio, response.format)
      } else {
        setError(response.error || 'Synthesis failed')
      }
    } catch (err) {
      setError(err.response?.data?.detail?.message || err.message || 'Failed to synthesize')
    } finally {
      setLoading(false)
    }
  }

  // Play audio
  const playAudio = (base64Data, format) => {
    if (audioRef.current) {
      audioRef.current.pause()
    }
    const audio = playAudioFromBase64(base64Data, format)
    audioRef.current = audio
    audio.play()
  }

  // Download audio
  const handleDownload = () => {
    if (result) {
      const filename = `tts_${selectedVoice}_p${pitch}.${result.format}`
      downloadTTSAudio(result.audio, filename, result.format)
    }
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Text-to-Speech</h2>
        <p className="description">
          Chuyển văn bản thành giọng nói với nhiều tùy chọn giọng và pitch.
        </p>
      </div>

      <form className="form" onSubmit={handleSynthesize}>
        {/* Text Input */}
        <div className="form-section">
          <h3>Văn bản</h3>
          <div className="form-group">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Nhập văn bản cần chuyển thành giọng nói..."
              rows={4}
              maxLength={5000}
              disabled={loading}
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid #ddd',
                borderRadius: '6px',
                fontSize: '1rem',
                resize: 'vertical',
              }}
            />
            <p className="field-desc">{DESCRIPTIONS.text} ({text.length}/5000)</p>
          </div>
        </div>

        {/* Voice Selection */}
        <div className="form-section">
          <h3>Giọng nói {loadingVoices && '(Loading...)'}</h3>
          <div className="form-group">
            <select
              value={selectedVoice}
              onChange={(e) => setSelectedVoice(e.target.value)}
              disabled={loading || loadingVoices}
              className="preset-select"
            >
              {loadingVoices ? (
                <option value="">Đang tải giọng nói...</option>
              ) : voices.length === 0 ? (
                <option value="">Không có giọng nói nào</option>
              ) : (
                voices.map(voice => (
                  <option key={voice.id} value={voice.id}>
                    {voice.name} ({voice.gender === 'female' ? 'Nữ' : 'Nam'}) - {voice.engine === 'capcut' ? 'CapCut TTS' : voice.engine === 'edge' ? 'Edge TTS' : 'Google TTS'}
                  </option>
                ))
              )}
            </select>
            <p className="field-desc">{DESCRIPTIONS.voice}</p>
            {voices.length > 0 && (
              <p className="field-desc" style={{color: '#4caf50'}}>
                Đã tải {voices.length} giọng nói
              </p>
            )}
          </div>
        </div>

        {/* Pitch Control */}
        <div className="form-section">
          <h3>Pitch (Cao độ): {pitch > 0 ? `+${pitch}` : pitch} semitones</h3>
          <div className="form-group">
            <input
              type="range"
              min="-12"
              max="12"
              step="1"
              value={pitch}
              onChange={(e) => setPitch(parseInt(e.target.value))}
              disabled={loading}
              className="slider"
            />
            <div className="slider-labels">
              <span>-12 (Trầm)</span>
              <span>0 (Gốc)</span>
              <span>+12 (Cao)</span>
            </div>
            <p className="field-desc">{DESCRIPTIONS.pitch}</p>
          </div>
        </div>

        {/* Speed Mode Selection */}
        <div className="form-section">
          <h3>Chế độ điều chỉnh tốc độ</h3>
          <div className="form-group">
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="speedMode"
                  value="speed"
                  checked={speedMode === 'speed'}
                  onChange={() => setSpeedMode('speed')}
                  disabled={loading}
                />
                Speed Adjust (x0.5 - x1.5)
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="speedMode"
                  value="time"
                  checked={speedMode === 'time'}
                  onChange={() => setSpeedMode('time')}
                  disabled={loading}
                />
                Time Adjust (ms)
              </label>
            </div>
          </div>
        </div>

        {/* Speed Control - show based on mode */}
        {speedMode === 'speed' ? (
          <div className="form-section">
            <h3>Speed (Tốc độ): {speed.toFixed(2)}x</h3>
            <div className="form-group">
              <input
                type="range"
                min="0.5"
                max="1.5"
                step="0.05"
                value={speed}
                onChange={(e) => setSpeed(parseFloat(e.target.value))}
                disabled={loading}
                className="slider"
              />
              <div className="slider-labels">
                <span>0.5x (Chậm)</span>
                <span>1.0x</span>
                <span>1.5x (Nhanh)</span>
              </div>
              <p className="field-desc">{DESCRIPTIONS.speed}</p>
            </div>
          </div>
        ) : (
          <div className="form-section">
            <h3>Time Adjust</h3>
            <div className="form-group">
              <label style={{ display: 'block', marginBottom: '0.5rem' }}>
                Thời gian mục tiêu: {targetDuration} ms ({(targetDuration / 1000).toFixed(1)}s)
              </label>
              <input
                type="range"
                min="500"
                max="10000"
                step="100"
                value={targetDuration}
                onChange={(e) => setTargetDuration(parseInt(e.target.value))}
                disabled={loading}
                className="slider"
              />
              <div className="slider-labels">
                <span>500ms</span>
                <span>5000ms</span>
                <span>10000ms</span>
              </div>
              <p className="field-desc">{DESCRIPTIONS.targetDuration}</p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '1rem' }}>
              <div className="form-group">
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>
                  Min Speed: {minSpeed}x
                </label>
                <input
                  type="range"
                  min="0.3"
                  max="1.0"
                  step="0.1"
                  value={minSpeed}
                  onChange={(e) => setMinSpeed(parseFloat(e.target.value))}
                  disabled={loading}
                  className="slider"
                />
                <div className="slider-labels">
                  <span>0.3x</span>
                  <span>0.65x</span>
                  <span>1.0x</span>
                </div>
                <p className="field-desc">{DESCRIPTIONS.minSpeed}</p>
              </div>

              <div className="form-group">
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>
                  Max Speed: {maxSpeed}x
                </label>
                <input
                  type="range"
                  min="1.0"
                  max="3.0"
                  step="0.1"
                  value={maxSpeed}
                  onChange={(e) => setMaxSpeed(parseFloat(e.target.value))}
                  disabled={loading}
                  className="slider"
                />
                <div className="slider-labels">
                  <span>1.0x</span>
                  <span>2.0x</span>
                  <span>3.0x</span>
                </div>
                <p className="field-desc">{DESCRIPTIONS.maxSpeed}</p>
              </div>
            </div>
          </div>
        )}

        {/* Submit Button */}
        <button type="submit" className="submit-btn" disabled={loading || !text.trim()}>
          {loading ? 'Generating...' : 'Generate Speech'}
        </button>
      </form>

      {/* Error Display */}
      {error && (
        <div className="error-box">
          <h4>Error</h4>
          <p>{error}</p>
        </div>
      )}

      {/* Result Display */}
      {result && (
        <div className="result-section">
          <div className="result-header">
            <h3>Generated Audio</h3>
            <div className="result-actions">
              <button
                className="copy-btn"
                onClick={() => playAudio(result.audio, result.format)}
              >
                Play Again
              </button>
              <button className="download-btn" onClick={handleDownload}>
                Download
              </button>
            </div>
          </div>

          <div className="result-stats">
            <div className="stat-item">
              <span className="stat-label">Voice</span>
              <span className="stat-value">{result.voice_name}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Engine</span>
              <span className="stat-value">{result.engine === 'capcut' ? 'CapCut TTS' : result.engine === 'edge' ? 'Edge TTS' : 'Google TTS'}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Pitch</span>
              <span className="stat-value">{result.pitch > 0 ? `+${result.pitch}` : result.pitch} semitones</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Speed</span>
              <span className="stat-value">
                {typeof result.speed === 'number' ? result.speed.toFixed(2) : result.speed}x
                {result.time_adjust?.speed_clamped && ' (clamped)'}
              </span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Size</span>
              <span className="stat-value">{(result.size_bytes / 1024).toFixed(1)} KB</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Processing Time</span>
              <span className="stat-value">{result.processing_time_ms.toFixed(0)} ms</span>
            </div>
            {result.time_adjust && (
              <>
                <div className="stat-item">
                  <span className="stat-label">Target Duration</span>
                  <span className="stat-value">{result.time_adjust.target_duration_ms} ms</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Original Duration</span>
                  <span className="stat-value">{result.time_adjust.original_duration_ms} ms</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Calculated Speed</span>
                  <span className="stat-value">{result.time_adjust.calculated_speed}x</span>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default TTSPanel
