import os
from dotenv import load_dotenv

# Xác định đường dẫn thư mục gốc của dự án
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

DATA_DIR = os.path.join(basedir, 'data')

def resolve_db_url(url):
    """Tự động chuyển đường dẫn SQLite tương đối thành tuyệt đối theo thư mục gốc."""
    if url and url.startswith('sqlite:///') and ':' not in url[10:] and not url.startswith('sqlite:////'):
        return 'sqlite:///' + os.path.join(basedir, url[10:])
    return url


class Config:
    """Cấu hình cơ sở áp dụng cho mọi môi trường"""
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'fallback-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024

    UPLOAD_FOLDER = os.path.join(DATA_DIR, 'uploads')
    TRASH_FOLDER = os.path.join(DATA_DIR, 'deleted_assets')
    DATABASE_DIR = os.path.join(DATA_DIR, 'database')

class DevelopmentConfig(Config):
    """Cấu hình cho môi trường lập trình/kiểm thử (Dùng SQLite mặc định)"""
    DEBUG = True
    # Nếu không tìm thấy biến DATABASE_URL, tự động dùng SQLite an toàn trong thư mục instance
    SQLALCHEMY_DATABASE_URI = resolve_db_url(os.environ.get('DATABASE_URL')) or (
        'sqlite:///' + os.path.join(Config.DATABASE_DIR, 'asset_management.db')
    )

class ProductionConfig(Config):
    """Cấu hình cho môi trường xưởng thực tế (Bắt buộc phải có biến môi trường)"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = resolve_db_url(os.environ.get('DATABASE_URL'))
    
    # Có thể cấu hình thêm các giới hạn kết nối (Connection Pooling) cho PostgreSQL/MySQL tại đây