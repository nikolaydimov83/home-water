import asyncio

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    _gpio_available = True
except (ImportError, RuntimeError):
    _gpio_available = False


class Relay:
    async def activate(self, pin: int, duration: int) -> None:
        if _gpio_available:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
            GPIO.output(pin, GPIO.LOW)
            await asyncio.sleep(duration)
            GPIO.output(pin, GPIO.HIGH)
        else:
            print(f"[MOCK] GPIO {pin}: ON for {duration}s")
            await asyncio.sleep(duration)
            print(f"[MOCK] GPIO {pin}: OFF")

    async def on(self, pin: int) -> None:
        if _gpio_available:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
            GPIO.output(pin, GPIO.LOW)
        else:
            print(f"[MOCK] GPIO {pin}: ON")

    async def off(self, pin: int) -> None:
        if _gpio_available:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
            GPIO.output(pin, GPIO.HIGH)
        else:
            print(f"[MOCK] GPIO {pin}: OFF")
