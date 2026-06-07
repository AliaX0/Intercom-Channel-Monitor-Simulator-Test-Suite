# Intercom Channel Simulator & Test Suite

A Python simulation of a professional real-time intercom communication channel, built with a comprehensive pytest test suite.

This project models core behaviours found in mission-critical communication systems — user management, mute/unmute, floor control (talking states), message transmission, and channel lifecycle — and validates every behaviour with structured automated tests.

---

## Why this project?

Professional intercom systems (used in broadcast, aerospace, and live events) must behave predictably under all conditions: full capacity, conflicting states, invalid inputs, and mid-session lifecycle changes. 
This project demonstrates how a test engineer thinks about such a system:

- **What should happen** in the happy path
- **What should be rejected** at every boundary
- **What should not break** when state changes occur mid-session

---

## Project structure

```
intercom_project/
├── intercom_channel.py   # Core simulation: channel, users, messages, states
├── test_intercom.py      # Full pytest suite (unit, edge case, regression, integration)
├── requirements.txt      # Dependencies
└── README.md
```

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Running the tests

```bash
# Run all tests with verbose output
pytest test_intercom.py -v

# Run a specific test class
pytest test_intercom.py::TestMessageTransmission -v

# Generate a plain-text report
pytest test_intercom.py -v > test_report.txt
```

---

## What is being tested

| Test class                  | Coverage area                                              |
|-----------------------------|------------------------------------------------------------|
| `TestChannelCreation`       | Initialisation, name/capacity validation, default state    |
| `TestUserJoin`              | Join happy path, duplicates, capacity limits, locked/closed|
| `TestUserLeave`             | Leave, re-join, capacity freeing, closed channel           |
| `TestMuteUnmute`            | Mute/unmute state, interactions with talking state         |
| `TestTalkingState`          | Floor control, one-talker enforcement, state transitions   |
| `TestMessageTransmission`   | Transmit, muted sender, empty/long messages, ordering      |
| `TestChannelLifecycle`      | Lock, unlock, close, permanent closure                     |
| `TestAuditLog`              | Event log integrity, immutability of public accessors      |
| `TestIntegrationWorkflows`  | Realistic multi-step sequences end-to-end                  |

---

## Channel states

```
ACTIVE  →  LOCKED  →  ACTIVE   (lock / unlock)
ACTIVE  →  CLOSED              (permanent)
LOCKED  →  CLOSED              (permanent)
```

## User states

```
CONNECTED  →  MUTED      (mute)
MUTED      →  CONNECTED  (unmute)
CONNECTED  →  TALKING    (start_talking)
TALKING    →  CONNECTED  (stop_talking)
TALKING    →  MUTED      (mute)
```

---

## Design decisions

**Typed exceptions over silent failures** — every invalid operation raises a specific, named exception. This makes test assertions precise and makes production error handling unambiguous.

**Immutable public accessors** — `users`, `messages`, and `event_log` all return copies. External code cannot accidentally mutate internal state.

**Single talker enforcement** — only one user may hold the floor at a time. This mirrors real intercom behaviour where simultaneous transmission causes signal collision.

**Audit trail** — every state change is timestamped and appended to the event log, supporting post-session replay and debugging.

---

## Author

Lia — [github.com/AliaX0](https://github.com/AliaX0)
