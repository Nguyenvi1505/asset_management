# Hướng Dẫn Sử Dụng Database Migration (Alembic)

Dự án này sử dụng **Flask-Migrate** (dựa trên lõi **Alembic**) để quản lý cấu trúc cơ sở dữ liệu (Database Schema). 

Thay vì phải xóa đi tạo lại Database mỗi khi bạn muốn thêm cột, đổi tên bảng, hoặc thay đổi kiểu dữ liệu, Alembic giúp bạn sinh ra các đoạn code theo dõi lịch sử và cập nhật (upgrade) Database một cách an toàn mà **không làm mất dữ liệu cũ**.

---

## 1. Vòng Đời Cập Nhật Database Cơ Bản

Mỗi khi bạn cần thay đổi gì đó ở Database, hãy làm theo đúng 3 bước chuẩn sau:

### Bước 1: Chỉnh sửa file `models.py`
Mở file `models.py` và tiến hành sửa đổi các class (Model) theo ý muốn.
Ví dụ: Thêm cột `phone_number` vào bảng `users`.

```python
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    
    # Bạn gõ đoạn code này thêm vào file:
    phone_number = db.Column(db.String(15), nullable=True) 
```

### Bước 2: Sinh file Migration
Mở terminal (PowerShell/CMD), đảm bảo bạn đang ở thư mục gốc của dự án (nơi chứa `server.py`). Chạy lệnh sau:

```bash
# Trên Windows PowerShell:
$env:FLASK_APP="server.py"; flask db migrate -m "Them cot phone number cho User"

# Trên Linux/Mac:
FLASK_APP=server.py flask db migrate -m "Them cot phone number cho User"
```

*Lưu ý: Chữ trong ngoặc kép `""` là mô tả để sau này bạn nhìn lại hiểu được bản cập nhật này làm gì (giống như commit code).*
Hệ thống sẽ tự động quét, phát hiện sự thay đổi và sinh ra một file code trong thư mục `migrations/versions/`.

### Bước 3: Áp dụng thay đổi vào Database
Chạy lệnh sau để thực thi file vừa sinh ra vào trong file `asset_management.db` thực tế:

```bash
# Trên Windows PowerShell:
$env:FLASK_APP="server.py"; flask db upgrade

# Trên Linux/Mac:
FLASK_APP=server.py flask db upgrade
```
**Xong!** Bây giờ bảng `users` đã có thêm cột `phone_number` và tất cả dữ liệu cũ của bạn vẫn còn nguyên vẹn.

---

## 2. Các Lệnh Nâng Cao Khác

### Hạ cấp (Rollback) Database
Nếu bạn vừa lỡ chạy `upgrade` nhưng phát hiện code bị lỗi và muốn quay ngược thời gian về phiên bản Database trước đó:
```bash
flask db downgrade
```

### Xem lịch sử các phiên bản
Để xem danh sách các lần chỉnh sửa Database từ lúc mới lập trình đến nay:
```bash
flask db history
```

### Xem trạng thái hiện tại
Để kiểm tra xem Database thực tế có đang ở phiên bản code mới nhất không:
```bash
flask db current
```

---

## 3. Khắc Phục Sự Cố Thường Gặp

- **Lỗi `table already exists` hoặc `column already exists`**: Lỗi này xảy ra khi Database thực tế của bạn ĐÃ CÓ cái bảng/cột đó rồi, nhưng trong lịch sử Alembic lại không biết. Bạn có thể ép Alembic bỏ qua lỗi và đánh dấu là "đã đồng bộ" bằng lệnh: `flask db stamp head`.
- **Ghi đè file SQLite**: Hãy nhớ lệnh `flask db migrate` chỉ cập nhật cấu trúc (schema). Nếu bạn lỡ xóa nhầm thư mục `data/database/asset_management.db`, bạn chỉ cần chạy lệnh `flask db upgrade` là hệ thống sẽ tự động tạo lại cho bạn một file DB mới hoàn toàn với 100% các bảng đầy đủ nhất.
