# Test Audio Fixtures

This directory contains audio files for testing the subtitle generation service.

## Required Test Fixtures

### For MVP (Phase 3 - US1):
- **13min_sample.mp3**: 13-minute audio sample for speed benchmarking (<90s target)
- **clean_speech.wav**: 5-second clean speech sample for accuracy testing

### For Future Phases:
- **music_background.mp3**: Audio with background music for preprocessing tests
- **noisy_speech.wav**: Low SNR audio for noise handling tests
- **ground_truth.wav**: Audio with manually verified timestamps
- **ground_truth.json**: Ground truth timestamps for accuracy validation
- **music_video_truth.txt**: Ground truth text for WER calculation

## Creating Test Fixtures

You can create test fixtures using:
1. **Your own recordings**: Record or use existing audio files
2. **Public domain audio**: Download from sources like LibriVox
3. **Test-to-speech**: Generate using tools like `espeak` or online TTS
4. **YouTube-DL**: Extract audio from videos (respect copyright)

### Example: Generate short test audio with espeak

```bash
# Install espeak (Mac)
brew install espeak

# Generate 5s test audio
espeak "Hello world. This is a test of the subtitle generation service." -w clean_speech.wav

# Convert to MP3 if needed
ffmpeg -i clean_speech.wav -acodec libmp3lame -ab 128k clean_speech.mp3
```

## File Format Guidelines

- **Formats**: MP3, WAV, M4A, FLAC, OGG, OPUS, WebM
- **Sample Rate**: 16kHz or higher recommended
- **Channels**: Mono or stereo
- **Bit Depth**: 16-bit or 24-bit for WAV
- **Max Size**: 500MB per file (API limit)

## Testing Without Real Audio

For development/CI without audio files:
- Unit tests mock audio processing
- Integration tests check API structure without actual transcription
- Performance tests are skipped if fixtures are missing
