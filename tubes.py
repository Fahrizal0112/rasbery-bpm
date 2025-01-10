from smbus2 import SMBus
import numpy as np
import time

# ADS1115 constants tetap sama
ADS1115_ADDRESS = 0x48
ADS1115_POINTER_CONVERSION = 0x00
ADS1115_POINTER_CONFIG = 0x01
ADS1115_CONFIG_OS_SINGLE = 0x8000
ADS1115_CONFIG_MUX_SINGLE_0 = 0x4000
ADS1115_CONFIG_PGA_4_096V = 0x0200
ADS1115_CONFIG_MODE_SINGLE = 0x0100
ADS1115_CONFIG_DR_128SPS = 0x0080
ADS1115_CONFIG_CMODE_TRAD = 0x0000
ADS1115_CONFIG_CQUE_NONE = 0x0003

# Setup I2C
bus = SMBus(1)

def read_adc():
    # Fungsi read_adc tetap sama
    config = (ADS1115_CONFIG_OS_SINGLE |
             ADS1115_CONFIG_MUX_SINGLE_0 |
             ADS1115_CONFIG_PGA_4_096V |
             ADS1115_CONFIG_MODE_SINGLE |
             ADS1115_CONFIG_DR_128SPS |
             ADS1115_CONFIG_CMODE_TRAD |
             ADS1115_CONFIG_CQUE_NONE)
    
    bus.write_i2c_block_data(ADS1115_ADDRESS, ADS1115_POINTER_CONFIG, [(config >> 8) & 0xFF, config & 0xFF])
    time.sleep(0.008)
    data = bus.read_i2c_block_data(ADS1115_ADDRESS, ADS1115_POINTER_CONVERSION, 2)
    value = (data[0] << 8) | data[1]
    
    if value < 0:
        value = 0
    
    return value

def is_signal_valid(data_buffer, min_amplitude=1000):
    """
    Memeriksa apakah sinyal valid berdasarkan amplitude dan variasi
    """
    if len(data_buffer) < 10:
        return False
    
    # Perketat pengecekan nilai minimum dan maksimum
    if min(data_buffer) < 100 or max(data_buffer) > 20000:  # Tambah batas maksimum
        return False
    
    amplitude = np.ptp(data_buffer)
    std_dev = np.std(data_buffer)
    
    # Perketat persyaratan validasi
    return (amplitude > min_amplitude and amplitude < 15000 and  # Tambah batas amplitude maksimum
            std_dev > 100 and std_dev < 5000 and  # Tambah batas std_dev
            1000 < max(data_buffer) < 20000)  # Perketat range nilai valid

def calculate_bpm(data_buffer, sampling_rate=50):
    if len(data_buffer) < sampling_rate:
        return None, 0, 0, 0
    
    # Validasi sinyal
    if not is_signal_valid(data_buffer):
        return None, 0, 0, np.ptp(data_buffer)
    
    # Konversi ke numpy array dan terapkan moving average
    data = np.array(data_buffer)
    window = 5
    moving_avg = np.convolve(data, np.ones(window)/window, mode='valid')
    data_detrended = data[window-1:] - moving_avg
    
    # Normalisasi
    normalized = (data_detrended - np.mean(data_detrended)) / np.std(data_detrended)
    
    # Deteksi peaks
    threshold = 0.2
    peaks = np.where(normalized > threshold)[0]
    
    # Filter peaks yang terlalu dekat
    min_distance = int(sampling_rate * 0.5)
    filtered_peaks = []
    last_peak = -min_distance
    
    for peak in peaks:
        if peak - last_peak >= min_distance:
            filtered_peaks.append(peak)
            last_peak = peak
    
    amplitude = np.ptp(data_detrended)
    
    if len(filtered_peaks) < 2:
        return None, len(filtered_peaks), threshold, amplitude
    
    intervals = np.diff(filtered_peaks)
    avg_interval = np.mean(intervals)
    bpm = 60 * sampling_rate / avg_interval
    
    # Validasi BPM
    if 40 <= bpm <= 200:
        return round(bpm), len(filtered_peaks), threshold, amplitude
    return None, len(filtered_peaks), threshold, amplitude

def get_heart_rate_status(bpm):
    if bpm is None:
        return "tidak terdeteksi"
    elif bpm < 60:
        return "rendah"
    elif bpm > 100:
        return "tinggi"
    else:
        return "normal"

def main():
    print("Starting Heart Rate Monitor...")
    print("Press Ctrl+C to exit")
    
    pulse_buffer = []
    sampling_rate = 50
    buffer_size = sampling_rate * 4
    last_valid_bpm = None
    min_value = float('inf')
    max_value = float('-inf')
    
    try:
        while True:
            value = read_adc()
            
            # Perketat validasi nilai sensor
            if value < 100 or value > 20000:  # Tambah batas maksimum
                pulse_buffer.clear()
                last_valid_bpm = None
                print(f"\rSensor terlepas | BPM: Tidak terdeteksi | Status: tidak terdeteksi", end="")
                time.sleep(1/sampling_rate)
                continue
                
            pulse_buffer.append(value)
            
            # Update min/max values
            min_value = min(min_value, value)
            max_value = max(max_value, value)
            
            if len(pulse_buffer) > buffer_size:
                pulse_buffer.pop(0)
            
            # Cek apakah sinyal valid
            signal_valid = is_signal_valid(pulse_buffer)
            
            # Hitung BPM hanya jika sinyal valid
            if signal_valid:
                bpm, num_peaks, threshold, amplitude = calculate_bpm(pulse_buffer)
                if bpm is not None:
                    last_valid_bpm = bpm
            else:
                bpm = None
                num_peaks = 0
                threshold = 0
                amplitude = np.ptp(pulse_buffer)
                last_valid_bpm = None
            
            status = get_heart_rate_status(last_valid_bpm)
            
            # Print status dengan indikator kontak sensor
            print(f"\rNilai: {value:5d} | "
                  f"Amp: {amplitude:5.0f} | "
                  f"Kontak: {'Ya' if signal_valid else 'Tidak'} | "
                  f"BPM: {last_valid_bpm if last_valid_bpm else 'Tidak terdeteksi':<4} | "
                  f"Status: {status}", end="")
            
            time.sleep(1/sampling_rate)
            
    except KeyboardInterrupt:
        print("\nProgram dihentikan oleh pengguna")
    finally:
        bus.close()

if __name__ == "__main__":
    main()


