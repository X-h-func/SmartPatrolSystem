# 智能巡更系统 (Smart Patrol System)

基于摄像头的智能巡更系统，支持图片上传、AI人物识别、缺勤自动检测、异常上报审批、周报/月报生成。

---

## 一、部署与运行

### 1. 环境要求

- Python 3.10+
- pip 包管理器
- 现代浏览器（Chrome / Edge / Firefox）

### 2. 安装依赖

```bash
cd SmartPatrolSystem
pip install -r requirements.txt
```

`requirements.txt` 包含：

| 依赖 | 用途 |
|------|------|
| flask | Web 框架 |
| flask-sqlalchemy | 数据库 ORM |
| flask-login | 用户登录认证 |
| werkzeug | 密码哈希 |
| Pillow | 图片处理 |
| opencv-python-headless | AI 人物检测（内置 HOG 方案） |

如需更高识别精度，可额外安装 YOLOv8（约 2GB 下载量）：

```bash
pip install ultralytics   # 可选，安装后自动切换高精度模式
```

### 3. 启动服务

```bash
python app.py
```

首次启动自动创建数据库并插入种子数据（6个用户、12个摄像头、示例异常记录）。

浏览器打开 **http://127.0.0.1:5000**。

### 4. 演示账号

| 角色 | 用户名 | 密码 | 说明 |
|------|--------|------|------|
| 系统管理员 | `admin` | `admin123` | 全部功能 |
| 物业主管 | `supervisor` | `sup123` | 审批、报表 |
| 巡更人员 A区 | `patrol1` | `patrol123` | 上传打卡 |
| 巡更人员 B区 | `patrol2` | `patrol123` | 上传打卡 |
| 巡更人员 C区 | `patrol3` | `patrol123` | 上传打卡 |
| 巡更人员 A区 | `patrol4` | `patrol123` | 上传打卡 |

### 5. 重置数据库

```bash
del instance\patrol.db    # Windows
rm instance/patrol.db     # macOS / Linux
```

重启 `python app.py` 即自动重建。

---

## 二、接入真实摄像头改进方案

当前系统通过手动上传图片模拟摄像头工作。如果接入真实摄像头，按以下四个阶段改造：

### 阶段一：RTSP 视频流接入（2-3周）

**改造点：** 用摄像头自动抓拍替代人工上传。

**技术方案：**
- 利用网络摄像头的 RTSP 协议拉取视频流
- 后端新增 `video_service.py`，使用 OpenCV `VideoCapture` 定时抓帧
- `cameras` 表增加 `rtsp_url` 字段存储每台摄像头的流地址
- 使用 APScheduler 定时任务，每 30 秒对所有正常摄像头抓取一帧进行人物检测

```python
# services/video_service.py 核心代码
import cv2

class CameraStreamManager:
    def __init__(self):
        self.streams = {}  # camera_id -> cv2.VideoCapture

    def connect_camera(self, camera_id, rtsp_url):
        cap = cv2.VideoCapture(rtsp_url)
        if cap.isOpened():
            self.streams[camera_id] = cap

    def capture_frame(self, camera_id):
        """从指定摄像头抓取一帧，返回图片路径"""
        cap = self.streams.get(camera_id)
        if cap is None:
            return None
        ret, frame = cap.read()
        if ret:
            path = f"static/captures/{camera_id}_{datetime.now():%Y%m%d_%H%M%S}.jpg"
            cv2.imwrite(path, frame)
            return path
        return None
```

**cameras 表新增字段：**

```sql
ALTER TABLE cameras ADD COLUMN rtsp_url VARCHAR(256);
-- 示例：rtsp://admin:password@192.168.1.101:554/stream1
```

### 阶段二：人脸识别自动匹配（3-4周）

**改造点：** 系统自动识别巡更人员身份，无需手动选择摄像头归属。

**技术方案：**
- 使用 `face_recognition` 库提取面部特征向量
- `users` 表增加 `face_encoding` 字段（BLOB，存储 128 维向量）
- 巡更人员注册时录入面部特征；摄像头抓拍后自动匹配身份
- 匹配成功 → 自动创建 `patrol_record`
- 匹配失败 → 记为"未识别"，记录到审核日志

```python
# services/face_service.py 核心逻辑
import face_recognition
import numpy as np

def recognize_patrol_person(image_path):
    img = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(img)

    for encoding in encodings:
        for user in User.query.filter_by(role='patrol').all():
            if user.face_encoding is None:
                continue
            known = np.frombuffer(user.face_encoding)
            if face_recognition.compare_faces([known], encoding)[0]:
                return user  # 匹配成功
    return None
```

### 阶段三：轨迹可视化与实时监控（2-3周）

**改造点：** 提供巡更轨迹地图和实时监控大屏。

**技术方案：**
- 在小区平面图上标注摄像头位置，Canvas/SVG 绘制移动轨迹线
- 按时间戳排序抓拍记录，连线形成巡更路径
- 使用 Flask-SocketIO（WebSocket）向前端推送实时数据
- 新增 `/monitor` 大屏页面：左侧实时画面 + 右侧统计面板

```
摄像头上报时间线：
  Cam-A01(09:00) → Cam-A02(09:08) → Cam-A03(09:15) → Cam-A04(09:22)
  ─────────────────────────────────────────────────────────────→ 轨迹线
```

### 阶段四：视频行为分析（4-6周）

**改造点：** 从"人数统计"升级到"行为分析"。

**技术方案：**
- **异常行为检测**：YOLO + DeepSORT 目标跟踪，检测深夜逗留、快速奔跑
- **区域入侵检测**：设置电子围栏，越界自动告警
- **遗留物检测**：背景建模（ Background Subtraction），检测公共区域遗留物品
- **人流密度统计**：出入口实时人流量统计，超阈值告警

### 架构升级建议

| 组件 | 当前方案 | 生产环境建议 |
|------|----------|-------------|
| Web 服务器 | Flask 内置服务器 | Gunicorn + Nginx |
| 数据库 | SQLite | PostgreSQL / MySQL |
| 任务队列 | 同步处理 | Celery + Redis（图片识别异步化） |
| 文件存储 | 本地 static/uploads/ | MinIO / 阿里云 OSS |
| 视频流 | 无 | FFmpeg + 流媒体网关 |
| 前端 | Jinja2 模板渲染 | Vue 3 / React + RESTful API |
| 部署 | `python app.py` | Docker Compose 容器化 |

### 改造实施路线

| 阶段 | 周期 | 核心内容 |
|------|------|----------|
| 一 | 2-3周 | RTSP 拉流、自动抓拍、定时检测 |
| 二 | 3-4周 | 人脸识别、身份自动匹配、面部特征注册 |
| 三 | 2-3周 | 轨迹地图、实时大屏、WebSocket 推送 |
| 四 | 4-6周 | 行为分析、入侵检测、人流统计 |
| 架构 | 并行 | PG 迁移、Celery 异步、Docker 部署 |
