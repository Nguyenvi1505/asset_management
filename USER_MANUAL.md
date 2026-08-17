# 📖 Hướng Dẫn Sử Dụng Hệ Thống (User Manual)

Tài liệu này là cẩm nang toàn diện hướng dẫn cách sử dụng **Hệ Thống Quản Lý Tài Sản & Phiên Bản Chương Trình Máy** dành cho Kỹ sư bảo trì, Người quản lý và Quản trị viên (Admin).

---

## 🔐 1. Đăng Nhập, Xin Cấp Tài Khoản & Bảo Mật

Hệ thống quản lý dữ liệu gốc của nhà máy, mang tính bảo mật nội bộ cao. Do đó, hệ thống không mở đăng ký tự do.

1. **Yêu cầu Cấp tài khoản mới**: 
   - Tại màn hình Đăng nhập, nhấn nút **"Yêu cầu cấp tài khoản"**.
   - Điền trung thực các thông tin: *Họ tên, Email liên hệ, Xưởng làm việc, Chức vụ*.
   - Nhấn gửi. Yêu cầu của bạn sẽ được chuyển vào hàng đợi để Admin xét duyệt.
2. **Yêu cầu Đặt lại Mật khẩu**:
   - Nếu lỡ quên mật khẩu, hãy nhấn nút **"Quên mật khẩu"** ở màn hình đăng nhập.
   - Nhập Username và Email. Admin sẽ phê duyệt và hệ thống tự động sinh một mật khẩu mới ngẫu nhiên cấp lại cho bạn.
3. **Đăng nhập & Đổi mật khẩu**: 
   - Sau khi được Admin cấp (hoặc reset), bạn dùng Username và Password để đăng nhập.
   - **Lưu ý quan trọng**: Ngay sau khi đăng nhập thành công, hãy click vào góc phải trên cùng (Hồ sơ cá nhân) để tự đổi lại mật khẩu cho dễ nhớ.
4. **Tự động Đăng xuất (Auto-Logout)**:
   - Nếu bạn đăng nhập tại máy tính chung dưới xưởng nhưng lại bỏ đi làm việc khác, hệ thống sẽ **tự động đăng xuất sau 15 phút** không có bất kỳ tương tác nào (chuột, bàn phím) để ngăn chặn người lạ can thiệp.

---

## 🏭 2. Quản Lý Tài Sản (Dành cho Admin & Kỹ sư được phân quyền)

Tài sản trong hệ thống được quản lý logic theo mô hình 3 lớp: **Xưởng ➔ Máy móc ➔ Thiết Bị**.

### 2.1. Quản lý Xưởng (Factory)
- Truy cập menu **"Quản lý Xưởng"**.
- Nhấn **"Thêm Xưởng Mới"** và nhập Tên (VD: Xưởng Dập, Xưởng Lắp Ráp) cùng Mô tả. Xưởng là đơn vị cấp cao nhất.

### 2.2. Quản lý Máy móc (Machine)
- Truy cập vào một Xưởng bất kỳ, bạn sẽ thấy danh sách Máy móc.
- Nhấn **"Thêm Máy Mới"** để khai báo tổ hợp máy. *(Ví dụ: Máy dán nhãn tự động, Băng tải Pallet).*

### 2.3. Quản lý Thiết bị (Device)
- Một chiếc máy (Machine) thường được cấu thành từ nhiều phần cứng điều khiển (Device) như PLC, Màn hình HMI, Biến tần...
- Trong màn hình chi tiết của một Máy, nhấn **"Thêm Thiết Bị"**.
- **Khai báo Định dạng**: Bạn bắt buộc phải khai báo định dạng file hỗ trợ (VD: `.cxp`, `.st`, `.zap16`). Việc này giúp rào lỗi, chặn kỹ sư upload nhầm file văn bản hoặc file rác lên hệ thống.
- **Tuỳ chọn Backup Folder**: Một số phần mềm (như TIA Portal) lưu code dạng nguyên một thư mục thay vì 1 file. Đối với các thiết bị này, khi tạo hãy tick vào ô **"Cho phép tải lên Backup"**. Nó sẽ mở ra một tính năng cho phép kỹ sư nén thư mục lại thành `.zip` hoặc `.rar` và upload kèm theo mã nguồn chính.

---

## 🗂️ 3. Quản Lý Phiên Bản & Upload Chương Trình (Tính Năng Lõi)

Đây là thao tác sống còn đối với mọi kỹ sư Tự động hoá. Bất cứ khi nào bạn chỉnh sửa chương trình máy dưới xưởng xong, bạn phải cập nhật lên Web để lưu trữ.

1. Vào mục **Thiết Bị** tương ứng.
2. Nhấn **"Upload Phiên Bản Mới"**.
3. **Mã phiên bản**: Đặt tên gợi nhớ (Ví dụ: `V1.2` hoặc `2026.08.16_FixLoi`).
4. **Ghi chú (Changelog)**: Bắt buộc! Bạn phải ghi rõ bạn đã thay đổi logic gì, sửa lỗi ở block nào để người tiếp quản hoặc Admin nắm được.
5. **Đính kèm file**: 
   - Tải file chương trình chính lên (phải đúng đuôi mở rộng đã khai báo).
   - Nếu thiết bị có cấu hình Backup, giao diện sẽ xuất hiện thêm ô **Tải lên Folder Backup (.zip, .rar)**.
