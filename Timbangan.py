#!/usr/bin/env python3
"""
========================================================
  TIMBANGAN DIGITAL - Raspberry Pi 4
  Konversi dari ESP32 (C++) ke Raspberry Pi 4 (Python)
  
  FIXED: Kompatibel dengan library hx711 (tatobari/hx711)
         yang menggunakan API berbeda dari versi lain.
         
  Library yang digunakan:
    pip install hx711        → tatobari/hx711
    pip install RPLCD        → LCD I2C
    pip install RPi.GPIO     → GPIO control
    pip install requests     → HTTP ke Google Sheets
========================================================
"""

import RPi.GPIO as GPIO
import time
import requests
import statistics
from hx711 import HX711
from RPLCD.i2c import CharLCD

# ================= KONFIGURASI GOOGLE SCRIPT =================
GOOGLE_SCRIPT_ID = ""

# ================= KONFIGURASI PIN GPIO =================
HX_DOUT    = 17   # GPIO17 = Pin fisik 11
HX_SCK     = 27   # GPIO27 = Pin fisik 13
PIN_BUTTON = 22   # GPIO22 = Pin fisik 15

# ================= KONFIGURASI KALIBRASI =================
# Nilai ini adalah RATIO: raw_value / berat_gram
# Didapat dari hasil kalibrasi. Default dari ESP32 = 23.95
# Jalankan kalibrasi.py jika hasil tidak akurat.
CALIBRATION_FACTOR = 23.95

NOISE_THRESHOLD_KG = 0.1    # Berat < 0.1 Kg dianggap 0 (noise filter)
TARE_SAMPLES       = 15     # Jumlah sampel untuk tare
READ_SAMPLES       = 5      # Jumlah sampel per pembacaan berat

# ================= KONFIGURASI INTERVAL =================
INTERVAL_UPDATE  = 0.01   # 10ms  - update Load Cell (sama ESP32)
INTERVAL_DISPLAY = 0.5    # 500ms - refresh LCD (sama ESP32)

# ================= INISIALISASI LCD I2C =================
# Cek alamat I2C dengan: sudo i2cdetect -y 1
# Ganti address=0x27 ke address=0x3f jika LCD tidak muncul
lcd = CharLCD(
    i2c_expander='PCF8574',
    address=0x27,
    port=1,
    cols=16,
    rows=2,
    dotsize=8,
    charmap='A02',
    auto_linebreaks=True,
    backlight_enabled=True
)

# ================= VARIABEL GLOBAL HX711 =================
hx       = None
tare_val = 0.0   # Nilai offset tare

# ================= FUNGSI HX711 (tatobari API) =================
def hx711_setup():
    """
    Inisialisasi HX711 menggunakan API tatobari/hx711.
    API ini TIDAK memiliki set_reading_format / set_reference_unit.
    Semua kalibrasi dilakukan manual dengan raw value.
    """
    global hx, tare_val

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    hx = HX711(HX_DOUT, HX_SCK)

    # Reset & tare
    hx711_tare()
    print(f"HX711 siap. Tare offset = {tare_val:.1f}")

def hx711_read_raw_avg(n=5):
    """Baca rata-rata n sampel raw dari HX711."""
    vals = []
    for _ in range(n):
        raw = hx.get_raw_data_mean(1)
        if raw is not False and raw is not None:
            vals.append(raw)
        time.sleep(0.01)
    if not vals:
        return None
    # Buang outlier sederhana: median dari vals
    return statistics.median(vals)

def hx711_tare():
    """Set nilai tare (nol) dari rata-rata banyak sampel."""
    global tare_val
    print(f"  Mengambil {TARE_SAMPLES} sampel untuk tare...")
    raw = hx711_read_raw_avg(TARE_SAMPLES)
    if raw is not None:
        tare_val = raw
    else:
        tare_val = 0.0
        print("  PERINGATAN: Tare gagal, offset diset ke 0")

def hx711_get_kg():
    """
    Baca berat dalam Kg.
    Formula: (raw - tare_offset) / CALIBRATION_FACTOR / 1000
    """
    raw = hx711_read_raw_avg(READ_SAMPLES)
    if raw is None:
        return None
    gram = (raw - tare_val) / CALIBRATION_FACTOR
    kg   = gram / 1000.0
    if kg < NOISE_THRESHOLD_KG:
        kg = 0.0
    return kg

