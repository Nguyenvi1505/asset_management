import socket
import logging
from waitress import serve
from app import create_app, init_db

from app.utils import get_local_ip
# Thiết lập ghi log để theo dõi lỗi nếu có
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('waitress')

if __name__ == '__main__':
    # Tạo app instance từ Application Factory
    app = create_app()

    # Đảm bảo Database đã được khởi tạo
    init_db(app)
   
    # Lấy IP mạng LAN của máy chủ
    local_ip = get_local_ip()
   
    print("\n=========================================================")
    print("🚀 HỆ THỐNG QUẢN LÝ TÀI SẢN MÁY ĐANG CHẠY (PRODUCTION)")
    print("=========================================================")
    print(f"🏠 Nếu truy cập tại máy này: http://localhost:8080")
    print(f"🌐 Nếu truy cập từ máy khác trong xưởng: http://{local_ip}:8080")
    print("=========================================================\n")
   
    # Khởi động máy chủ Waitress
    serve(app, host='0.0.0.0', port=8080, threads=6)
