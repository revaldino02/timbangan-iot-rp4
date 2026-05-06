#!/bin/bash
# ============================================================
#  SETUP OTOMATIS - Timbangan Digital Raspberry Pi 4
#  Jalankan script ini sekali untuk install semua dependensi
# ============================================================

echo "=================================================="
echo "  SETUP TIMBANGAN DIGITAL - Raspberry Pi 4"
echo "=================================================="

# Update sistem
echo ""
echo "[1/6] Update sistem..."
sudo apt update && sudo apt upgrade -y

# Install dependensi sistem
echo ""
echo "[2/6] Install dependensi sistem..."
sudo apt install -y python3-pip python3-smbus i2c-tools git python3-dev

# Aktifkan I2C dan SPI di Raspberry Pi
echo ""
echo "[3/6] Mengaktifkan interface I2C..."
sudo raspi-config nonint do_i2c 0
echo "I2C diaktifkan."

# Install library Python
echo ""
echo "[4/6] Install library Python..."
pip3 install RPi.GPIO
pip3 install hx711
pip3 install RPLCD
pip3 install requests
echo "Library Python berhasil diinstall."

# Verifikasi I2C LCD terdeteksi
echo ""
echo "[5/6] Scan alamat I2C (pastikan LCD terhubung)..."
sudo i2cdetect -y 1

# Set permission eksekusi script utama
echo ""
echo "[6/6] Set permission file..."
chmod +x timbangan.py

echo ""
echo "=================================================="
echo "  SETUP SELESAI!"
echo ""
echo "  Cara menjalankan:"
echo "  python3 timbangan.py"
echo ""
echo "  Untuk auto-start saat boot:"
echo "  sudo nano /etc/rc.local"
echo "  Tambahkan: python3 /path/to/timbangan.py &"
echo "=================================================="