# ================= FUNGSI LCD =================
def lcd_clear_line(row):
    """Bersihkan satu baris LCD dengan spasi."""
    lcd.cursor_pos = (row, 0)
    lcd.write_string(' ' * 16)

def lcd_print(row, col, text):
    """Tulis teks ke posisi tertentu di LCD."""
    lcd.cursor_pos = (row, col)
    lcd.write_string(str(text)[:16 - col])

# ================= FUNGSI KIRIM KE GOOGLE SHEET =================
def kirim_ke_google_sheet(berat_kg):
    """Kirim data berat ke Google Sheets via HTTP GET ke Apps Script."""
    url = (
        f"https://script.google.com/macros/s/"
        f"{GOOGLE_SCRIPT_ID}/exec?berat={berat_kg:.2f}"
    )
    try:
        print(f"  URL: {url}")
        resp = requests.get(url, allow_redirects=True, timeout=10)
        print(f"  HTTP {resp.status_code}: {resp.text[:80]}")
        return True
    except requests.exceptions.Timeout:
        print("  ERROR: Timeout — cek koneksi internet")
        return False
    except requests.exceptions.ConnectionError:
        print("  ERROR: Tidak terhubung — cek WiFi/LAN")
        return False
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

# ================= PROGRAM UTAMA =================
def main():
    global hx

    print("=" * 40)
    print("  TIMBANGAN DIGITAL - Raspberry Pi 4")
    print("=" * 40)

    # ── Tampilan awal LCD ──
    lcd.clear()
    lcd_print(0, 0, "TIMBANGAN DIGITAL")
    lcd_print(1, 0, " MENGINISIALISASI")
    time.sleep(1)

    # ── Setup GPIO ──
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(PIN_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    print("GPIO dikonfigurasi.")

    # ── Setup HX711 ──
    lcd.clear()
    lcd_print(0, 0, "INIT LOAD CELL..")
    lcd_print(1, 0, "JANGAN TARUH BENDA")
    print("Inisialisasi HX711...")
    print("PENTING: Jangan ada benda di atas load cell!")
    hx711_setup()

    # ── Tampilan siap ──
    lcd.clear()
    lcd_print(0, 0, "SISTEM SIAP!")
    lcd_print(1, 0, "TOMBOL=KIRIM DATA")
    print("\nSistem siap! Tekan CTRL+C untuk keluar.\n")
    time.sleep(1.5)
    lcd.clear()

    # ── State variabel ──
    last_button_state = GPIO.HIGH
    kg            = 0.0
    time_update   = time.time()
    time_display  = time.time()

    try:
        while True:
            now = time.time()

            # ── BAGIAN 1: UPDATE BERAT SETIAP 10ms ──
            if now - time_update >= INTERVAL_UPDATE:
                time_update = now
                hasil = hx711_get_kg()
                if hasil is not None:
                    kg = hasil

            # ── BAGIAN 2: REFRESH LCD SETIAP 500ms ──
            if now - time_display >= INTERVAL_DISPLAY:
                time_display = now
                lcd_print(0, 0, f"BERAT:{kg:7.2f} KG  ")

            # ── BAGIAN 3: CEK TOMBOL ──
            button_state = GPIO.input(PIN_BUTTON)

            # Deteksi tekan: transisi HIGH → LOW
            if button_state == GPIO.LOW and last_button_state == GPIO.HIGH:
                print(f"\nTombol ditekan! Berat = {kg:.2f} Kg")

                lcd_clear_line(1)
                lcd_print(1, 0, "MENGIRIM DATA...")

                sukses = kirim_ke_google_sheet(kg)

                lcd_clear_line(1)
                if sukses:
                    lcd_print(1, 0, "DATA TERKIRIM!  ")
                    print("✓ Berhasil terkirim ke Google Sheets!")
                else:
                    lcd_print(1, 0, "GAGAL KIRIM!    ")
                    print("✗ Gagal kirim. Cek koneksi internet.")

                time.sleep(1)
                lcd_clear_line(1)

            last_button_state = button_state
            time.sleep(0.05)   # Debounce ~50ms (sama dengan ESP32)

    except KeyboardInterrupt:
        print("\n\nProgram dihentikan.")
    finally:
        lcd.clear()
        lcd_print(0, 0, "SISTEM BERHENTI")
        time.sleep(1)
        lcd.close(clear=True)
        GPIO.cleanup()
        hx.power_down()
        print("Selesai.")

if __name__ == "__main__":
    main()
