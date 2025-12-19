# STT - Speech to Text Subtitle Service

Dịch vụ tạo phụ đề chuyên nghiệp từ audio/video sử dụng Whisper AI.

## Tính năng

- Hỗ trợ nhiều engine: **faster-whisper** (nhanh) và **OpenAI Whisper** (chính xác)
- Xuất file **SRT** và **JSON**
- 11 preset được tối ưu cho các use case khác nhau
- Giao diện web thân thiện
- API RESTful đầy đủ

## Yêu cầu

- Docker
- Git

## Cài đặt & Chạy

```bash
# Clone repo
git clone https://github.com/hainguyen-keyti/stt.git
cd stt

# Deploy
chmod +x deploy.sh
./deploy.sh
```

## Truy cập

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

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/subtitle` | Upload audio và tạo phụ đề |
| GET | `/subtitle/jobs/{job_id}` | Lấy trạng thái job |
| GET | `/presets/` | Danh sách presets |
| GET | `/health` | Health check |

## Cấu trúc thư mục

```
stt/
├── api/                 # FastAPI backend
│   ├── routers/         # API endpoints
│   ├── models/          # Pydantic models
│   ├── schemas/         # Validation schemas
│   └── utils/           # Utilities
├── lib/                 # Core library
│   ├── engines/         # Whisper engines
│   └── formatters/      # SRT/JSON formatters
├── web/                 # React frontend
│   └── src/
│       ├── components/  # UI components
│       └── services/    # API client
├── presets/             # Preset configurations
├── Dockerfile
├── deploy.sh
└── requirements.txt
```

## Lưu ý

- Lần đầu chạy sẽ download model (~1.5GB cho turbo)
- Model được cache trong Docker volume để tái sử dụng
- Cloud Shell có giới hạn tài nguyên, nên dùng VM có GPU cho production
