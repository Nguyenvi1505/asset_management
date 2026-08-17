# 🏭 Hệ Thống Quản Lý Tài Sản & Phiên Bản Chương Trình Máy (Asset Management System)

Chào mừng bạn đến với **Hệ Thống Quản Lý Tài Sản & Phiên Bản Chương Trình Máy** (Asset Management System). Đây là một ứng dụng Web chuyên nghiệp được xây dựng bằng **Python (Flask)**, thiết kế đặc thù để giải quyết bài toán quản lý phần cứng và kiểm soát mã nguồn (version control) của các chương trình điều khiển trong môi trường nhà máy công nghiệp.

Hệ thống giúp các kỹ sư dễ dàng lưu trữ, theo dõi và phục hồi các tệp chương trình chạy trên **PLC, HMI, Servo, Robot, Inverter...**, đảm bảo mọi sự thay đổi đều được ghi vết, bảo mật tuyệt đối và vận hành ổn định 24/7.

---

## 🌟 1. Tính Năng Cốt Lõi (Core Features)

### 📂 1.1. Cấu Trúc Quản Lý Phân Cấp Chặt Chẽ
Hệ thống tổ chức dữ liệu theo sơ đồ cây 3 cấp trực quan, chuẩn công nghiệp:
- **Xưởng (Factory)**: Ví dụ "Xưởng Đột Dập", "Xưởng Lắp Ráp".
- **Máy móc (Machine)**: Trực thuộc Xưởng. Ví dụ "Máy Cắt Laser CNC", "Robot Hàn Yaskawa".
- **Thiết bị (Device)**: Trực thuộc Máy móc. Nơi thực sự chứa các file chương trình (VD: "PLC Siemen S7-1500", "Màn hình HMI Proface").

### 🕒 1.2. Kiểm Soát Phiên Bản (Version Control)
- **Tải lên không giới hạn**: Lưu giữ toàn bộ lịch sử các phiên bản chương trình cho mỗi Thiết bị.
- **Hỗ trợ Đóng gói Thư mục (Backup Folder)**: Hỗ trợ tuỳ chọn upload kèm một file nén `.zip` hoặc `.rar` bên cạnh file mã nguồn chính (Rất hữu ích cho các dự án TIA Portal hoặc CX-Programmer có nhiều file rác đi kèm).
- **Ghi chú (Changelog) bắt buộc**: Yêu cầu kỹ sư phải ghi lại lý do sửa đổi để dễ dàng truy xuất sau này.
- **Thuật toán Chống Trùng lặp (Anti-Duplication)**: Sử dụng băm SHA-256 phân tích nội dung file ở mức nhị phân. Nếu file mới giống hệt phiên bản cũ 100%, hệ thống tự động từ chối để tiết kiệm bộ nhớ máy chủ.

### ♻️ 1.3. Thùng Rác & Phục Hồi Dữ Liệu (Soft-Delete)
- **Xóa mềm an toàn**: Khi kỹ sư lỡ tay xóa một Xưởng, Máy, hoặc Phiên bản, dữ liệu không biến mất ngay. Chúng bị gắn nhãn `deleted` và chuyển vào `Thùng Rác`.
- Admin nắm quyền sinh sát tại Thùng rác: Có thể **Khôi phục (Restore)** hoặc **Tiêu hủy vĩnh viễn (Hard Delete)**.

### 🛡️ 1.4. Phân Quyền & Quy Trình Khép Kín (RBAC)
- **Bảo mật nội bộ**: Chặn tự do đăng ký. Cung cấp một cổng Gửi Yêu Cầu (Cấp tài khoản / Quên mật khẩu) duy nhất tại màn hình đăng nhập.
- **Auto-Logout**: Tự động văng đăng xuất nếu người dùng treo máy không tương tác quá 15 phút.
- Phân quyền chặt chẽ:
  - **Admin**: Toàn quyền cấu hình, duyệt tài khoản, dọn rác, xem log, Backup hệ thống.
  - **Viewer/Kỹ sư**: Quyền thao tác cơ bản, upload/download phần mềm và quản lý tài sản xưởng.

