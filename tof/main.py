import time
import board
import busio
import adafruit_vl53l0x

# Setup I2C
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize VL53L0X
vl53 = adafruit_vl53l0x.VL53L0X(i2c)

print("TOF sensor reading distances (mm)")

while True:
    try:
        distance = vl53.range
        print(f"Distance: {distance} mm")
        time.sleep(0.1)
    except Exception as e:
        print("Error:", e)
