import React, { useState } from 'react'
import SubtitlePanel from './components/SubtitlePanel'
import SeparatorPanel from './components/SeparatorPanel'
import TTSPanel from './components/TTSPanel'
import MetricsPanel from './components/MetricsPanel'
import HealthPanel from './components/HealthPanel'
import './styles/App.css'

function App() {
  const [activeTab, setActiveTab] = useState('subtitle')

  const tabs = [
    { id: 'subtitle', label: 'Subtitle', icon: 'SUB' },
    { id: 'separator', label: 'Separator', icon: 'MIX' },
    { id: 'tts', label: 'TTS', icon: 'TTS' },
    { id: 'metrics', label: 'Metrics', icon: 'MTR' },
    { id: 'health', label: 'Health', icon: 'SYS' },
  ]

  return (
    <div className="app">
      <header className="header">
        <h1>Audio Processing Service</h1>
        <p className="version">v4.0.0</p>
      </header>

      <div className="tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="tab-icon">{tab.icon}</span>
            <span className="tab-label">{tab.label}</span>
          </button>
        ))}
      </div>

      <main className="content">
        {activeTab === 'subtitle' && <SubtitlePanel />}
        {activeTab === 'separator' && <SeparatorPanel />}
        {activeTab === 'tts' && <TTSPanel />}
        {activeTab === 'metrics' && <MetricsPanel />}
        {activeTab === 'health' && <HealthPanel />}
      </main>

      <footer className="footer">
        <p>FastAPI Backend | React Frontend | Whisper ASR | Spleeter</p>
      </footer>
    </div>
  )
}

export default App
