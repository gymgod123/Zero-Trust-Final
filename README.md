# 🛡️ Secure Remote Access Gateway (Zero Trust)

Một dự án mô phỏng kiến trúc mạng Zero Trust (ZTA), cung cấp giải pháp truy cập an toàn từ xa vào các dịch vụ nội bộ mà không cần mở cổng (Port Forwarding) trên Router/Firewall.

Hệ thống được thiết kế theo tư duy phòng thủ (Blue Team), kết hợp giữa xác thực cục bộ đa tầng và đường hầm mã hóa tàng hình.

## ✨ Tính năng cốt lõi

* **Xác thực bảo mật (Authentication):** Đăng nhập/Đăng ký sử dụng mã thông báo JWT (JSON Web Token).
* **Kiểm soát truy cập (RBAC):** Phân quyền chặt chẽ giữa `Admin` và `User`. Chỉ Admin mới có quyền xem danh sách, xóa tài khoản hoặc thăng cấp quyền.
* **Nhật ký kiểm toán (Audit Logs):** Ghi nhận mọi hoạt động (đăng nhập thành công/thất bại, cấp quyền, xóa user) theo thời gian thực để giám sát hệ thống.
* **Zero Trust Tunnel:** Tích hợp Cloudflare Tunnel (cloudflared) để ẩn hoàn toàn IP của máy chủ gốc khỏi Internet.
* **Containerization:** Triển khai độc lập, dễ dàng bằng Docker và Docker Compose.

## 🛠️ Công nghệ sử dụng

* **Backend:** Python, FastAPI, JWT (python-jose).
* **Database:** SQLite (Lưu trữ cục bộ).
* **Frontend:** HTML5, CSS3, JavaScript (Fetch API), SweetAlert2.
* **Deployment & Security:** Docker, Cloudflare Zero Trust.

## 🚀 Hướng dẫn khởi chạy (Bằng Docker)

1. Clone kho lưu trữ này về máy:
   ```bash
   git clone [https://github.com/your-username/zero-trust-gateway.git](https://github.com/your-username/zero-trust-gateway.git)
   cd zero-trust-gateway
2. Khởi động hệ thống:
    ```bash
    docker-compose up -d --build
