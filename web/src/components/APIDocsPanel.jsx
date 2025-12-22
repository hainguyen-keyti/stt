import React, { useState } from 'react'
import '../styles/Panel.css'

const API_SECTIONS = [
  {
    id: 'stt',
    title: 'Speech-to-Text (STT)',
    description: 'Chuyển đổi audio thành text/phụ đề',
    endpoints: [
      {
        method: 'POST',
        path: '/subtitle/',
        description: 'Tạo phụ đề từ file audio',
        params: [
          { name: 'audio_file', type: 'file', required: true, desc: 'File audio (MP3, WAV, M4A, FLAC, OGG, OPUS, WebM)' },
          { name: 'format', type: 'string', required: false, desc: 'Định dạng output: srt, json (default: srt)' },
          { name: 'engine', type: 'string', required: false, desc: 'Engine: faster-whisper, openai-whisper' },
          { name: 'model_size', type: 'string', required: false, desc: 'Model: tiny, base, small, medium, large-v3, turbo' },
          { name: 'language', type: 'string', required: false, desc: 'Mã ngôn ngữ ISO 639-1 (vd: vi, en, zh). Để trống = tự động' },
          { name: 'max_line_width', type: 'integer', required: false, desc: 'Số ký tự tối đa mỗi dòng (default: 42)' },
          { name: 'max_line_count', type: 'integer', required: false, desc: 'Số dòng tối đa mỗi entry (default: 2)' },
          { name: 'beam_size', type: 'integer', required: false, desc: 'Beam size cho search (default: 5)' },
          { name: 'word_timestamps', type: 'boolean', required: false, desc: 'Bật timestamp từng từ' },
          { name: 'vad_filter', type: 'boolean', required: false, desc: 'Bật Voice Activity Detection' },
        ],
        response: `{
  "job_id": "abc123",
  "status": "pending",
  "message": "Job submitted successfully"
}`,
        curlExample: `curl -X POST "https://your-domain.com/subtitle/" \\
  -F "audio_file=@audio.mp3" \\
  -F "format=srt" \\
  -F "engine=openai-whisper" \\
  -F "model_size=turbo" \\
  -F "language=vi"`,
      },
      {
        method: 'GET',
        path: '/subtitle/jobs/{job_id}',
        description: 'Kiểm tra trạng thái job và lấy kết quả',
        params: [
          { name: 'job_id', type: 'string', required: true, desc: 'ID của job' },
        ],
        response: `{
  "job_id": "abc123",
  "status": "completed",
  "progress": 100,
  "result": {
    "type": "srt",
    "content": "1\\n00:00:00,000 --> 00:00:02,500\\nXin chào...",
    "filename": "audio.srt",
    "metadata": {
      "total_time_ms": 5230,
      "engine": "openai-whisper"
    }
  }
}`,
        curlExample: `curl "https://your-domain.com/subtitle/jobs/abc123"`,
      },
      {
        method: 'GET',
        path: '/presets/',
        description: 'Lấy danh sách các preset cấu hình sẵn',
        params: [],
        response: `[
  {
    "id": "dialogue",
    "title": "Dialogue",
    "description": "Tối ưu cho hội thoại",
    "engine": "openai-whisper",
    "transcription": { ... },
    "formatter": { ... }
  }
]`,
        curlExample: `curl "https://your-domain.com/presets/"`,
      },
    ],
  },
  {
    id: 'tts',
    title: 'Text-to-Speech (TTS)',
    description: 'Chuyển đổi text thành giọng nói với nhiều engine (Edge TTS, gTTS, CapCut TTS)',
    endpoints: [
      {
        method: 'POST',
        path: '/tts/synthesize',
        description: 'Tổng hợp giọng nói từ text',
        params: [
          { name: 'text', type: 'string', required: true, desc: 'Văn bản cần chuyển (tối đa 5000 ký tự)' },
          { name: 'voice_id', type: 'string', required: false, desc: 'ID giọng nói (default: vi-VN-HoaiMyNeural)' },
          { name: 'pitch', type: 'integer', required: false, desc: 'Cao độ: -12 đến +12 semitones (default: 0)' },
          { name: 'speed', type: 'float', required: false, desc: 'Tốc độ: 0.5 đến 1.5 (default: 1.0). Bỏ qua nếu dùng target_duration_ms' },
          { name: 'output_format', type: 'string', required: false, desc: 'Định dạng: mp3, wav (default: mp3)' },
          { name: 'target_duration_ms', type: 'integer', required: false, desc: 'Thời gian mục tiêu (100-60000ms). Nếu set, speed sẽ tự động tính' },
          { name: 'min_speed', type: 'float', required: false, desc: 'Tốc độ tối thiểu khi dùng target_duration_ms (0.3-1.0)' },
          { name: 'max_speed', type: 'float', required: false, desc: 'Tốc độ tối đa khi dùng target_duration_ms (1.0-3.0)' },
        ],
        response: `{
  "success": true,
  "audio": "base64_encoded_audio_data...",
  "format": "mp3",
  "voice_id": "vi-VN-HoaiMyNeural",
  "voice_name": "Edge Nữ",
  "engine": "edge",
  "pitch": 0,
  "speed": 1.0,
  "size_bytes": 45678,
  "processing_time_ms": 1234,
  "time_adjust": {
    "target_duration_ms": 2000,
    "original_duration_ms": 1500,
    "calculated_speed": 0.75,
    "final_speed": 0.75,
    "speed_clamped": false
  }
}`,
        curlExample: `curl -X POST "https://your-domain.com/tts/synthesize" \\
  -H "Content-Type: application/json" \\
  -d '{
    "text": "Xin chào, tôi là trợ lý ảo.",
    "voice_id": "vi-VN-HoaiMyNeural",
    "pitch": 0,
    "speed": 1.0
  }'`,
      },
      {
        method: 'GET',
        path: '/tts/voices',
        description: 'Lấy danh sách giọng nói khả dụng',
        params: [
          { name: 'language', type: 'string', required: false, desc: 'Lọc theo ngôn ngữ (vd: vi)' },
          { name: 'gender', type: 'string', required: false, desc: 'Lọc theo giới tính: male, female' },
          { name: 'engine', type: 'string', required: false, desc: 'Lọc theo engine: edge, gtts, capcut' },
        ],
        response: `{
  "voices": [
    {
      "id": "vi-VN-HoaiMyNeural",
      "name": "Edge Nữ",
      "language": "vi-VN",
      "gender": "female",
      "engine": "edge",
      "description": "Vietnamese female voice - natural and clear"
    },
    {
      "id": "vi-VN-NamMinhNeural",
      "name": "Edge Nam",
      "language": "vi-VN",
      "gender": "male",
      "engine": "edge",
      "description": "Vietnamese male voice - professional"
    },
    {
      "id": "gtts-vi",
      "name": "gTTS Nữ",
      "language": "vi",
      "gender": "female",
      "engine": "gtts",
      "description": "Google TTS Vietnamese voice"
    },
    {
      "id": "tt-BV074_streaming",
      "name": "CapCut Nữ",
      "language": "vi-VN",
      "gender": "female",
      "engine": "capcut",
      "description": "Vietnamese female voice - CapCut/TikTok style"
    },
    {
      "id": "tt-BV075_streaming",
      "name": "CapCut Nam",
      "language": "vi-VN",
      "gender": "male",
      "engine": "capcut",
      "description": "Vietnamese male voice - CapCut/TikTok style"
    }
  ]
}`,
        curlExample: `curl "https://your-domain.com/tts/voices"`,
      },
      {
        method: 'GET',
        path: '/tts/engines',
        description: 'Lấy danh sách TTS engines khả dụng',
        params: [],
        response: `{
  "engines": [
    { "name": "edge", "display_name": "Microsoft Edge TTS" },
    { "name": "gtts", "display_name": "Google TTS" },
    { "name": "capcut", "display_name": "CapCut TTS" }
  ],
  "available": true
}`,
        curlExample: `curl "https://your-domain.com/tts/engines"`,
      },
    ],
  },
  {
    id: 'separator',
    title: 'Audio Separator',
    description: 'Tách vocal và instrumental từ audio',
    endpoints: [
      {
        method: 'POST',
        path: '/separator/',
        description: 'Tách và mix lại audio với volume tùy chỉnh',
        params: [
          { name: 'audio_file', type: 'file', required: true, desc: 'File audio (MP3, WAV, M4A, FLAC, OGG)' },
          { name: 'vocal_volume', type: 'float', required: false, desc: 'Âm lượng vocal: 0.0-2.0 (default: 1.0)' },
          { name: 'instrumental_volume', type: 'float', required: false, desc: 'Âm lượng instrumental: 0.0-2.0 (default: 1.0)' },
          { name: 'output_format', type: 'string', required: false, desc: 'Định dạng: mp3, wav, flac (default: mp3)' },
          { name: 'model', type: 'string', required: false, desc: 'Model: fast, balanced, quality (default: fast)' },
        ],
        response: `{
  "job_id": "xyz789",
  "status": "pending",
  "message": "Separation job submitted"
}`,
        curlExample: `curl -X POST "https://your-domain.com/separator/" \\
  -F "audio_file=@song.mp3" \\
  -F "vocal_volume=0" \\
  -F "instrumental_volume=1.0" \\
  -F "output_format=mp3" \\
  -F "model=fast"`,
      },
      {
        method: 'GET',
        path: '/separator/jobs/{job_id}',
        description: 'Kiểm tra trạng thái job separation',
        params: [
          { name: 'job_id', type: 'string', required: true, desc: 'ID của job' },
        ],
        response: `{
  "job_id": "xyz789",
  "status": "completed",
  "progress": 100,
  "result": {
    "format": "mp3",
    "filename": "song_mixed.mp3",
    "data": "base64_encoded_audio...",
    "size_bytes": 4567890,
    "metadata": {
      "processing_time_ms": 15000,
      "vocal_volume": 0,
      "instrumental_volume": 1.0
    }
  }
}`,
        curlExample: `curl "https://your-domain.com/separator/jobs/xyz789"`,
      },
    ],
  },
  {
    id: 'system',
    title: 'System',
    description: 'Health check và metrics',
    endpoints: [
      {
        method: 'GET',
        path: '/health',
        description: 'Kiểm tra trạng thái hệ thống',
        params: [],
        response: `{
  "status": "healthy",
  "version": "4.0.0",
  "services": {
    "stt": { "status": "ok", "engines": ["faster-whisper", "openai-whisper"] },
    "tts": { "status": "ok", "engines": ["edge-tts", "gtts", "capcut"] },
    "separator": { "status": "ok" }
  }
}`,
        curlExample: `curl "https://your-domain.com/health"`,
      },
      {
        method: 'GET',
        path: '/metrics',
        description: 'Lấy metrics hệ thống',
        params: [],
        response: `{
  "total_requests": 1234,
  "active_jobs": 2,
  "cpu_usage": 45.2,
  "memory_usage": 68.5
}`,
        curlExample: `curl "https://your-domain.com/metrics"`,
      },
    ],
  },
]

