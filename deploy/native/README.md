# 7KT-AI Native Installation

Chạy trực tiếp trên máy để sử dụng **100% tài nguyên phần cứng**.

**Python được tải tự động** - không cần cài Python trước!

## Yêu cầu

- Git
- FFmpeg
- Node.js 18+ (optional, cho web UI)

**Không cần cài Python** - script sẽ tự tải Python 3.11 vào thư mục project.

## Cài đặt nhanh

### Linux/Mac
```bash
# Tải và chạy
curl -fsSL https://raw.githubusercontent.com/hainguyen-keyti/stt/master/deploy/native/install.sh -o install.sh
chmod +x install.sh
./install.sh
```

### Windows
1. Download `install.bat`
2. Double-click để chạy

## Khởi động

### Linux/Mac
```bash
cd ~/stt
./start.sh
```

### Windows
```batch
cd %USERPROFILE%\stt
start.bat
```

## Truy cập

- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Hardware Support

| Platform | GPU Support | Performance |
|----------|-------------|-------------|
| Mac M1/M2/M3/M4 | MPS (Apple Silicon) | Tốt nhất |
| Windows + NVIDIA | CUDA | Tốt nhất |
| Linux + NVIDIA | CUDA | Tốt nhất |
| Linux + AMD | ROCm | Tốt |
| Không có GPU | CPU | Chậm hơn |

## Gỡ cài đặt

Xóa hoàn toàn (bao gồm cả Python):

### Linux/Mac
```bash
rm -rf ~/stt
```

### Windows
```batch
rmdir /s /q %USERPROFILE%\stt
```

## Cập nhật

```bash
cd ~/stt
git pull
source venv/bin/activate  # Linux/Mac
# hoặc: venv\Scripts\activate.bat  # Windows
pip install -r requirements.txt
```