### 🕵️ 1.5. Nhật Ký Hoạt Động (Audit Logs) & Báo Động Đỏ
- **Ghi vết 100%**: Mọi hành động (Thêm/Sửa/Xóa/Download/Upload) đều được lưu vào Database kèm theo tên người thực hiện và thời gian chính xác. Hỗ trợ trích xuất `.csv`.
- **Trình quét Toàn vẹn (Integrity Scanner)**: Hệ thống chạy ngầm liên tục để quét ổ cứng máy chủ. Nếu ai đó bí mật xóa hoặc sửa file vật lý mà không thông qua Web, hệ thống tự sinh ra một Log Báo Động Đỏ cảnh báo Admin.

### 💾 1.6. Backup & Khôi Phục Hệ Thống Toàn Diện
- Cho phép xuất (Export) toàn bộ máy chủ (Database, File chương trình, File Backup, Thùng rác) thành một cục nén `.zip` duy nhất bằng 1 cú click chuột.
- Hỗ trợ Import file `.zip` này để phục hồi khẩn cấp 100% hiện trạng khi máy chủ bị cháy hỏng phần cứng hoặc chuyển đổi server.

---

## 🛠️ 2. Công Nghệ Sử Dụng (Tech Stack)

* **Backend**: Python (Flask 3.0.3)
* **Database**: **SQLite** (Nhẹ, không cần cài server DB rời). Tích hợp ORM **SQLAlchemy** và **Flask-Migrate**.
* **Bảo mật**: Flask-Login, Werkzeug (Hash BCrypt), Flask-WTF (Chống CSRF).
* **Tác vụ ngầm**: **APScheduler** (Chạy nền dọn rác và quét bảo mật ổ cứng).
* **Web Server (Production)**: **Waitress** (Xử lý đa luồng mạnh mẽ trên Windows/Linux).
* **Giao diện**: HTML5, CSS3, JavaScript thuần, Jinja2, Bootstrap 5, SweetAlert2.

---

## 📁 3. Cấu Trúc Dự Án (Project Structure)

```text
asset_management/
├── app/                        # Thư mục mã nguồn chính của Flask
│   ├── routes/                 # Các Blueprints chia nhỏ module chức năng
│   ├── extensions.py           # Khởi tạo db, login_manager, csrf...
│   ├── utils.py                # Hàm tiện ích (hash file, check role...)
│   └── __init__.py             # Nơi lắp ráp ứng dụng Flask (Factory Pattern)
├── data/                       # Chứa DỮ LIỆU THỰC TẾ (Cần backup thường xuyên)
│   ├── database/               # File asset_management.db
│   ├── uploads/                # File chương trình PLC/HMI và file zip backup
│   └── deleted_assets/         # Thùng rác chứa các file bị xóa mềm
├── server_tools/               # CÔNG CỤ QUẢN TRỊ SERVER (Bật/Tắt Web)
│   ├── start_server.bat        # Vòng lặp chạy server, tự động restart khi crash
│   ├── stop_server.bat         # Kịch bản dọn dẹp tiến trình Python ẩn
│   └── run_hidden.vbs          # Kịch bản chạy server Ẩn hoàn toàn (Nền)
├── static/                     # Chứa CSS, JS, Icon tĩnh, Font
├── templates/                  # Các file giao diện HTML (Jinja2)
├── .env                        # File biến môi trường (Database URL, Chế độ chạy)
├── config.py                   # Lớp cấu hình DevelopmentConfig, ProductionConfig
├── models.py                   # Định nghĩa các Bảng (Tables)
├── requirements.txt            # Danh sách thư viện Python phụ thuộc
└── server.py                   # File Entry point - Khởi chạy Web Server
```

