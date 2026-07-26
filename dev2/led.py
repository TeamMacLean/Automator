# SPDX-License-Identifier: MIT
# Copyright (c) 2025–2026 Rohan R

# led.py
import atexit
try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None  # type: ignore[assignment]
import threading

RELAY_PIN = 23
PULSE_PIN = 4
PULSE_TIME = 0.1   # 100 ms pulse time for relay trigger

if GPIO is not None:
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RELAY_PIN, GPIO.OUT)
        GPIO.setup(PULSE_PIN, GPIO.OUT)
        GPIO.output(RELAY_PIN, GPIO.LOW)
        GPIO.output(PULSE_PIN, GPIO.LOW)
    except RuntimeError:
        GPIO.cleanup([RELAY_PIN, PULSE_PIN])
        raise

_pulse_state_lock = threading.Lock()
_off_pulse_armed = False

def _pulse():
    GPIO.output(PULSE_PIN, GPIO.HIGH)
    import time
    time.sleep(PULSE_TIME)
    GPIO.output(PULSE_PIN, GPIO.LOW)

def turn_on_led():
    global _off_pulse_armed
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    _pulse()
    with _pulse_state_lock:
        _off_pulse_armed = True
    print("LED ON + pulse")

def turn_off_led():
    global _off_pulse_armed
    GPIO.output(RELAY_PIN, GPIO.LOW)
    with _pulse_state_lock:
        armed = _off_pulse_armed
        _off_pulse_armed = False
    if armed:
        _pulse()
        print("LED OFF + pulse")
    else:
        print("LED OFF (pulse skipped: no prior LED ON pulse)")

def turn_on_led_no_pulse():
    global _off_pulse_armed
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    with _pulse_state_lock:
        _off_pulse_armed = False
    print("LED ON (no pulse)")

def turn_off_led_no_pulse():
    global _off_pulse_armed
    GPIO.output(RELAY_PIN, GPIO.LOW)
    with _pulse_state_lock:
        _off_pulse_armed = False
    print("LED OFF (no pulse)")

def send_pulse():
    _pulse()
    print("Pulse sent")

def cleanup_led():
    global _off_pulse_armed
    GPIO.output(RELAY_PIN, GPIO.LOW)
    with _pulse_state_lock:
        _off_pulse_armed = False
    GPIO.cleanup([RELAY_PIN, PULSE_PIN])
    print("LED GPIO + pulse pin cleaned up")

atexit.register(cleanup_led)
