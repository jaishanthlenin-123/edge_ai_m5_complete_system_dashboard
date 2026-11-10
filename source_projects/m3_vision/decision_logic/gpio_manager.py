"""
Raspberry Pi 5 GPIO Manager for 3-LED PPE Indicator System
Controls 3 physical LEDs connected to Raspberry Pi 5 40-pin header:
- GREEN LED:  GPIO 27 (Pin 13) -> Turns ON when HELMET ONLY detected
- YELLOW LED: GPIO 17 (Pin 11) -> Turns ON when GLOVES ONLY detected
- RED LED:    GPIO 22 (Pin 15) -> BLINKS when BOTH HELMET & GLOVES detected (Green & Yellow OFF)
- GROUND:     Physical Pin 14 (GND, also Pin 9 or Pin 6)

Authoritative Truth Table:
| Detection condition      | Green LED | Yellow LED | Red LED     | Active Condition |
|--------------------------|-----------|------------|-------------|------------------|
| Helmet only              | ON        | OFF        | OFF         | GREEN            |
| Gloves only              | OFF       | ON         | OFF         | YELLOW           |
| Both helmet AND gloves   | OFF       | OFF        | BLINKING    | RED_BLINKING     |
| Neither detected         | OFF       | OFF        | OFF         | OFF              |

Supports real hardware execution on Raspberry Pi 5 (via gpiozero / RP1)
with automatic non-blocking simulated fallback on non-Pi development machines.
"""

import sys
import time
import threading
from typing import Dict, Any, Optional

# Pin Definitions (BCM GPIO numbers and Physical Header Pins)
PIN_YELLOW_BCM = 17   # Physical Pin 11 - Gloves Only Indicator
PIN_GREEN_BCM = 27    # Physical Pin 13 - Helmet Only Indicator
PIN_RED_BCM = 22      # Physical Pin 15 - Combined Both Detected Indicator (Blinking)
PIN_GND_PHYSICAL = 14 # Physical Pin 14 (or Pin 9 / Pin 6)


