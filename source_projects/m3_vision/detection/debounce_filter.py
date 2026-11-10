"""
Consecutive-Frame Debounce State Machine for PPE Detection
Milestone 3 - Task 3: Industrial Debounce & Chattering Prevention Filter
"""

from typing import Tuple, Dict, Any, Callable, Optional

class ConsecutiveFrameDebounceFilter:
    """
    Filters raw frame-by-frame detections through an N-consecutive-frame
    confirmation window before issuing actuator state transitions.
    Prevents sensor noise, occlusion flickers, and false momentary triggers.
    """
    def __init__(self, confirmation_n: int = 3, on_transition: Optional[Callable[[bool, bool], None]] = None):
        self.n = max(1, confirmation_n)
        self.on_transition = on_transition

        # Confirmed stable state (helmet, gloves)
        self.confirmed_helmet = False
        self.confirmed_gloves = False

        # Candidate state pending confirmation
        self.candidate_state: Optional[Tuple[bool, bool]] = None
        self.consecutive_count = 0

        # Telemetry & Diagnostics
        self.total_frames_processed = 0
        self.transition_count = 0
        self.filtered_glitches_count = 0

    def set_n(self, n: int):
        """Dynamically adjust confirmation threshold N."""
        self.n = max(1, int(n))
        self.consecutive_count = 0
        self.candidate_state = None

    def process_frame(self, raw_helmet: bool, raw_gloves: bool) -> Tuple[bool, bool, bool]:
        """
        Process a single raw frame.
        Returns:
            confirmed_helmet (bool)
            confirmed_gloves (bool)
            state_changed (bool): True if this frame triggered a confirmed state change
        """
        self.total_frames_processed += 1
        raw_state = (bool(raw_helmet), bool(raw_gloves))
        current_confirmed = (self.confirmed_helmet, self.confirmed_gloves)

        # Case 1: Raw state matches already confirmed stable state
        if raw_state == current_confirmed:
            if self.consecutive_count > 0:
                # Intervening frame returned to confirmed state: glitch filtered!
                self.filtered_glitches_count += 1
            self.candidate_state = None
            self.consecutive_count = 0
            return self.confirmed_helmet, self.confirmed_gloves, False

        # Case 2: Raw state differs from confirmed state
        if raw_state == self.candidate_state:
            # Another consecutive frame of the candidate state
            self.consecutive_count += 1
        else:
            # First frame of a new candidate state
            self.candidate_state = raw_state
            self.consecutive_count = 1

        # Check if candidate has reached N consecutive confirmations
        if self.consecutive_count >= self.n:
            # Transition confirmed!
            self.confirmed_helmet, self.confirmed_gloves = self.candidate_state
            self.candidate_state = None
            self.consecutive_count = 0
            self.transition_count += 1

            if self.on_transition:
                self.on_transition(self.confirmed_helmet, self.confirmed_gloves)

            return self.confirmed_helmet, self.confirmed_gloves, True

        # Candidate has fewer than N frames: suppress actuator action
        return self.confirmed_helmet, self.confirmed_gloves, False

    def get_status(self) -> Dict[str, Any]:
        """Telemetry diagnostics for debounce filter."""
        return {
            "n_threshold": self.n,
            "confirmed_helmet": self.confirmed_helmet,
            "confirmed_gloves": self.confirmed_gloves,
            "candidate_state": self.candidate_state,
            "consecutive_count": self.consecutive_count,
            "total_frames": self.total_frames_processed,
            "transitions_fired": self.transition_count,
            "filtered_glitches": self.filtered_glitches_count
        }