const WORKFLOW_EXAMPLES = [
  {
    id: 'karaoke',
    title: 'Tạo nhạc Karaoke',
    description: 'Xóa vocal khỏi bài hát để tạo nhạc nền karaoke',
    steps: [
      { step: 1, action: 'Upload file audio', endpoint: 'POST /separator/', params: 'vocal_volume=0, instrumental_volume=1.0' },
      { step: 2, action: 'Poll status', endpoint: 'GET /separator/jobs/{job_id}', params: 'Lặp lại cho đến khi status=completed' },
      { step: 3, action: 'Download kết quả', endpoint: 'Từ response.result.data', params: 'Decode base64 và save file' },
    ],
  },
  {
    id: 'subtitle',
    title: 'Tạo phụ đề tiếng Việt',
    description: 'Tạo file SRT từ video/audio tiếng Việt',
    steps: [
      { step: 1, action: 'Submit job', endpoint: 'POST /subtitle/', params: 'format=srt, language=vi, engine=openai-whisper' },
      { step: 2, action: 'Poll status', endpoint: 'GET /subtitle/jobs/{job_id}', params: 'Lặp lại mỗi 5 giây' },
      { step: 3, action: 'Lấy phụ đề', endpoint: 'Từ response.result.content', params: 'Nội dung file SRT' },
    ],
  },
  {
    id: 'tts-batch',
    title: 'TTS hàng loạt',
    description: 'Chuyển nhiều đoạn text thành audio với thời gian cố định',
    steps: [
      { step: 1, action: 'Lấy danh sách voices', endpoint: 'GET /tts/voices', params: 'Chọn voice: Edge, gTTS, hoặc CapCut' },
      { step: 2, action: 'Synthesize từng đoạn', endpoint: 'POST /tts/synthesize', params: 'text, voice_id, pitch, speed hoặc target_duration_ms' },
      { step: 3, action: 'Decode và save', endpoint: 'Từ response.audio', params: 'Base64 decode thành file MP3' },
    ],
  },
  {
    id: 'tts-time-adjust',
    title: 'TTS với thời gian cố định',
    description: 'Tạo audio với độ dài chính xác (cho sync video/audio)',
    steps: [
      { step: 1, action: 'Xác định thời gian mục tiêu', endpoint: 'Tính từ video segment', params: 'vd: 2000ms cho câu thoại' },
      { step: 2, action: 'Synthesize với time adjust', endpoint: 'POST /tts/synthesize', params: 'target_duration_ms=2000, min_speed=0.5, max_speed=2.0' },
      { step: 3, action: 'Kiểm tra kết quả', endpoint: 'Từ response.time_adjust', params: 'calculated_speed, speed_clamped' },
    ],
  },
]

