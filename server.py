from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import FileResponse # Thư viện để trả về file HTML
from jose import JWTError, jwt
from datetime import datetime, timedelta
import sqlite3 
import os
import tempfile
# --- 1. CẤU HÌNH CƠ BẢN ---
app = FastAPI(title="API Server & Web UI (SQLite + Tắt Hashing)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "KHOA_BI_MAT_CUA_HE_THONG_KHONG_DUOC_DE_LO" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
EMERGENCY_ADMIN=["admin"]
def is_working_time():
    return False
# --- 2. KHỞI TẠO DATABASE SQLITE ---
# --- 2. KHỞI TẠO DATABASE SQLITE ---
DB_DIR = tempfile.gettempdir()
DB_FILE = os.path.join(DB_DIR, "users.db")
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Bảng Users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
    
    # BẢNG MỚI: Bảng Logs (Nhật ký hệ thống)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            outcome TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# HÀM BỔ SUNG: Ghi log tự động
def write_audit_log(username: str, action: str, outcome: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Lấy giờ hệ thống hiện tại
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO logs (timestamp, username, action, outcome) VALUES (?, ?, ?, ?)", 
                   (now, username, action, outcome))
    conn.commit()
    conn.close()

# --- 3. CÁC HÀM XỬ LÝ ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực thông tin",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
            
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT username, role FROM users WHERE username = ?", (username,))
        user_row = cursor.fetchone()
        conn.close()
        
        if user_row is None:
            raise credentials_exception
            
        return {"username": user_row[0], "role": user_row[1]}
    except JWTError:
        raise credentials_exception
def enforce_admin_time_access(current_user:dict):
    if current_user['role']!='admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Truy cập bị từ chối")
    if not is_working_time() and current_user["username"] not in EMERGENCY_ADMIN:
        write_audit_log(current_user['username'],"Truy cập ngoài giờ làm việc","403 access denied")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Admin truy cập ngoài giờ làm việc")
    if not is_working_time() and current_user["username"] in EMERGENCY_ADMIN:
        write_audit_log(current_user['username'],"Emergency login ngoài giờ làm việc",'200 access')

# --- 4. API ENDPOINTS CHÍNH (Xử lý dữ liệu ngầm - POST) ---

@app.post("/register", tags=["Authentication"])
async def register(username: str, password: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                       (username, password, 'user'))
        conn.commit()
        print(f"[DB LOG] Đã lưu user mới: {username}")
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại")
        
    conn.close()
    return {"msg": "Đăng ký thành công!"}

@app.post("/login", tags=["Authentication"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT password, role FROM users WHERE username = ?", (form_data.username,))
    user_row = cursor.fetchone()
    conn.close()
    
    if not user_row or form_data.password != user_row[0]:
        # Ghi log: Đăng nhập sai
        write_audit_log(form_data.username, "Cố gắng đăng nhập (Sai mật khẩu/Tài khoản)", "401 Failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai thông tin")
    role=user_row[1]
    if role=='admin' and not is_working_time():
        if form_data.username not in EMERGENCY_ADMIN:
            write_audit_log(form_data.username,'Đăng nhập admin ngoài giờ làm việc','403 Denied')
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail='Admin không đc đăng nhập ngoài giờ làm việc')
        else:
            write_audit_log(form_data.username,"Emergency login ngoài giờ làm việc",'200 Emergency Access')
    write_audit_log(form_data.username,"Đăng nhập thành công","200 Access")
    access_token=create_access_token(data={"sub":form_data.username,"role":role})
    return {"access_token":access_token,"token_type":"bearer"}
# --- API LẤY NHẬT KÝ CHO ADMIN ---
@app.get("/admin/logs", tags=["Admin Zone"])
async def get_audit_logs(current_user: dict = Depends(get_current_user)):
    enforce_admin_time_access(current_user)
    conn=sqlite3.connect(DB_FILE)
    cursor=conn.cursor()
    cursor.execute("SELECT timestamp,username,action,outcome FROM logs ORDER BY id DESC LIMIT 50")
    logs_list=[{'time':row[0],'user':row[1],'action':row[2],"outcome":row[3]}for row in cursor.fetchall()]
    conn.close()
    return {"logs":logs_list} 


# --- 5. API THEO PHÂN QUYỀN (Lấy dữ liệu - GET) ---
@app.get("/user/data", tags=["User Zone"])
async def read_user_data(current_user: dict = Depends(get_current_user)):
    return {"msg": f"Xin chào {current_user['username']}!", "role": current_user["role"]}

@app.get("/admin/data", tags=["Admin Zone"])
async def read_admin_data(current_user: dict = Depends(get_current_user)):
    enforce_admin_time_access(current_user)
    return {"msg": f"Kính chào Admin {current_user['username']}."}

@app.get("/admin/users", tags=["Admin Zone"])
async def get_all_users(current_user: dict = Depends(get_current_user)):
    # 1. Kiểm tra quyền Admin
    enforce_admin_time_access(current_user)
    conn=sqlite3.connect(DB_FILE)
    cursor=conn.cursor()
    cursor.execute("SELECT username,role FROM users")
    user_list=[]
    for row in cursor.fetchall():
        user_list.append({'username':row[0],'role':row[1]})
    conn.close()
    return{"users":user_list}

@app.delete("/admin/users/{target_user}", tags=["Admin Zone"])
async def delete_user(target_user: str, current_user: dict = Depends(get_current_user)):
    # 1. Kiểm tra xem người đang bấm xóa có phải là Admin không
    enforce_admin_time_access(current_user)
    if target_user=='admin':
        raise HTTPException(status_code=400,detail="Không thể xóa tài khoản root Admin")
    conn=sqlite3.connect(DB_FILE)
    cursor=conn.cursor()
    cursor.execute("DELETE FROM users WHERE username=?",(target_user,))
    conn.commit()
    conn.close()
    write_audit_log(current_user["username"],f"Đã xóa tài khoản {target_user}","200 ok")
    return {"msg":"Đã xóa thành công"}

@app.put("/admin/users/{target_user}/role", tags=["Admin Zone"])
async def update_user_role(target_user: str, new_role: str, current_user: dict = Depends(get_current_user)):
    # 1. Chỉ Admin mới được phép đổi quyền người khác
    enforce_admin_time_access(current_user)
    
    # 2. Bảo vệ tài khoản Root Admin (không cho phép tự giáng cấp hoặc bị người khác giáng cấp)
    if target_user == "admin":
        raise HTTPException(status_code=400, detail="Không thể thay đổi quyền của Root Admin!")
        
    if new_role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="Quyền không hợp lệ!")

    # 3. Cập nhật vào DB
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, target_user))
    conn.commit()
    conn.close()
    
    # 4. Ghi Audit Log tự động
    write_audit_log(current_user["username"], f"Cấp quyền {new_role.upper()} cho {target_user}", "200 OK")
    
    return {"msg": f"Đã cập nhật quyền thành {new_role}"}

# --- 6. PHỤC VỤ GIAO DIỆN HTML (Trình duyệt truy cập trực tiếp) ---

@app.get("/", tags=["Pages"])
@app.get("/login", tags=["Pages"])
@app.get("/login.html", tags=["Pages"])
async def show_login_page():
    return FileResponse("login.html")

@app.get("/register", tags=["Pages"])
@app.get("/register.html", tags=["Pages"])
async def show_register_page():
    return FileResponse("register.html")

# Chuẩn bị sẵn cổng cho 2 bạn kia ghép code vào ngày mai
@app.get("/user", tags=["Pages"])
@app.get("/user.html", tags=["Pages"])
async def show_user_page():
    return FileResponse("user.html")

@app.get("/admin", tags=["Pages"])
@app.get("/admin.html", tags=["Pages"])
async def show_admin_page():
    return FileResponse("admin.html")