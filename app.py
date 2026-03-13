import os
import uuid
from flask import Flask, request, jsonify, render_template, send_from_directory

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
AUDIO_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'audio')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'bmp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/convert', methods=['POST'])
def convert():
    try:
        import cv2
        import numpy as np
        import pytesseract
        from gtts import gTTS
        from PIL import Image

        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded.'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected.'}), 400

        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type. Please upload JPG, PNG, or BMP only.'}), 400

        file_id = str(uuid.uuid4())
        ext = file.filename.rsplit('.', 1)[1].lower()
        img_path = os.path.join(UPLOAD_FOLDER, f'{file_id}.{ext}')
        mp3_filename = f'{file_id}.mp3'
        mp3_path = os.path.join(AUDIO_FOLDER, mp3_filename)

        file.save(img_path)

        img = cv2.imread(img_path)
        if img is None:
            return jsonify({'success': False, 'error': 'Could not read image file.'}), 400

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.medianBlur(gray, 3)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        pil_image = Image.fromarray(thresh)

        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(pil_image, config=custom_config)
        text = text.strip()

        if not text:
            return jsonify({'success': False, 'error': 'No text detected in image. Try a clearer image.'}), 400

        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(mp3_path)

        os.remove(img_path)

        word_count = len(text.split())
        char_count = len(text)
        audio_url = f'/audio/{mp3_filename}'

        return jsonify({
            'success': True,
            'text': text,
            'audio_url': audio_url,
            'word_count': word_count,
            'char_count': char_count
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_FOLDER, filename)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
