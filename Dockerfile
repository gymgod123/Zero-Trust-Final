# Dùng bản Python 3.10 siêu nhẹ
FROM python:3.10-slim

# Đặt thư mục làm việc bên trong Container
WORKDIR /app

# Copy file thư viện vào trước và cài đặt (Tối ưu cache của Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code (server.py, các file .html, users.db) vào container
COPY . .

# Mở cổng 8000 để giao tiếp
EXPOSE 8000

# Lệnh khởi động Server khi Container chạy
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]