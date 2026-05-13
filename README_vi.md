# SyntheticDataset App

Một ứng dụng web giúp **thiết kế trực quan template bố cục** và sinh **bộ dữ liệu tổng hợp có nhãn** từ các tài nguyên tài liệu cục bộ.

![Tech Stack](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)
![Tech Stack](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB?style=flat-square&logo=react)
![Tech Stack](https://img.shields.io/badge/Image%20Engine-Pillow-FFD43B?style=flat-square)
![Tech Stack](https://img.shields.io/badge/Canvas-Konva.js-E33D28?style=flat-square)

---

## Tổng quan

SyntheticDataset App giải quyết bài toán **thiếu dữ liệu** cho các workflow học từ bố cục tài liệu. Thay vì phải gán nhãn thủ công hàng nghìn ảnh thực tế, bạn chỉ cần thiết kế một *layout template* — xác định khu vực mà các đối tượng thường xuất hiện trên trang — và engine sẽ tự động ghép thư viện asset hiện có của bạn lên các nền tài liệu (document background) “thật” để tạo ra số lượng ảnh huấn luyện có nhãn tuỳ ý.

Toàn bộ quy trình nằm gọn trong một tab trình duyệt:

1. **Tải lên assets** (PNG nền trong của đối tượng)
2. **Thiết kế scenes** — vẽ các vùng (region) trên canvas, gán nhãn/class, tinh chỉnh capacity & augmentation cho từng block
3. **Xem trước (Preview)** — tạo ngay 1 mẫu ảnh “thật”
4. **Sinh dữ liệu (Generate)** — chạy nền để tạo hàng trăm/hàng nghìn ảnh có nhãn
5. **Xuất (Export)** — tải về ZIP (hiện hỗ trợ annotation kiểu YOLO và kiểu COCO)

## Tính năng chính

| Tính năng | Chi tiết |
|---|---|
| **Trình chỉnh sửa Canvas trực quan** | Kéo-thả để vẽ block trên canvas Konva.js với nền xem trước theo thời gian thực |
| **Hỗ trợ nhiều Scene** | Định nghĩa nhiều background scene với bố cục block và trọng số scene độc lập |
| **Tự động lưu (Auto-Save)** | Trạng thái template tự lưu trước khi preview, chuyển scene và generate |
| **Preview “thật”** | Preview tạo ảnh composite thực tế (không chỉ khung wireframe) bằng chính engine dùng để sinh dataset |
| **Quản lý Background** | Upload nền tuỳ chỉnh; scene bị xoá sẽ được xoá cả file vật lý trên server |
| **Định dạng xuất** | Export dataset với nhãn kiểu YOLO **hoặc** COCO JSON (`instances_default.json`) |
| **Sinh bất đồng bộ** | Job chạy lâu được thực thi trong thread nền và có polling tiến độ theo thời gian thực |
| **Tăng cường dữ liệu (Augmentation)** | Theo từng block: xoay ngẫu nhiên, blur, noise, jitter scale và neo vị trí đặt |

---

## Bắt đầu

### Yêu cầu

- Python ≥ 3.10
- Node.js ≥ 18
- Có virtual environment `.venv` ở thư mục gốc repo

### 1. Cài dependencies cho backend

```bash
python -m venv .venv
source .venv/bin/activate
python3 -m pip install -r backend/requirements.txt
```

### 2. Cài dependencies cho frontend

```bash
cd frontend
npm install
```

### 3. Chuẩn bị assets

Đặt các asset tiền cảnh (foreground) vào `backend/tmp/synth_app/assets/` theo cấu trúc sau:

```
assets/
  figure/
    compact_diagram/
      001.png
    wide_diagram/
      002.png
  table/
    wide_strip/
      001.png
  note/
    medium_note/
      001.png
```

- **Thư mục cấp 1** = tên nhãn/class (ví dụ: `figure`, `table`, `note`)
- **Thư mục con** = subtype nội bộ (dùng để lọc trong cấu hình block)
- PNG nền trong cho chất lượng ghép tốt nhất; ảnh không trong suốt cũng được hỗ trợ

### 4. Chạy backend

```bash
# Chạy từ thư mục gốc repo
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Trong lúc phát triển có thể thêm `--reload` để tự reload khi code Python thay đổi.

### 5. Chạy frontend

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Mở [http://127.0.0.1:5173](http://127.0.0.1:5173) trên trình duyệt.

---

## Một số ảnh demo
### Tải assets
![Upload UI](demo/upload-ui.png)

### Tạo scene
![Editor UI](demo/editor-ui.png)

### Thiết kế bố cục
![Editor UI](demo/editor-ui.png)

### Xem trước một mẫu sinh ra
![Preview demo](demo/preview.png)

### Cấu hình và bắt đầu generate
![Generate UI](demo/generate-ui.png)

### Job hoàn tất và sẵn sàng export 
![Done UI](demo/done.png)
---
