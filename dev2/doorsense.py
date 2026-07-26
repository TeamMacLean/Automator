# SPDX-License-Identifier: MIT
# Copyright (c) 2025–2026 Rohan R

# doorsense.py
import atexit
try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None  # type: ignore[assignment]

IR_PIN = 26

def init_door_sensor():
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(IR_PIN, GPIO.IN)
        print("Door sensor initialized (GPIO 26)")
    except RuntimeError:
        GPIO.cleanup(IR_PIN)
        raise

def door_state():
    """Return True if door is OPEN, False if CLOSED."""
    return GPIO.input(IR_PIN) == GPIO.HIGH

def cleanup_door():
    GPIO.cleanup(IR_PIN)
    print("Door sensor GPIO cleaned up")

atexit.register(cleanup_door)
