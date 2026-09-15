import cv2
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
import os
import collections
import threading
import time
import requests

# ── Base directory ─────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Alert sound ────────────────────────────────────────────
def play_alert():
    try:
        import winsound
        winsound.Beep(1000, 400)
    except Exception as e:
        print(f"Alert: {e}")

def play_shutdown_alert():
    try:
        import winsound
        for _ in range(3):
            winsound.Beep(500, 300)
            time.sleep(0.1)
    except Exception as e:
        print(f"Shutdown alert error: {e}")

# ── Load model ─────────────────────────────────────────────
print("Loading ShieldScan model...")
model = load_model(os.path.join(BASE_DIR, "shieldscan_model.h5"))
print("Model loaded!")

# ── Load DNN face detector ─────────────────────────────────
prototxt   = os.path.join(BASE_DIR, "deploy.prototxt")
caffemodel = os.path.join(BASE_DIR,
             "res10_300x300_ssd_iter_140000.caffemodel")
print("Loading face detector...")
net = cv2.dnn.readNet(prototxt, caffemodel)
print("Face detector loaded!")

# ── Smoothing ──────────────────────────────────────────────
SMOOTH_FRAMES = 8
label_buffers = collections.defaultdict(
    lambda: collections.deque(maxlen=SMOOTH_FRAMES)
)

# ── Session state ──────────────────────────────────────────
session_stats = {
    "mask_count"        : 0,
    "nomask_count"      : 0,
    "total_faces"       : 0,
    "last_alert"        : 0,
    "nomask_start_time" : None,
    "shutdown"          : False,
    "shutdown_reason"   : "",
    "countdown"         : 60
}

ALERT_COOLDOWN   = 3
LOG_INTERVAL     = 30
SHUTDOWN_SECONDS = 60
FACE_TIMEOUT     = 1.5
frame_counter    = 0
_face_id_counter = 0
_active_face_ids = {}

# ──────────────────────────────────────────────────────────
#  FACE DETECTION
# ──────────────────────────────────────────────────────────

def get_face_regions(frame):
    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(
        cv2.resize(frame, (300, 300)),
        1.0,
        (300, 300),
        (104.0, 177.0, 123.0)
    )
    net.setInput(blob)
    detections = net.forward()

    faces = []
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence < 0.55:
            continue

        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
        x1, y1, x2, y2 = box.astype("int")
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)

        bw = x2 - x1
        bh = y2 - y1

        if bw < 60 or bh < 60:
            continue

        aspect = bw / float(bh)
        if aspect < 0.5 or aspect > 1.8:
            continue

        area_ratio = (bw * bh) / float(w * h)
        if area_ratio < 0.005 or area_ratio > 0.85:
            continue

        faces.append((x1, y1, x2, y2, float(confidence)))

    return faces

# ──────────────────────────────────────────────────────────
#  MASK PREDICTION
# ──────────────────────────────────────────────────────────

def predict_mask(face_img):
    try:
        face_img = cv2.resize(face_img, (224, 224))
        face_img = img_to_array(face_img)
        face_img = preprocess_input(face_img)
        face_img = np.expand_dims(face_img, axis=0)
        preds    = model.predict(face_img, verbose=0)[0]
        return preds
    except Exception as e:
        print(f"Prediction error: {e}")
        return np.array([1.0, 0.0])

# ──────────────────────────────────────────────────────────
#  SMOOTHING & FACE TRACKING
# ──────────────────────────────────────────────────────────

def smooth_prediction(face_id, preds):
    label_buffers[face_id].append(preds)
    return np.mean(label_buffers[face_id], axis=0)

def match_face_id(cx, cy, now):
    global _face_id_counter
    best_id   = None
    best_dist = 100

    for fid, (fx, fy, ft) in _active_face_ids.items():
        dist = np.sqrt((cx - fx)**2 + (cy - fy)**2)
        if dist < best_dist:
            best_dist = dist
            best_id   = fid

    if best_id is None:
        best_id = _face_id_counter
        _face_id_counter += 1

    _active_face_ids[best_id] = (cx, cy, now)
    return best_id

# ──────────────────────────────────────────────────────────
#  DATABASE LOGGING
# ──────────────────────────────────────────────────────────

