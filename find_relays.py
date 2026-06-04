#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

#! 26 is the rightmost relay when you are seeing the relays from the green part

pins = [26, 20, 21]

for p in pins:
    GPIO.setup(p, GPIO.OUT, initial=GPIO.HIGH)

try:
    for p in pins:
        print(f'Testing GPIO {p}...')
        GPIO.output(p, GPIO.LOW)
        time.sleep(5)
        GPIO.output(p, GPIO.HIGH)
        time.sleep(0)
except KeyboardInterrupt:
    print("Stopped")
finally:
    GPIO.cleanup()