class PiGPIOManager:
    """
    Manages 3-LED stack light indicators with non-blocking actuation.
    Controls physical GPIO on Raspberry Pi 5 or provides simulated fallback.
    """
    def __init__(self, blink_interval: float = 0.5):
        self.is_hardware = False
        self.hw_error = None
        self.led_yellow = None
        self.led_green = None
        self.led_red = None

        # Virtual state tracking
        self.state_yellow = False
        self.state_green = False
        self.state_red = False
        self.is_blinking = False
        self.blink_interval = float(blink_interval)
        self.active_condition = "OFF"

        # Threading for non-blocking simulation blink
        self._stop_blink_event = threading.Event()
        self._blink_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self._init_gpio()

    def _init_gpio(self):
        """Attempts to initialize Raspberry Pi 5 GPIO pins via gpiozero."""
        try:
            from gpiozero import LED
            self.led_yellow = LED(PIN_YELLOW_BCM)
            self.led_green = LED(PIN_GREEN_BCM)
            self.led_red = LED(PIN_RED_BCM)
            self.is_hardware = True
            print(f"[GPIO] Raspberry Pi 5 GPIO initialized successfully (Pins: Green={PIN_GREEN_BCM}, Yellow={PIN_YELLOW_BCM}, Red={PIN_RED_BCM})")
        except Exception as e:
            self.is_hardware = False
            self.hw_error = str(e)
            print(f"[GPIO] Physical GPIO not available ({e}). Running in Virtual/Simulated Mode for live dashboard.")

    def _start_red_blink(self):
        """Starts non-blocking blinking on Red LED (both hardware and simulation)."""
        with self._lock:
            if self.is_blinking:
                return
            self.is_blinking = True

            if self.is_hardware:
                try:
                    self.led_red.blink(on_time=self.blink_interval, off_time=self.blink_interval, background=True)
                except Exception as e:
                    print(f"[GPIO] Hardware blink error: {e}")
            else:
                self.state_red = True
                self._stop_blink_event.clear()
                self._blink_thread = threading.Thread(target=self._simulate_blink_worker, daemon=True)
                self._blink_thread.start()

    def _stop_red_blink(self):
        """Stops Red LED blinking and guarantees it is de-energized."""
        with self._lock:
            if not self.is_blinking:
                self.state_red = False
                return
            self.is_blinking = False
            self._stop_blink_event.set()

            if self.is_hardware:
                try:
                    self.led_red.off()
                except Exception as e:
                    print(f"[GPIO] Hardware stop error: {e}")
            self.state_red = False

    def _simulate_blink_worker(self):
        """Background worker simulating 0.5s square-wave blinking in virtual mode."""
        while not self._stop_blink_event.is_set() and self.is_blinking:
            self._stop_blink_event.wait(self.blink_interval)
            if self.is_blinking and not self._stop_blink_event.is_set():
                self.state_red = not self.state_red
        self.state_red = False

    def update(self, has_helmet: bool, has_gloves: bool) -> Dict[str, Any]:
        """
        Applies authoritative M3 Three-LED activation rules:
        1. Both Helmet AND Gloves -> RED LED BLINKING, Green OFF, Yellow OFF
        2. Helmet ONLY            -> GREEN LED ON, Yellow OFF, Red OFF
        3. Gloves ONLY            -> YELLOW LED ON, Green OFF, Red OFF
        4. Neither                -> ALL LEDS OFF
        """
        h = bool(has_helmet)
        g = bool(has_gloves)

        if h and g:
            # Case 1: Both detected -> Red blinks, Green & Yellow must remain OFF
            self.state_green = False
            self.state_yellow = False
            self._start_red_blink()
            self.active_condition = "RED_BLINKING"
        elif h and not g:
            # Case 2: Helmet only -> Green ON, Yellow & Red OFF
            self._stop_red_blink()
            self.state_green = True
            self.state_yellow = False
            self.active_condition = "GREEN"
        elif g and not h:
            # Case 3: Gloves only -> Yellow ON, Green & Red OFF
            self._stop_red_blink()
            self.state_green = False
            self.state_yellow = True
            self.active_condition = "YELLOW"
        else:
            # Case 4: Neither detected -> All LEDs OFF
            self._stop_red_blink()
            self.state_green = False
            self.state_yellow = False
            self.active_condition = "OFF"

        # Synchronize physical actuators on Raspberry Pi 5
        if self.is_hardware:
            try:
                if self.state_green:
                    self.led_green.on()
                else:
                    self.led_green.off()

                if self.state_yellow:
                    self.led_yellow.on()
                else:
                    self.led_yellow.off()

                # Note: Red is managed asynchronously via blink() / off()
            except Exception as e:
                print(f"[GPIO] Hardware write error: {e}")

        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        """Returns structured LED status for WebSocket telemetry and live dashboard UI."""
        if self.active_condition == "RED_BLINKING":
            active_label = "BOTH DETECTED – RED LED BLINKING"
        elif self.active_condition == "GREEN":
            active_label = "GREEN LED ACTIVE (HELMET ONLY)"
        elif self.active_condition == "YELLOW":
            active_label = "YELLOW LED ACTIVE (GLOVES ONLY)"
        else:
            active_label = "ALL LEDS OFF"

        return {
            "yellow": {
                "active": self.state_yellow,
                "blinking": False,
                "pin_bcm": PIN_YELLOW_BCM,
                "pin_physical": 11,
                "condition": "Gloves Indicator (Gloves Only)",
                "color": "#ffd600"
            },
            "green": {
                "active": self.state_green,
                "blinking": False,
                "pin_bcm": PIN_GREEN_BCM,
                "pin_physical": 13,
                "condition": "Helmet Indicator (Helmet Only)",
                "color": "#00e676"
            },
            "red": {
                "active": self.state_red or self.is_blinking,
                "blinking": self.is_blinking,
                "pin_bcm": PIN_RED_BCM,
                "pin_physical": 15,
                "condition": "Combined Indicator (Blinks when Both Helmet & Gloves Detected)",
                "color": "#ff1744"
            },
            "gnd_pin_physical": PIN_GND_PHYSICAL,
            "active_condition": self.active_condition,
            "active_label": active_label,
            "is_hardware": self.is_hardware,
            "mode_label": "Raspberry Pi 5 (RP1 GPIO Active)" if self.is_hardware else "Simulated GPIO Mode"
        }

    def safe_state(self):
        """Immediately de-energizes all actuator outputs into a safe OFF state."""
        self._stop_red_blink()
        self.state_yellow = False
        self.state_green = False
        self.state_red = False
        self.active_condition = "OFF"
        if self.is_hardware:
            try:
                self.led_yellow.off()
                self.led_green.off()
                self.led_red.off()
            except Exception:
                pass

    def cleanup(self):
        """Turn off all LEDs and close GPIO handles safely."""
        self.safe_state()
        if self.is_hardware:
            try:
                self.led_yellow.close()
                self.led_green.close()
                self.led_red.close()
            except Exception:
                pass
        print("[GPIO] Pins reset and released.")


# Global instance
gpio_controller = PiGPIOManager()