def log_to_database(mask_status, confidence, user_id):
    try:
        requests.post(
            "http://127.0.0.1:5000/log_detection",
            data={
                "mask_status" : mask_status,
                "confidence"  : confidence,
                "location"    : "Main Entrance",
                "user_id"     : user_id
            },
            timeout=1
        )
    except Exception:
        pass

# ──────────────────────────────────────────────────────────
#  DRAWING
# ──────────────────────────────────────────────────────────

def draw_label(frame, x1, y1, x2, y2, label, confidence, color):
    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
    cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    label_text  = f"{label}: {confidence:.1f}%"
    font        = cv2.FONT_HERSHEY_SIMPLEX
    font_scale  = 0.65
    thickness   = 2
    (tw, th), _ = cv2.getTextSize(
        label_text, font, font_scale, thickness
    )

    lx1 = max(0, x1)
    ly1 = max(0, y1 - th - 14)
    lx2 = min(frame.shape[1], x1 + tw + 10)
    ly2 = y1

    cv2.rectangle(frame, (lx1, ly1), (lx2, ly2), color, -1)
    cv2.putText(
        frame, label_text, (lx1 + 5, ly2 - 8),
        font, font_scale, (255, 255, 255), thickness
    )

def draw_hud(frame, num_faces):
    h, w        = frame.shape[:2]
    hud_overlay = frame.copy()
    cv2.rectangle(hud_overlay, (0, 0), (w, 44), (0, 0, 0), -1)
    cv2.addWeighted(hud_overlay, 0.55, frame, 0.45, 0, frame)
    cv2.putText(
        frame,
        f"ShieldScan  |  "
        f"Faces: {num_faces}  |  "
        f"Mask: {session_stats['mask_count']}  |  "
        f"No Mask: {session_stats['nomask_count']}  |  "
        f"Total: {session_stats['total_faces']}",
        (10, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.56, (255, 255, 255), 1
    )

def draw_nomask_border(frame):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 239), 4)
    cv2.putText(
        frame,
        "WARNING: No Mask Detected!",
        (10, h - 12),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65, (0, 0, 239), 2
    )

def draw_countdown(frame, seconds_left):
    h, w    = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h-80), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    if seconds_left <= 10:
        color = (0, 0, 239)
    elif seconds_left <= 30:
        color = (0, 140, 255)
    else:
        color = (0, 200, 255)

    cv2.putText(
        frame,
        f"Shutting down in {seconds_left}s — please wear a mask!",
        (10, h - 48),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62, color, 2
    )

    total = w - 20
    fill  = int(total * (seconds_left / SHUTDOWN_SECONDS))
    cv2.rectangle(frame, (10, h-22), (10+total, h-10),
                  (60, 60, 60), -1)
    cv2.rectangle(frame, (10, h-22), (10+fill, h-10),
                  color, -1)

