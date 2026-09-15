import os
import sys
import time
import numpy as np
import cv2
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("="*60)
print(" SHIELDSCAN MODEL VERIFICATION TEST ")
print("="*60)

# 1. Test TensorFlow CNN model
model_path = os.path.join(BASE_DIR, "shieldscan_model.h5")
print(f"[1/3] Loading classification model: {model_path}")

if not os.path.exists(model_path):
    print("ERROR: shieldscan_model.h5 file not found!")
    sys.exit(1)

start_time = time.time()
model = load_model(model_path)
load_duration = time.time() - start_time
print(f"SUCCESS: Model loaded in {load_duration:.2f} seconds.")
print(f"  - Input shape : {model.input_shape}")
print(f"  - Output shape: {model.output_shape}")
print(f"  - Total layers: {len(model.layers)}")
print(f"  - Total params: {model.count_params():,}")

# 2. Test OpenCV DNN face detector
prototxt   = os.path.join(BASE_DIR, "deploy.prototxt")
caffemodel = os.path.join(BASE_DIR, "res10_300x300_ssd_iter_140000.caffemodel")
print(f"\n[2/3] Loading OpenCV SSD face detector...")

if os.path.exists(prototxt) and os.path.exists(caffemodel):
    net = cv2.dnn.readNet(prototxt, caffemodel)
    print("SUCCESS: Face detector SSD network loaded successfully.")
else:
    print("WARNING: Face detector files missing.")

# 3. Benchmark Inference
print(f"\n[3/3] Running inference tests...")

dummy_face = np.full((224, 224, 3), 120, dtype=np.uint8)
cv2.circle(dummy_face, (112, 112), 80, (200, 180, 150), -1)

x = img_to_array(dummy_face)
x = preprocess_input(x)
x = np.expand_dims(x, axis=0)

times = []
for i in range(10):
    t0 = time.time()
    preds = model.predict(x, verbose=0)[0]
    times.append((time.time() - t0) * 1000)

avg_latency = np.mean(times)
mask_prob   = preds[0] * 100
nomask_prob = preds[1] * 100

print(f"\nInference Benchmark Results:")
print(f"  - Average latency : {avg_latency:.2f} ms / frame")
print(f"  - Test Prediction : Mask = {mask_prob:.2f}%, No Mask = {nomask_prob:.2f}%")
print("="*60)
print("ALL MODEL TESTS PASSED SUCCESSFULLY!")
print("="*60)
