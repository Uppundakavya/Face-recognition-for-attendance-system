from flask import Flask, render_template, Response, request, jsonify, send_file
import face_recognition
import cv2
import numpy as np
from datetime import date
import xlwt
from xlrd import open_workbook
from xlutils.copy import copy as xl_copy
from PIL import Image
import os

app = Flask(__name__)

# Paths for known faces
image_paths = {
    "charan":"E:\Attendance\images\charan.png",
    "jyoshna":"E:\Attendance\images\jyoshna.png",
    "kavya": "E:\Attendance\images\kavya.png",
    "mythri": "E:\Attendance\images\mythri.png",
    "tharun":"E:\Attendance\images\tharun.png",
}

known_face_encodings = []
known_face_names = []

# Load known face encodings
def load_images_and_encodings():
    for name, path in image_paths.items():
        try:
            image = Image.open(path).convert("RGB")
            image_array = np.array(image)
            encoding = face_recognition.face_encodings(image_array)
            if encoding:
                known_face_encodings.append(encoding[0])
                known_face_names.append(name)
        except Exception as e:
            print(f"Error loading image {name}: {e}")

load_images_and_encodings()

# Path for attendance workbook
workbook_path = "E:\\Attendance\\attendance.xls"
attendance_active = False

def log_attendance(name, subject_name):
    try:
        rb = open_workbook(workbook_path, formatting_info=True)
        wb = xl_copy(rb)
    except FileNotFoundError:
        wb = xlwt.Workbook()

    sheet_names = rb.sheet_names() if 'rb' in locals() else []
    
    if subject_name in sheet_names:
        counter = 1
        new_subject_name = f"{subject_name}_{counter}"
        while new_subject_name in sheet_names:
            counter += 1
            new_subject_name = f"{subject_name}_{counter}"
        subject_name = new_subject_name

    sheet1 = wb.add_sheet(subject_name)
    sheet1.write(0, 0, 'Name/Date')
    sheet1.write(0, 1, str(date.today()))
    row = len(sheet1.rows)
    sheet1.write(row, 0, name)
    sheet1.write(row, 1, "Present")
    wb.save(workbook_path)

@app.route('/')
def index():
    return render_template('index.html')

def generate_frames(subject_name):
    video_capture = cv2.VideoCapture(0)
    already_attendance_taken = []

    while attendance_active:
        ret, frame = video_capture.read()
        if not ret:
            break
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = small_frame[:, :, ::-1]

        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame)

        face_names = []
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            name = "Unknown"
            if True in matches:
                first_match_index = matches.index(True)
                name = known_face_names[first_match_index]

            face_names.append(name)

            if name not in already_attendance_taken and name != "Unknown":
                log_attendance(name, subject_name)
                already_attendance_taken.append(name)

        for (top, right, bottom, left), name in zip(face_locations, face_names):
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 1)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    video_capture.release()

@app.route('/start_attendance', methods=['GET'])
def start_attendance():
    global attendance_active
    subject_name = request.args.get('subject_name')
    attendance_active = True
    return Response(generate_frames(subject_name), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stop_attendance', methods=['POST'])
def stop_attendance():
    global attendance_active
    attendance_active = False
    return jsonify(success=True)

@app.route('/download_attendance', methods=['GET'])
def download_attendance():
    return send_file(workbook_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