6. **Bộ lọc thông minh (Anti-Duplication)**: Khi bạn bấm Upload, thuật toán Băm (Hash) của máy chủ sẽ quét file. Nếu phát hiện file này nội dung y hệt 100% so với phiên bản bạn vừa tải lên tuần trước, hệ thống sẽ từ chối và báo lỗi: *"File không có sự thay đổi"*.

> **Tính năng Tải Xuống**: Tại danh sách phiên bản, bất kỳ tài khoản nào cũng có thể nhấn nút xanh để **Tải Source Code** hoặc nút cam để **Tải File Backup**. Lịch sử ai đã tải file gì, lúc mấy giờ đều được hệ thống ghi hình lại.

---

## 🗑️ 4. Xóa Mềm & Khôi Phục (Recycle Bin)

Để tránh rủi ro lỡ tay bấm Xóa làm bốc hơi toàn bộ tài sản, hệ thống sử dụng cơ chế **Thùng Rác (Soft-delete)**.

1. Khi bạn nhấn Xóa một Xưởng, Máy, hoặc Thiết bị, nó chỉ bị ẩn đi khỏi giao diện và bị tước quyền truy cập. File vật lý vẫn nằm an toàn trên Server.
2. **Khôi phục**: Chỉ có Admin mới được vào mục **"Thùng Rác"** trên Menu.
3. Trong Thùng rác, Admin có 2 quyền quyết định:
   - ♻️ **Khôi phục (Restore)**: Phục sinh dữ liệu, đưa nó quay về vị trí ban đầu.
   - 💀 **Tiêu hủy (Hard Delete)**: Xóa sổ vĩnh viễn khỏi ổ cứng (Không thể khôi phục). Dùng để dọn dẹp giải phóng dung lượng.

---

## 👑 5. Phân Hệ Quản Trị Hệ Thống (Chỉ dành cho Admin)

Menu "Hệ Thống" bên thanh Sidebar chỉ xuất hiện nếu tài khoản của bạn có quyền `admin`.

### 5.1. Quản Lý Yêu Cầu Tích Hợp
- Khi có nhân viên mới xin cấp TK hoặc xin Reset MK, hệ thống sẽ hiện biểu tượng số (Badge) màu đỏ.
- Truy cập **"Quản lý Yêu cầu"**. Tại đây có 2 Tab rất rõ ràng: **Yêu cầu Tạo TK** và **Yêu cầu Đặt lại MK**.
- Bạn có quyền Từ chối hoặc Duyệt. Nếu Duyệt, hệ thống tự động sinh ra mật khẩu ngẫu nhiên độ khó cao, hiển thị hộp thoại, và hỗ trợ bạn tự động mở ứng dụng gửi Email cho người đó.

### 5.2. Nhật Ký Hoạt Động (Audit Logs)
- Đây là "Hộp đen" của nhà máy. Ghi lại 100% mọi thao tác: Tên người dùng, Hành động (Thêm/Sửa/Xóa/Tải), Thời gian, và Địa chỉ IP.
- Bạn có thể **Lọc theo ngày/tháng**, tìm tên kỹ sư, và nhấn **Export CSV** để làm báo cáo.
- Hệ thống sẽ tự dọn dẹp các dòng Log quá 1 năm, hoặc bạn có thể tự dọn thủ công các Log cũ hơn 6 tháng để làm nhẹ Web.

### 5.3. Radar Cảnh Báo An Ninh (BÁO ĐỘNG ĐỎ)
- Ứng dụng tích hợp một vệ sĩ mạng chạy ngầm (Background Scheduler). Cứ mỗi vài tiếng, nó sẽ tự lùng sục ổ cứng máy chủ và đối chiếu với Database.
- Nếu phát hiện có người cắm USB vào Server sửa trộm file chương trình, hoặc cố tình xóa file không thông qua Website, lập tức màn hình Log sẽ bắn ra dòng: `BÁO ĐỘNG ĐỎ! Sai Hash / Mất file`. Bạn cần kiểm tra ngay lập tức.

### 5.4. Backup & Khôi Phục Hệ Thống Toàn Diện
- Truy cập **Dữ liệu > Xuất bản sao lưu**. Hệ thống sẽ tự nén toàn bộ Database, hình ảnh, file Source code, file Backup `.zip`, và cả dữ liệu trong Thùng rác lại thành 1 cục nén `.zip` duy nhất.
- Hãy cất kỹ file ZIP này. Nếu ngày mai Server nhà máy bị cháy ổ cứng, bạn chỉ cần mua ổ cứng mới, cài lại code gốc, sau đó vào **Dữ liệu > Nhập phục hồi**, tải file ZIP đó lên. Toàn bộ hệ thống hàng trăm máy móc của bạn sẽ sống lại y như cũ sau vài giây!
