from flask import Flask, render_template, jsonify
from tubes import read_adc, calculate_bpm, is_signal_valid, get_heart_rate_status
import time
import numpy as np

app = Flask(__name__)

# Variabel global untuk menyimpan data
pulse_buffer = []
sampling_rate = 50
buffer_size = sampling_rate * 4
last_valid_bpm = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_bpm')
def get_bpm():
    global pulse_buffer, last_valid_bpm
    
    value = read_adc()
    
    if value < 100 or value > 20000:
        pulse_buffer.clear()
        last_valid_bpm = None
        return jsonify({
            'value': value,
            'bpm': 'Tidak terdeteksi',
            'status': 'tidak terdeteksi',
            'kontak': 'Tidak'
        })
    
    pulse_buffer.append(value)
    if len(pulse_buffer) > buffer_size:
        pulse_buffer.pop(0)
    
    signal_valid = is_signal_valid(pulse_buffer)
    
    if signal_valid:
        bpm, num_peaks, threshold, amplitude = calculate_bpm(pulse_buffer)
        if bpm is not None:
            last_valid_bpm = bpm
    else:
        bpm = None
        amplitude = np.ptp(pulse_buffer) if pulse_buffer else 0
        last_valid_bpm = None
    
    status = get_heart_rate_status(last_valid_bpm)
    
    return jsonify({
        'value': value,
        'bpm': last_valid_bpm if last_valid_bpm else 'Tidak terdeteksi',
        'status': status,
        'kontak': 'Ya' if signal_valid else 'Tidak',
        'amplitude': round(amplitude) if 'amplitude' in locals() else 0
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
