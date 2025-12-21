import { useState, useEffect, useRef } from 'react'
import { getTTSVoices, getTTSPresets, synthesizeTTS, playAudioFromBase64, downloadTTSAudio } from '../services/api'
import '../styles/Panel.css'

// Setting descriptions
const DESCRIPTIONS = {
  text: 'Nhập văn bản cần chuyển thành giọng nói (tối đa 5000 ký tự).',
  voice: 'Chọn giọng nói. Edge TTS có chất lượng cao, gTTS đơn giản và ổn định.',
  pitch: 'Điều chỉnh cao độ giọng nói. Giá trị dương = giọng cao hơn (cute), giá trị âm = giọng trầm hơn.',
  speed: 'Tốc độ nói. 1.0 = bình thường, <1.0 = chậm hơn, >1.0 = nhanh hơn.',
}

function TTSPanel() {
  // State
  const [text, setText] = useState('Xin chào, tôi là trợ lý ảo.')
  const [voices, setVoices] = useState([])
  const [presets, setPresets] = useState([])
  const [selectedVoice, setSelectedVoice] = useState('vi-VN-HoaiMyNeural')
  const [selectedPreset, setSelectedPreset] = useState('')
  const [pitch, setPitch] = useState(0)
  const [speed, setSpeed] = useState(1.0)
  const [loading, setLoading] = useState(false)
  const [loadingVoices, setLoadingVoices] = useState(true)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  // Audio ref
  const audioRef = useRef(null)

  // Load voices and presets on mount
  useEffect(() => {
    loadVoices()
    loadPresets()
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

  const loadPresets = async () => {
    try {
      const data = await getTTSPresets()
      setPresets(data.presets || [])
    } catch (err) {
      // Silent fail for presets
    }
  }

  // Handle preset selection
  const handlePresetChange = (presetId) => {
    setSelectedPreset(presetId)
    const preset = presets.find(p => p.id === presetId)
    if (preset) {
      setSelectedVoice(preset.voice_id)
      setPitch(preset.pitch)
      setSpeed(preset.speed)
    }
  }

  // Handle voice change
  const handleVoiceChange = (voiceId) => {
    setSelectedVoice(voiceId)
    setSelectedPreset('') // Clear preset when manually changing voice
  }

  // Handle synthesis
  const handleSynthesize = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await synthesizeTTS({
        text,
        voice_id: selectedVoice,
        pitch,
        speed,
        output_format: 'mp3',
      })

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

        {/* Preset Selection */}
        <div className="form-section">
          <h3>Preset</h3>
          <div className="preset-grid">
            {presets.map(preset => (
              <label
                key={preset.id}
                className={`preset-card ${selectedPreset === preset.id ? 'selected' : ''}`}
              >
                <input
                  type="radio"
                  name="preset"
                  value={preset.id}
                  checked={selectedPreset === preset.id}
                  onChange={(e) => handlePresetChange(e.target.value)}
                  disabled={loading}
                />
                <div className="preset-content">
                  <div className="preset-name">{preset.name}</div>
                  <div className="preset-desc">{preset.description}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Voice Selection */}
        <div className="form-section">
          <h3>Giọng nói {loadingVoices && '(Loading...)'}</h3>
          <div className="form-group">
            <select
              value={selectedVoice}
              onChange={(e) => handleVoiceChange(e.target.value)}
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
                    {voice.name} ({voice.gender === 'female' ? 'Nữ' : 'Nam'}) - {voice.engine === 'edge' ? 'Edge TTS' : 'Google TTS'}
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
              onChange={(e) => {
                setPitch(parseInt(e.target.value))
                setSelectedPreset('') // Clear preset when manually adjusting
              }}
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

        {/* Speed Control */}
        <div className="form-section">
          <h3>Speed (Tốc độ): {speed.toFixed(2)}x</h3>
          <div className="form-group">
            <input
              type="range"
              min="0.5"
              max="2.0"
              step="0.05"
              value={speed}
              onChange={(e) => {
                setSpeed(parseFloat(e.target.value))
                setSelectedPreset('')
              }}
              disabled={loading}
              className="slider"
            />
            <div className="slider-labels">
              <span>0.5x (Chậm)</span>
              <span>1.0x</span>
              <span>2.0x (Nhanh)</span>
            </div>
            <p className="field-desc">{DESCRIPTIONS.speed}</p>
          </div>
        </div>

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
              <span className="stat-value">{result.engine === 'edge' ? 'Edge TTS' : 'Google TTS'}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Pitch</span>
              <span className="stat-value">{result.pitch > 0 ? `+${result.pitch}` : result.pitch} semitones</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Speed</span>
              <span className="stat-value">{result.speed}x</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Size</span>
              <span className="stat-value">{(result.size_bytes / 1024).toFixed(1)} KB</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Processing Time</span>
              <span className="stat-value">{result.processing_time_ms.toFixed(0)} ms</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default TTSPanel
