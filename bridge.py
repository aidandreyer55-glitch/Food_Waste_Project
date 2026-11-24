from flask import Flask, request, render_template_string, jsonify
import serial
import threading
import time
import os


# Connect to Arduino over USB (Keep your working COM port here)
arduino = serial.Serial(port='COM4', baudrate=9600, timeout=1)
time.sleep(2)

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Flag that tells the phone when to snap a photo
take_photo_now = False


# Background thread that constantly listens to the Arduino
def listen_to_arduino():
    global take_photo_now
    while True:
        if arduino.in_waiting > 0:
            line = arduino.readline().decode('utf-8').strip()
            print("Arduino says:", line)
            if line == "TRIGGER_PHOTO":
                print("Trigger received! Telling phone to snap a photo...")
                take_photo_now = True
        time.sleep(0.05)


threading.Thread(target=listen_to_arduino, daemon=True).start()

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: sans-serif; text-align: center; padding: 20px; }
    video { width: 100%; max-width: 400px; border-radius: 8px; border: 2px solid #333; }
    button { padding: 12px 20px; font-size: 16px; margin-top: 10px; }
  </style>
</head>
<body>
  <h2>Remote Auto-Camera</h2>
  <p id="status">Tap "Start Camera" to arm remote trigger.</p>
  <video id="video" autoplay playsinline></video>
  <canvas id="canvas" style="display:none;"></canvas>
  <br>
  <button onclick="startCamera()">1. Start Camera</button>
  <button onclick="snapAndUpload()">Manual Test Snap</button>

  <script>
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const statusText = document.getElementById('status');

    // Ask phone for camera permission and show live preview
    async function startCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
          video: { facingMode: "environment" }, audio: false 
        });
        video.srcObject = stream;
        statusText.innerText = "Armed! Waiting for Arduino/PC trigger...";
        setInterval(checkForTrigger, 1000); // Check PC every 1 second
      } catch (err) {
        statusText.innerText = "Camera error: " + err;
      }
    }

    // Ask the Python server if the Arduino sent a trigger
    async function checkForTrigger() {
      const res = await fetch('/check_trigger');
      const data = await res.json();
      if (data.snap) {
        statusText.innerText = "Trigger received! Taking photo...";
        snapAndUpload();
      }
    }

    // Capture a frame from the video stream and upload it to Python
    function snapAndUpload() {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext('2d').drawImage(video, 0, 0);

      canvas.toBlob(async (blob) => {
        const formData = new FormData();
        formData.append('photo', blob, 'auto_photo.jpg');
        await fetch('/upload', { method: 'POST', body: formData });
        statusText.innerText = "Photo uploaded! Waiting for next trigger...";
      }, 'image/jpeg');
    }
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


# Route for the computer itself to manually trigger a photo anytime
@app.route("/trigger")
def manual_pc_trigger():
    global take_photo_now
    take_photo_now = True
    return "Phone camera triggered!"


# Phone polls this route every second
@app.route("/check_trigger")
def check_trigger():
    global take_photo_now
    if take_photo_now:
        take_photo_now = False  # Reset flag so it only snaps once per trigger
        return jsonify({"snap": True})
    return jsonify({"snap": False})


# Phone sends the captured image here
@app.route("/upload", methods=["POST"])
def Dupload():
    file = request.files.get("photo")
    if file:
        filename = f"auto_{int(time.time())}.jpg"
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)
        print(f"Saved automatic photo: {save_path}")
        arduino.write(b"PHOTO_SAVED\n")
        return "OK", 200
    return "No file", 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, ssl_context="adhoc")