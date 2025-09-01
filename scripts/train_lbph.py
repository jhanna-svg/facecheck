import os, sys, json
import cv2
import numpy as np

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FACES_DIR = os.path.join(BASE, "data", "faces")
MODELS_DIR = os.path.join(BASE, "data", "models")
os.makedirs(MODELS_DIR, exist_ok=True)

MODEL_PATH = os.path.join(MODELS_DIR, "lbph.xml")
LABELS_PATH = os.path.join(MODELS_DIR, "labels.json")

# Haar cascade for detecting faces
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

images, labels = [], []
label_map = {}
next_id = 0
total_images = 0

if not os.path.isdir(FACES_DIR):
    print("Error: faces directory not found:", FACES_DIR)
    sys.exit(1)

for person in sorted(os.listdir(FACES_DIR)):
    person_dir = os.path.join(FACES_DIR, person)
    if not os.path.isdir(person_dir):
        continue
    if person not in label_map:
        label_map[person] = next_id
        next_id += 1
    label_id = label_map[person]

    for fname in os.listdir(person_dir):
        if not fname.lower().endswith((".jpg", ".png", ".jpeg")):
            continue
        img_path = os.path.join(person_dir, fname)
        img = cv2.imread(img_path)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.2, 5)
        if len(faces) > 0:
            x,y,w,h = faces[0]
            roi = gray[y:y+h, x:x+w]
        else:
            roi = gray
        roi = cv2.resize(roi, (200,200))
        images.append(roi)
        labels.append(label_id)
        total_images += 1

if not images:
    print("No images found in data/faces/. Please register faces first.")
    sys.exit(1)

try:
    recognizer = cv2.face.LBPHFaceRecognizer_create()
except:
    print("ERROR: cv2.face not available. Install opencv-contrib-python inside your venv.")
    sys.exit(1)

print(f"Training on {total_images} images across {len(label_map)} students...")
recognizer.train(images, np.array(labels))
recognizer.write(MODEL_PATH)

with open(LABELS_PATH, "w") as f:
    json.dump({v:k for k,v in label_map.items()}, f, indent=2)

print("Model saved to", MODEL_PATH)
print("Labels saved to", LABELS_PATH)
