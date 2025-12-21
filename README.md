# Audio Processing Service

Dịch vụ xử lý audio chuyên nghiệp: tạo phụ đề và tách/mix âm thanh.

## Tính năng

### Speech-to-Text (STT)
- Hỗ trợ nhiều engine: **faster-whisper** (nhanh) và **OpenAI Whisper** (chính xác)
- Xuất file **SRT** và **JSON**
- 11 preset được tối ưu cho các use case khác nhau

### Audio Separator
- Tách **vocal** và **instrumental** từ audio
- Điều chỉnh âm lượng từng track
- Mix lại với tỷ lệ tùy chọn
- Sử dụng **Spleeter** - tối ưu cho CPU

### Chung
- Giao diện web thân thiện
- API RESTful đầy đủ

## Yêu cầu

- Python 3.11+
- Node.js 18+
- FFmpeg
- Git

## Chạy Local (Development)

### Backend

```bash
# Tạo virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc: venv\Scripts\activate  # Windows

# Cài dependencies
pip install -r requirements.txt
pip install faster-whisper openai-whisper

# Chạy API server
PYTHONPATH=. uvicorn api.main:app --reload --port 8000
```

### Frontend

```bash
cd web
npm install
npm run dev
```

### Truy cập Development

- **Frontend:** http://localhost:3050
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

---

## Deploy Production (Docker)

```bash
# Clone repo
git clone https://github.com/hainguyen-keyti/stt.git
cd stt

# Deploy
chmod +x deploy.sh
./deploy.sh
```

### Truy cập Production

- **Web UI:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Presets có sẵn

| Preset | Engine | Mô tả |
|--------|--------|-------|
| Dialogue | openai-whisper | Hội thoại 2+ người, có nhạc nền |
| Movie/Film | openai-whisper | Phim, nhạc nền và hiệu ứng |
| Interview | openai-whisper | Phỏng vấn, podcast |
| Lecture | faster-whisper | Bài giảng, thuyết trình |
| Karaoke | openai-whisper | Lyrics, word-level timing |
| Fast | faster-whisper | Xử lý nhanh, batch processing |
| Accurate | openai-whisper | Độ chính xác cao nhất |
| Chinese | openai-whisper | Tiếng Trung |
| Vietnamese | openai-whisper | Tiếng Việt |
| English | faster-whisper | Tiếng Anh |
| Default | faster-whisper | Cài đặt mặc định |

## API Endpoints

### Speech-to-Text
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/subtitle/` | Upload audio và tạo phụ đề |
| GET | `/subtitle/jobs/{job_id}` | Lấy trạng thái job |
| GET | `/presets/` | Danh sách presets |

### Audio Separator
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/separator/` | Tách và mix audio |
| GET | `/separator/jobs/{job_id}` | Lấy trạng thái job |

### System
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/health` | Health check |
| GET | `/metrics` | Service metrics |

## Cấu trúc thư mục

```
stt/
├── api/                        # FastAPI backend (API gateway)
│   ├── routers/                # API endpoints
│   ├── models/                 # Pydantic models
│   ├── schemas/                # Validation schemas
│   └── utils/                  # Utilities
├── modules/                    # Core modules
│   ├── stt/                    # Speech-to-Text module
│   │   ├── engines/            # ASR engines (faster-whisper, openai-whisper)
│   │   ├── formatters/         # Output formatters (SRT, JSON)
│   │   ├── presets/            # Preset configurations
│   │   └── utils/              # Module utilities
│   └── audio_separator/        # Audio Separator module
│       ├── engines/            # Separation engines (Spleeter)
│       ├── mixer.py            # Audio mixing utilities
│       └── service.py          # High-level service API
├── web/                        # React frontend
│   └── src/
│       ├── components/         # UI components
│       └── services/           # API client
├── Dockerfile
├── deploy.sh
└── requirements.txt
```

## Lưu ý

- Lần đầu chạy sẽ download model (~1.5GB cho turbo)
- Model được cache trong Docker volume để tái sử dụng
- Cloud Shell có giới hạn tài nguyên, nên dùng VM có GPU cho production