def draw_shutdown_screen(frame):
    h, w    = frame.shape[:2]
    overlay = np.zeros_like(frame)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    lines  = [
        "CAMERA SHUTDOWN",
        "No mask detected for 60 seconds.",
        "Please wear a mask and restart."
    ]
    ys     = [h//2 - 50, h//2, h//2 + 40]
    sizes  = [1.2, 0.7, 0.65]
    colors = [(0,0,239), (255,255,255), (200,200,200)]

    for line, y, size, color in zip(lines, ys, sizes, colors):
        (tw, _), _ = cv2.getTextSize(
            line, cv2.FONT_HERSHEY_SIMPLEX, size, 2
        )
        x = (w - tw) // 2
        cv2.putText(
            frame, line, (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            size, color, 2
        )

# ──────────────────────────────────────────────────────────
#  SHUTDOWN TIMER
# ──────────────────────────────────────────────────────────

def check_shutdown_timer(no_mask_found):
    now = time.time()

    if no_mask_found:
        if session_stats["nomask_start_time"] is None:
            session_stats["nomask_start_time"] = now
            print("No mask timer started...")

        elapsed   = now - session_stats["nomask_start_time"]
        remaining = max(0, int(SHUTDOWN_SECONDS - elapsed))
        session_stats["countdown"] = remaining

        if remaining <= 0 and not session_stats["shutdown"]:
            session_stats["shutdown"]        = True
            session_stats["shutdown_reason"] = \
                "No mask for 60 seconds"
            print("Camera shutdown triggered!")
            threading.Thread(
                target = play_shutdown_alert,
                daemon = True
            ).start()
    else:
        if session_stats["nomask_start_time"] is not None:
            print("Mask detected — timer reset.")
        session_stats["nomask_start_time"] = None
        session_stats["countdown"]         = SHUTDOWN_SECONDS

# ──────────────────────────────────────────────────────────
#  MAIN DETECT FRAME
# ──────────────────────────────────────────────────────────

def detect_frame(frame, user_id=1):
    global frame_counter, _active_face_ids

    frame_counter += 1

    if session_stats["shutdown"]:
        draw_shutdown_screen(frame)
        return frame

    faces         = get_face_regions(frame)
    no_mask_found = False
    now           = time.time()

    for (x1, y1, x2, y2, face_conf) in faces:
        cx      = (x1 + x2) // 2
        cy      = (y1 + y2) // 2
        face_id = match_face_id(cx, cy, now)

        face_roi = frame[y1:y2, x1:x2]
        if face_roi.size == 0:
            continue

        preds       = predict_mask(face_roi)
        avg_preds   = smooth_prediction(face_id, preds)
        label_index = np.argmax(avg_preds)
        confidence  = avg_preds[label_index] * 100

        if confidence < 70.0:
            label = "Checking..."
            color = (200, 200, 0)
        elif label_index == 0:
            label = "Mask"
            color = (34, 197, 94)
            if frame_counter % LOG_INTERVAL == 0:
                session_stats["mask_count"]  += 1
                session_stats["total_faces"] += 1
                threading.Thread(
                    target = log_to_database,
                    args   = ("Mask", confidence, user_id),
                    daemon = True
                ).start()
        else:
            label         = "No Mask"
            color         = (0, 0, 239)
            no_mask_found = True
            if frame_counter % LOG_INTERVAL == 0:
                session_stats["nomask_count"] += 1
                session_stats["total_faces"]  += 1
                threading.Thread(
                    target = log_to_database,
                    args   = ("No Mask", confidence, user_id),
                    daemon = True
                ).start()

        draw_label(frame, x1, y1, x2, y2,
                   label, confidence, color)

    _active_face_ids = {
        fid: (fx, fy, ft)
        for fid, (fx, fy, ft) in _active_face_ids.items()
        if now - ft < FACE_TIMEOUT
    }

    check_shutdown_timer(no_mask_found)

    if no_mask_found:
        t = time.time()
        if t - session_stats["last_alert"] > ALERT_COOLDOWN:
            session_stats["last_alert"] = t
            threading.Thread(
                target = play_alert,
                daemon = True
            ).start()
        draw_nomask_border(frame)
        draw_countdown(frame, session_stats["countdown"])

    draw_hud(frame, len(faces))
    return frame

# ──────────────────────────────────────────────────────────
#  VIDEO STREAM
# ──────────────────────────────────────────────────────────

def generate_frames(user_id=1):
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS,          30)

    if not cap.isOpened():
        print("Error: Could not open webcam (serverless/headless host).")
        img = np.zeros((480, 640, 3), np.uint8)
        cv2.putText(img, "Webcam capture requires local client environment.", (30, 220),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(img, "Serverless Vercel cloud instances do not have direct webcam hardware.", (15, 260),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1)
        ret, buffer = cv2.imencode(".jpg", img)
        if ret:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                buffer.tobytes() +
                b"\r\n"
            )
        return

    print("Webcam started!")

    while True:
        success, frame = cap.read()
        if not success:
            break

        frame = detect_frame(frame, user_id)

        ret, buffer = cv2.imencode(
            ".jpg", frame,
            [cv2.IMWRITE_JPEG_QUALITY, 85]
        )
        if not ret:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            buffer.tobytes() +
            b"\r\n"
        )

    cap.release()
    print("Webcam released.")

# ──────────────────────────────────────────────────────────
#  STATS HELPERS
# ──────────────────────────────────────────────────────────

def get_session_stats():
    return session_stats

def reset_session_stats():
    global _active_face_ids, _face_id_counter
    session_stats["mask_count"]        = 0
    session_stats["nomask_count"]      = 0
    session_stats["total_faces"]       = 0
    session_stats["last_alert"]        = 0
    session_stats["nomask_start_time"] = None
    session_stats["shutdown"]          = False
    session_stats["shutdown_reason"]   = ""
    session_stats["countdown"]         = 60
    label_buffers.clear()
    _active_face_ids  = {}
    _face_id_counter  = 0
    print("Session fully reset.")