function APIDocsPanel() {
  const [activeSection, setActiveSection] = useState('stt')
  const [expandedEndpoint, setExpandedEndpoint] = useState(null)
  const [copiedText, setCopiedText] = useState(null)

  const handleCopy = async (text, id) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedText(id)
      setTimeout(() => setCopiedText(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const toggleEndpoint = (endpointId) => {
    setExpandedEndpoint(expandedEndpoint === endpointId ? null : endpointId)
  }

  const currentSection = API_SECTIONS.find(s => s.id === activeSection)

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>API Documentation</h2>
        <p className="description">
          Hướng dẫn sử dụng API cho các dịch vụ STT, TTS và Audio Separator.
          Base URL: <code style={{ background: '#f0f0f0', padding: '2px 6px', borderRadius: '4px' }}>{window.location.origin}</code>
        </p>
      </div>

      {/* Section Navigation */}
      <div className="api-nav" style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' }}>
        {API_SECTIONS.map(section => (
          <button
            key={section.id}
            onClick={() => setActiveSection(section.id)}
            style={{
              padding: '8px 16px',
              border: activeSection === section.id ? '2px solid #2196F3' : '1px solid #ddd',
              borderRadius: '20px',
              background: activeSection === section.id ? '#E3F2FD' : '#fff',
              cursor: 'pointer',
              fontWeight: activeSection === section.id ? 'bold' : 'normal',
            }}
          >
            {section.title}
          </button>
        ))}
      </div>

      {/* Current Section */}
      {currentSection && (
        <div className="api-section">
          <h3 style={{ marginBottom: '8px' }}>{currentSection.title}</h3>
          <p style={{ color: '#666', marginBottom: '20px' }}>{currentSection.description}</p>

          {/* Endpoints */}
          {currentSection.endpoints.map((endpoint, idx) => {
            const endpointId = `${currentSection.id}-${idx}`
            const isExpanded = expandedEndpoint === endpointId

            return (
              <div
                key={endpointId}
                style={{
                  border: '1px solid #ddd',
                  borderRadius: '8px',
                  marginBottom: '12px',
                  overflow: 'hidden',
                }}
              >
                {/* Endpoint Header */}
                <div
                  onClick={() => toggleEndpoint(endpointId)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '12px 16px',
                    background: '#f9f9f9',
                    cursor: 'pointer',
                  }}
                >
                  <span
                    style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      fontWeight: 'bold',
                      color: '#fff',
                      background: endpoint.method === 'GET' ? '#4CAF50' : '#2196F3',
                    }}
                  >
                    {endpoint.method}
                  </span>
                  <code style={{ fontFamily: 'monospace', fontSize: '14px' }}>{endpoint.path}</code>
                  <span style={{ color: '#666', flex: 1 }}>{endpoint.description}</span>
                  <span style={{ fontSize: '12px' }}>{isExpanded ? '▼' : '▶'}</span>
                </div>

                {/* Endpoint Details */}
                {isExpanded && (
                  <div style={{ padding: '16px', borderTop: '1px solid #eee' }}>
                    {/* Parameters */}
                    {endpoint.params.length > 0 && (
                      <div style={{ marginBottom: '16px' }}>
                        <h4 style={{ marginBottom: '8px', fontSize: '14px' }}>Parameters</h4>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                          <thead>
                            <tr style={{ background: '#f5f5f5' }}>
                              <th style={{ padding: '8px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>Name</th>
                              <th style={{ padding: '8px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>Type</th>
                              <th style={{ padding: '8px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>Required</th>
                              <th style={{ padding: '8px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>Description</th>
                            </tr>
                          </thead>
                          <tbody>
                            {endpoint.params.map((param, pIdx) => (
                              <tr key={pIdx}>
                                <td style={{ padding: '8px', borderBottom: '1px solid #eee' }}>
                                  <code>{param.name}</code>
                                </td>
                                <td style={{ padding: '8px', borderBottom: '1px solid #eee', color: '#666' }}>
                                  {param.type}
                                </td>
                                <td style={{ padding: '8px', borderBottom: '1px solid #eee' }}>
                                  {param.required ? (
                                    <span style={{ color: '#f44336' }}>Yes</span>
                                  ) : (
                                    <span style={{ color: '#999' }}>No</span>
                                  )}
                                </td>
                                <td style={{ padding: '8px', borderBottom: '1px solid #eee', color: '#666' }}>
                                  {param.desc}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {/* Response Example */}
                    <div style={{ marginBottom: '16px' }}>
                      <h4 style={{ marginBottom: '8px', fontSize: '14px' }}>Response Example</h4>
                      <pre
                        style={{
                          background: '#1e1e1e',
                          color: '#d4d4d4',
                          padding: '12px',
                          borderRadius: '6px',
                          fontSize: '12px',
                          overflow: 'auto',
                          maxHeight: '200px',
                        }}
                      >
                        {endpoint.response}
                      </pre>
                    </div>

                    {/* cURL Example */}
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <h4 style={{ fontSize: '14px', margin: 0 }}>cURL Example</h4>
                        <button
                          onClick={() => handleCopy(endpoint.curlExample, endpointId)}
                          style={{
                            padding: '4px 12px',
                            border: '1px solid #ddd',
                            borderRadius: '4px',
                            background: copiedText === endpointId ? '#4CAF50' : '#fff',
                            color: copiedText === endpointId ? '#fff' : '#333',
                            cursor: 'pointer',
                            fontSize: '12px',
                          }}
                        >
                          {copiedText === endpointId ? 'Copied!' : 'Copy'}
                        </button>
                      </div>
                      <pre
                        style={{
                          background: '#1e1e1e',
                          color: '#ce9178',
                          padding: '12px',
                          borderRadius: '6px',
                          fontSize: '12px',
                          overflow: 'auto',
                          whiteSpace: 'pre-wrap',
                        }}
                      >
                        {endpoint.curlExample}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Workflow Examples */}
      <div style={{ marginTop: '32px' }}>
        <h3 style={{ marginBottom: '16px' }}>Workflow Examples</h3>
        <div style={{ display: 'grid', gap: '16px' }}>
          {WORKFLOW_EXAMPLES.map(workflow => (
            <div
              key={workflow.id}
              style={{
                border: '1px solid #ddd',
                borderRadius: '8px',
                padding: '16px',
                background: '#fafafa',
              }}
            >
              <h4 style={{ marginBottom: '4px' }}>{workflow.title}</h4>
              <p style={{ color: '#666', marginBottom: '12px', fontSize: '14px' }}>{workflow.description}</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {workflow.steps.map(step => (
                  <div
                    key={step.step}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '12px',
                      padding: '8px',
                      background: '#fff',
                      borderRadius: '4px',
                      border: '1px solid #eee',
                    }}
                  >
                    <span
                      style={{
                        width: '24px',
                        height: '24px',
                        borderRadius: '50%',
                        background: '#2196F3',
                        color: '#fff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '12px',
                        fontWeight: 'bold',
                        flexShrink: 0,
                      }}
                    >
                      {step.step}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: '500', marginBottom: '2px' }}>{step.action}</div>
                      <code style={{ fontSize: '12px', color: '#666' }}>{step.endpoint}</code>
                      <div style={{ fontSize: '12px', color: '#888', marginTop: '2px' }}>{step.params}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Tips */}
      <div style={{ marginTop: '32px', padding: '16px', background: '#E3F2FD', borderRadius: '8px' }}>
        <h4 style={{ marginBottom: '12px' }}>Quick Tips</h4>
        <ul style={{ margin: 0, paddingLeft: '20px', lineHeight: '1.8' }}>
          <li><strong>Job Polling:</strong> Các job STT và Separator là async. Poll mỗi 5 giây cho đến khi <code>status=completed</code></li>
          <li><strong>Base64 Audio:</strong> TTS và Separator trả về audio dạng base64. Decode để lưu file</li>
          <li><strong>File Size:</strong> Giới hạn upload 500MB. Dùng format MP3 để giảm kích thước</li>
          <li><strong>Rate Limit:</strong> Không có rate limit cố định, nhưng nên tránh spam requests</li>
          <li><strong>Error Handling:</strong> Kiểm tra <code>status</code> field trong response. Nếu <code>failed</code>, xem <code>error</code> message</li>
        </ul>
      </div>
    </div>
  )
}

export default APIDocsPanel