---

## 🚀 4. Hướng Dẫn Cài Đặt (Dành cho Lập trình viên)

**Bước 1: Tải source code và cài đặt Python (Yêu cầu Python 3.8+)**

**Bước 2: Cài đặt các gói phụ thuộc**
```bash
pip install -r requirements.txt
```

**Bước 3: Cấu hình biến môi trường**
Tạo file `.env` ở thư mục gốc (ngang hàng với `server.py`). Nội dung mẫu:
```env
# Chuỗi bảo mật Session Cookie
FLASK_SECRET_KEY=chuoi_ky_tu_bi_mat_cua_ban

# Mật khẩu khởi tạo cho tài khoản Admin đầu tiên
ADMIN_DEFAULT_PASS=Admin_Asset@2026!

# Môi trường chạy (development / production)
FLASK_ENV=development

# Đường dẫn Database
DATABASE_URL=sqlite:///data/database/asset_management.db
```

**Bước 4: Khởi động Ứng dụng để code**
```bash
py server.py
```
> Trong lần chạy đầu tiên, hệ thống sẽ tự sinh Database và tạo 1 tài khoản `admin` (Pass lấy từ biến môi trường).

---

## 🌍 5. Hướng Dẫn Triển Khai Ở Nhà Máy (Production Deployment)

Khi mang hệ thống cài đặt lên một máy tính dùng chung (Server) dưới xưởng, bạn không nên chạy bằng Terminal (cmd) vì rất dễ bị người khác bấm tắt nhầm. Hãy làm theo chuẩn sau:

1. Chỉnh sửa file `.env`, đổi `FLASK_ENV` thành `production`.
2. Mở thư mục **`server_tools`** trong source code.
3. Nhấp đúp chuột vào file **`run_hidden.vbs`**.
   - Lúc này Server đã được khởi động và **chạy ngầm** hoàn toàn (Không có cửa sổ đen nào hiện lên).
   - Server tích hợp sẵn cơ chế **Auto-Restart**: Nếu ứng dụng gặp lỗi crash, nó sẽ tự khởi động lại sau 5 giây.
4. (Tuỳ chọn) Để hệ thống tự bật khi Server khởi động lại (sau khi cúp điện), hãy nhấn `Win + R`, gõ `shell:startup`, và copy file `run_hidden.vbs` vào đó.
5. Để truy cập, từ bất kỳ máy tính nào trong cùng mạng LAN, mở Chrome gõ: `http://<IP-CỦA-MÁY-CHỦ>:8080`.
6. Để **Tắt hoàn toàn** hệ thống: Mở thư mục `server_tools` và chạy file **`stop_server.bat`**.

---

## 🆘 6. Xử lý Lỗi Thường Gặp (Troubleshooting)

**1. Lỗi `sqlite3.OperationalError: unable to open database file`**
- Không cần bận tâm! Hệ thống (file `config.py`) đã tự động tính toán đường dẫn tuyệt đối bất chấp việc bạn đặt thư mục code ở ổ C, D hay E. Chỉ cần đảm bảo file `.env` viết đúng `sqlite:///data/database/asset_management.db`.

**2. Quên mật khẩu Admin duy nhất**
- Vào thư mục `data/database/` xóa file `.db` đi, sau đó khởi động lại server. Hệ thống sẽ tạo lại DB mới và cấp lại pass mặc định (Nhưng dữ liệu cũ sẽ mất hết). Bạn nên dùng chức năng Export ZIP thường xuyên.

**3. Upload file lớn bị lỗi (HTTP 413 Payload Too Large)**
- Mặc định giới hạn đang là **500MB**. Nếu file chương trình máy (hoặc file backup) nặng hơn, hãy vào `config.py` tăng thông số `MAX_CONTENT_LENGTH`.

---
*Phát triển chuyên biệt cho môi trường tự động hóa nhà máy.*
