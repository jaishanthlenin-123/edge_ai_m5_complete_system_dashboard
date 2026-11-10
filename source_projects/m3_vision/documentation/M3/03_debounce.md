# Consecutive-Frame Debounce Filter Implementation & Verification
**Milestone:** M3 – Decide and Act  
**Document ID:** `M3-DOC-03`  
**System Target:** Raspberry Pi 5 Actuator Subsystem  
**Author:** Lenin (`jaishanthlenin-123`)  

---

## 1. Problem Statement & Motivation

In real-world computer vision edge systems, individual frames frequently suffer from momentary lighting changes, optical glare, worker head tilts, or temporary occlusions by conveyor machinery. If the physical GPIO actuator reacted instantaneously to raw single-frame detections, the industrial stack lights and relays would experience **rapid chattering**, leading to:
1. Relay contact degradation and premature hardware failure.
2. Operator visual confusion caused by flickering LED indicators.
3. False safety violation alerts on momentary occlusion.

Task 3 designs and verifies a deterministic, configurable consecutive-frame confirmation state machine that guarantees actuator stability without violating the Milestone 3 Three-LED truth table.

---

## 2. Debounce State Machine Architecture

```
                       +-----------------------+
                       | Confirmed State (S)   |
                       | Output Actuators SET  |
                       +-----------+-----------+
                                   |
                             Raw Frame != S
                                   |
                                   v
                       +-----------------------+
                       | Candidate State (C)   |
                       | consecutive_count = 1 |
                       +-----------+-----------+
                                   |
         +-------------------------+-------------------------+
         |                                                   |
   Raw Frame == C                                     Raw Frame == S
         |                                                   |
consecutive_count += 1                                Reset Counter:
         |                                            consecutive_count = 0
         v                                            candidate_state = None
Is consecutive_count >= N?                            (Glitch Filtered!)
   /           \
  Yes           No
  /               \
Transition:     Maintain Current S
S = C           Actuator Unchanged
Fire Actuator!
```

---

## 3. Mathematical Specification

Let $f_t \in \{0, 1\}^2$ represent the raw binary detection tuple $(\text{helmet}, \text{gloves})$ at time frame $t$.  
Let $S_t \in \{0, 1\}^2$ represent the confirmed state commanded to the GPIO pins.  
Let $C_t \in \{0, 1\}^2$ represent the pending candidate state, and $k_t \in \mathbb{N}$ represent the consecutive frame counter.

$$\begin{aligned}
\text{If } f_t = S_t: &\quad k_t = 0,\quad C_t = \varnothing,\quad S_{t+1} = S_t \\
\text{If } f_t \neq S_t \land f_t = C_t: &\quad k_t = k_{t-1} + 1 \\
\text{If } f_t \neq S_t \land f_t \neq C_t: &\quad k_t = 1,\quad C_t = f_t \\
\text{Transition Rule:} &\quad S_{t+1} = \begin{cases} C_t & \text{if } k_t \ge N \\ S_t & \text{otherwise} \end{cases}
\end{aligned}$$

---

## 4. Test Scenarios & Verification Evidence

The test suite `tests/M3/test_debounce.py` validates all 7 mandatory operating conditions:

| Test ID | Test Scenario | Input Stimulus | Expected Behavior | Actuator Status | Result |
|---|---|---|---|---|---|
| **TC01** | One bad frame | 1 frame $(1, 0)$ from $(0, 0)$ | Filtered immediately; counter resets | All LEDs stay **OFF** | **PASS** |
| **TC02** | Two consecutive bad frames | 2 frames $(1, 0)$ when $N=3$ | Counter reaches 2; transition suppressed | All LEDs stay **OFF** | **PASS** |
| **TC03** | Fewer than $N$ frames | 3 frames $(1, 1)$ when $N=4$ | Counter reaches $N-1$; action suppressed | All LEDs stay **OFF** | **PASS** |
| **TC04** | Exactly $N$ consecutive frames | Exactly 3 frames $(1, 0)$ when $N=3$ | Confirmed transition fires at frame 3 | LED 1 (Green) turns **ON** | **PASS** |
| **TC05** | More than $N$ consecutive frames | 10 consecutive frames $(1, 0)$ | Fires exactly once at frame $N$; zero duplicates | LED 1 stays **ON** steadily | **PASS** |
| **TC06** | Intervening valid frame | 2 frames $(1, 0)$ followed by $(0, 0)$ | Counter resets to 0; prior state locked | Glitch count incremented | **PASS** |
| **TC07** | Persistent Both Detections | 3 frames $(1, 1)$ when $N=3$ | Confirmed Both transition fires | Red LED **BLINKS** (Green & Yellow OFF) | **PASS** |

### Transition Timeline Artifact:
The simulation timeline has been recorded to:
`evidence/M3/03_debounce/debounce_verification_timeline.csv`

