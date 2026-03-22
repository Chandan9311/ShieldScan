# ShieldScan — Real-time Face Mask Detection System

![Python](https://img.shields.io/badge/Python-3.11-blue)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.x-orange)
![Flask](https://img.shields.io/badge/Flask-3.x-green)
![Accuracy](https://img.shields.io/badge/Accuracy-99.1%25-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

A production-ready AI-powered face mask detection web application
built with Python, TensorFlow, OpenCV, and Flask. Designed for
real-world healthcare deployment with role-based access control,
automatic email alerts, Excel export, and camera auto-shutdown.

---

## Demo

> Login → Dashboard → Start Camera → Real-time Detection

- **Green box** — Mask detected
- **Red box** — No mask detected
- **Yellow box** — Checking (low confidence)
- **Countdown + auto shutdown** — Camera turns off after 60s of no mask

---

## Features

### Detection
- Real-time face mask detection via webcam
- DNN-based face detector (ResNet SSD) — highly accurate
- MobileNetV2 CNN classifier — 99.1% accuracy
- Multiple face detection simultaneously
- 8-frame prediction smoothing — stable labels
- Confidence threshold — no guessing below 70%
- Auto camera shutdown after 60 seconds of no mask
- Alert beep sound on no mask detection

### Web Application
- Secure login and registration system
- Role-based access — Admin and User accounts
- Admin dashboard with full system statistics
- User dashboard with personal detection stats
- Live session timer and detection counters
- Professional responsive UI

### Admin Features
- View all registered users, login history, visitor logs
- Camera shutdown log — tracks non-compliant users
- Manage users — activate, deactivate, promote, delete
- Export all records to formatted Excel (.xlsx) file
- Email alerts on no mask detection
- Email alerts on camera shutdown with user details
- Configure alert recipient from settings page

### User Features
- View own detection logs and login history
- Cannot access other users data or admin features
- Simple clean dashboard focused on detection

### Database
- SQLite database with 4 tables
- Users — registration records
- Login records — login history with IP address
- Visitor logs — every detection with confidence and location
- Shutdown logs — camera shutdown events per user

---

## Tech Stack

| Category | Technology |
|---|---|
| Language | Python 3.11 |
| Deep learning | TensorFlow 2.x + Keras |
| Base model | MobileNetV2 (ImageNet pretrained) |
| Face detector | OpenCV DNN (ResNet SSD) |
| Web framework | Flask 3.x |
| Database | SQLite + SQLAlchemy |
| Authentication | Flask-Login + Werkzeug bcrypt |
| Email | Flask-Mail + Gmail SMTP |
| Excel export | openpyxl |
| Frontend | HTML5 + CSS3 + JavaScript |
| Training platform | Google Colab (free T4 GPU) |

---

## Project Structure
```
ShieldScan/
├── app.py                              ← Flask web server + all routes
├── detect.py                           ← CNN detection engine
├── shieldscan_model.h5                 ← trained MobileNetV2 model
├── deploy.prototxt                     ← DNN face detector config
├── res10_300x300_ssd_iter_140000.caffemodel  ← DNN face detector weights
├── requirements.txt                    ← Python dependencies
├── README.md                           ← this file
├── templates/
│   ├── login.html                      ← login page
│   ├── register.html                   ← registration page
│   ├── admin_dashboard.html            ← admin dashboard
│   ├── user_dashboard.html             ← user dashboard
│   ├── detect.html                     ← live detection page
│   ├── records.html                    ← admin records page
│   ├── user_records.html               ← user records page
│   ├── manage_users.html               ← admin user management
│   └── email_settings.html             ← email configuration
└── static/
    └── style.css
```

---

## Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/YourUsername/ShieldScan.git
cd ShieldScan
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Download the trained model

The trained model file `shieldscan_model.h5` is too large for
GitHub. Download it from the link below and place it in the
root ShieldScan folder:

> https://drive.google.com/file/d/1EsusxViErjfupEbUPuVvdb3qMIS2oQwh/view?usp=drive_link
> Google Drive link

### 4. Download face detector files

Download these two files and place them in the root folder:
```bash
curl -o deploy.prototxt "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"

curl -L -o res10_300x300_ssd_iter_140000.caffemodel "https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"
```

### 5. Configure email alerts (optional)

Open `app.py` and update these lines with your Gmail credentials:
```python
app.config["MAIL_USERNAME"]       = "your_gmail@gmail.com"
app.config["MAIL_PASSWORD"]       = "your_16_char_app_password"
app.config["MAIL_DEFAULT_SENDER"] = "your_gmail@gmail.com"
ALERT_EMAIL_RECIPIENT             = "recipient@gmail.com"
```

To get a Gmail app password:
1. Go to myaccount.google.com
2. Security → 2-Step Verification → App Passwords
3. Generate a password for Mail + Windows Computer

### 6. Run the application
```bash
python app.py
```

Open your browser and go to: `http://127.0.0.1:5000`

---

## Default Admin Account

When the server starts for the first time a default admin
account is created automatically:
```
Email    : admin@shieldscan.com
Password : admin123
```

**Change this password after first login.**

---

## Model Training

The model was trained on Google Colab using a free T4 GPU.

- Dataset: Face Mask Detection 12K Images (Kaggle)
- Base model: MobileNetV2 pretrained on ImageNet
- Custom head: AveragePooling → Dense(128) → Dropout(0.5) → Softmax(2)
- Training: 20 epochs, Adam optimizer, lr=1e-4
- Result: 99.1% validation accuracy

To retrain the model yourself open Google Colab and run
the training notebook included in the `/colab` folder.

---

## How It Works
```
Webcam frame
    ↓
DNN face detector (ResNet SSD)
    ↓
Face ROI extracted
    ↓
MobileNetV2 classifier
    ↓
8-frame smoothed prediction
    ↓
Label drawn on frame (Mask / No Mask / Checking)
    ↓
Result logged to database
    ↓
Alert email sent if no mask
    ↓
Camera shuts down after 60s of no mask
    ↓
Shutdown logged + admin notified by email
```

---

## Screenshots

> Add screenshots of your login page, dashboard, and
> live detection here after uploading to GitHub.

---

## Use Cases in Healthcare

- Hospital entrance monitoring
- ICU and ward access control
- Operating room compliance verification
- Pharmacy and OPD waiting area monitoring
- Elderly care and nursing home staff compliance
- Compliance analytics and reporting for health authorities

---

## Future Improvements

- Multi-camera support for full floor coverage
- Mobile app integration
- Real-time analytics dashboard with charts
- Face recognition to identify specific individuals
- Integration with hospital management systems
- Cloud deployment for remote monitoring

---

## License

This project is licensed under the MIT License.

---

## Acknowledgements

- MobileNetV2 — Google Research
- Face Mask Dataset — Kaggle (Ashish Jangra)
- OpenCV DNN Face Detector — OpenCV community
- Built with TensorFlow, Flask, and OpenCV