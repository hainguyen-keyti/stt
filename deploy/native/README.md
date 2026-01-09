# 7KT-AI Native Installation

Chạy trực tiếp trên máy để sử dụng **100% tài nguyên phần cứng**.

**Tự động tải Python, FFmpeg** - không cần cài trước!

## Yêu cầu

- Git (Mac: Xcode CLT, Linux: package manager, Windows: tự động tải)
- Node.js 18+ (optional, cho web UI)

## Cài đặt nhanh

### Linux/Mac
```bash
# Tạo thư mục và tải install script
mkdir my-stt && cd my-stt
curl -fsSL https://raw.githubusercontent.com/hainguyen-keyti/stt/master/deploy/native/install.sh -o install.sh
chmod +x install.sh
./install.sh
```

### Windows
1. Tạo thư mục mới
2. Download `install.bat` vào thư mục đó
3. Double-click để chạy

## Khởi động

```bash
./start.sh      # Linux/Mac
start.bat       # Windows
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

Xóa thư mục cài đặt (bao gồm cả Python, FFmpeg):

```bash
rm -rf /path/to/install-dir    # Linux/Mac
rmdir /s /q C:\path\to\dir     # Windows
```

## Cập nhật

```bash
git pull
source venv/bin/activate  # Linux/Mac
# hoặc: venv\Scripts\activate.bat  # Windows
pip install -r requirements.txt
```
