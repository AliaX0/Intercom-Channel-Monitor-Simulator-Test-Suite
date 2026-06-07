"""
intercom_channel.py
-------------------
A software simulation of a professional intercom communication channel,
modelling the core behaviours of a real-time multi-user comms system.

Designed to be testable: all state is explicit, all transitions are validated,
and all errors are raised as typed exceptions rather than silent failures.

Author: Lia Wilkinson
"""

from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ─── Enums ────────────────────────────────────────────────────────────────────

class ChannelState(Enum):
    """Lifecycle states of an intercom channel."""
    ACTIVE   = auto()
    LOCKED   = auto()   # No new users may join
    CLOSED   = auto()   # Channel is shut down; no operations permitted


class UserState(Enum):
    """States a user can be in while connected to a channel."""
    CONNECTED  = auto()
    MUTED      = auto()
    TALKING    = auto()


# ─── Exceptions ───────────────────────────────────────────────────────────────

class IntercomError(Exception):
    """Base exception for all intercom errors."""


class ChannelClosedError(IntercomError):
    """Raised when an operation is attempted on a closed channel."""


class ChannelLockedError(IntercomError):
    """Raised when a user tries to join a locked channel."""


class UserNotFoundError(IntercomError):
    """Raised when an operation references a user not in the channel."""


class UserAlreadyConnectedError(IntercomError):
    """Raised when a user attempts to join a channel they are already in."""


class UserMutedError(IntercomError):
    """Raised when a muted user attempts to transmit."""


class UserAlreadyTalkingError(IntercomError):
    """Raised when a user tries to talk while already marked as talking."""


class CapacityExceededError(IntercomError):
    """Raised when joining would exceed the channel's maximum capacity."""


class MessageTooLongError(IntercomError):
    """Raised when a message exceeds the maximum allowed length."""


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class Message:
    """A transmitted message recorded in the channel log."""
    id:         str
    sender:     str
    content:    str
    timestamp:  float
    channel_id: str


@dataclass
class User:
    """Represents a connected user within an intercom channel."""
    username:   str
    state:      UserState = UserState.CONNECTED
    joined_at:  float     = field(default_factory=time.time)


# ─── Core Channel Class ────────────────────────────────────────────────────────

class IntercomChannel:
    """
    Simulates a single intercom channel in a professional communications system.

    Features:
    - User join / leave with capacity enforcement
    - Mute / unmute per user
    - Talking state (only one user may hold the floor at a time)
    - Message transmission with logging
    - Channel lock (no new joins) and close (full shutdown)
    - Full audit trail via message log and event log
    """

    MAX_MESSAGE_LENGTH = 500

    def __init__(self, name: str, max_users: int = 10, channel_id: Optional[str] = None):
        if max_users < 1:
            raise ValueError("max_users must be at least 1")
        if not name or not name.strip():
            raise ValueError("Channel name cannot be empty")

        self.name:       str          = name.strip()
        self.max_users:  int          = max_users
        self.channel_id: str          = channel_id or str(uuid.uuid4())
        self.state:      ChannelState = ChannelState.ACTIVE

        self._users:     dict[str, User]  = {}
        self._messages:  list[Message]    = []
        self._event_log: list[str]        = []

        self._log_event(f"Channel '{self.name}' created (capacity: {self.max_users})")

    # ─── Internal helpers ─────────────────────────────────────────────────────

    def _require_open(self) -> None:
        """Raise ChannelClosedError if the channel is not active or locked."""
        if self.state == ChannelState.CLOSED:
            raise ChannelClosedError(f"Channel '{self.name}' is closed")

    def _require_active(self) -> None:
        """Raise if channel is not in ACTIVE state (closed or locked)."""
        self._require_open()
        if self.state == ChannelState.LOCKED:
            raise ChannelLockedError(f"Channel '{self.name}' is locked — no new users may join")

    def _require_user(self, username: str) -> User:
        """Return the User object or raise UserNotFoundError."""
        if username not in self._users:
            raise UserNotFoundError(f"User '{username}' is not in channel '{self.name}'")
        return self._users[username]

    def _log_event(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self._event_log.append(f"[{timestamp}] {message}")

    # ─── User management ─────────────────────────────────────────────────────

    def join(self, username: str) -> User:
        """
        Add a user to the channel.

        Raises:
            ChannelClosedError       — channel is shut down
            ChannelLockedError       — channel is locked to new joins
            UserAlreadyConnectedError— user is already in this channel
            CapacityExceededError    — channel is at maximum capacity
            ValueError               — username is empty or whitespace
        """
        if not username or not username.strip():
            raise ValueError("Username cannot be empty")

        username = username.strip()
        self._require_active()

        if username in self._users:
            raise UserAlreadyConnectedError(
                f"User '{username}' is already connected to channel '{self.name}'"
            )
        if len(self._users) >= self.max_users:
            raise CapacityExceededError(
                f"Channel '{self.name}' is full ({self.max_users}/{self.max_users})"
            )

        user = User(username=username)
        self._users[username] = user
        self._log_event(f"'{username}' joined ({len(self._users)}/{self.max_users} users)")
        return user

    def leave(self, username: str) -> None:
        """
        Remove a user from the channel.
        If the user was talking, the talking state is automatically released.

        Raises:
            ChannelClosedError  — channel is shut down
            UserNotFoundError   — user is not in this channel
        """
        self._require_open()
        user = self._require_user(username)

        del self._users[username]
        self._log_event(f"'{username}' left (was {user.state.name})")

    # ─── Mute / unmute ────────────────────────────────────────────────────────

    def mute(self, username: str) -> None:
        """
        Mute a user. A muted user cannot transmit messages.
        If the user was talking, the talking state is released first.

        Raises:
            ChannelClosedError  — channel is shut down
            UserNotFoundError   — user is not in this channel
        """
        self._require_open()
        user = self._require_user(username)
        user.state = UserState.MUTED
        self._log_event(f"'{username}' muted")

    def unmute(self, username: str) -> None:
        """
        Unmute a user, returning them to CONNECTED state.

        Raises:
            ChannelClosedError  — channel is shut down
            UserNotFoundError   — user is not in this channel
        """
        self._require_open()
        user = self._require_user(username)
        user.state = UserState.CONNECTED
        self._log_event(f"'{username}' unmuted")

    # ─── Talking state ────────────────────────────────────────────────────────

    def start_talking(self, username: str) -> None:
        """
        Mark a user as actively transmitting audio (holding the floor).
        Only one user may be in TALKING state at a time.

        Raises:
            ChannelClosedError      — channel is shut down
            UserNotFoundError       — user is not in this channel
            UserMutedError          — muted users cannot talk
            UserAlreadyTalkingError — another user is already talking
        """
        self._require_open()
        user = self._require_user(username)

        if user.state == UserState.MUTED:
            raise UserMutedError(f"'{username}' is muted and cannot transmit")
        if user.state == UserState.TALKING:
            raise UserAlreadyTalkingError(f"'{username}' is already talking")

        # Check if another user is currently talking
        current_talker = self._current_talker()
        if current_talker and current_talker != username:
            raise UserAlreadyTalkingError(
                f"'{current_talker}' is already holding the floor"
            )

        user.state = UserState.TALKING
        self._log_event(f"'{username}' started talking")

    def stop_talking(self, username: str) -> None:
        """
        Release the floor — return user from TALKING to CONNECTED.

        Raises:
            ChannelClosedError  — channel is shut down
            UserNotFoundError   — user is not in this channel
        """
        self._require_open()
        user = self._require_user(username)
        if user.state == UserState.TALKING:
            user.state = UserState.CONNECTED
            self._log_event(f"'{username}' stopped talking")

    def _current_talker(self) -> Optional[str]:
        """Return the username of whoever is currently talking, or None."""
        for username, user in self._users.items():
            if user.state == UserState.TALKING:
                return username
        return None

    # ─── Messaging ────────────────────────────────────────────────────────────

    def transmit(self, sender: str, content: str) -> Message:
        """
        Transmit a text message from a user to the channel log.

        Raises:
            ChannelClosedError  — channel is shut down
            UserNotFoundError   — sender is not in this channel
            UserMutedError      — muted users cannot transmit
            MessageTooLongError — message exceeds MAX_MESSAGE_LENGTH
            ValueError          — message content is empty
        """
        self._require_open()
        user = self._require_user(sender)

        if not content or not content.strip():
            raise ValueError("Message content cannot be empty")
        if len(content) > self.MAX_MESSAGE_LENGTH:
            raise MessageTooLongError(
                f"Message length {len(content)} exceeds limit of {self.MAX_MESSAGE_LENGTH}"
            )
        if user.state == UserState.MUTED:
            raise UserMutedError(f"'{sender}' is muted and cannot transmit")

        msg = Message(
            id=str(uuid.uuid4()),
            sender=sender,
            content=content.strip(),
            timestamp=time.time(),
            channel_id=self.channel_id
        )
        self._messages.append(msg)
        self._log_event(f"'{sender}' transmitted: \"{content[:40]}{'...' if len(content) > 40 else ''}\"")
        return msg

    # ─── Channel lifecycle ────────────────────────────────────────────────────

    def lock(self) -> None:
        """
        Lock the channel — existing users stay, no new users may join.

        Raises:
            ChannelClosedError — channel is already closed
        """
        self._require_open()
        self.state = ChannelState.LOCKED
        self._log_event(f"Channel '{self.name}' locked (no new joins)")

    def unlock(self) -> None:
        """
        Unlock the channel — re-allow new users to join.

        Raises:
            ChannelClosedError — channel is closed
        """
        self._require_open()
        self.state = ChannelState.ACTIVE
        self._log_event(f"Channel '{self.name}' unlocked")

    def close(self) -> None:
        """
        Permanently close the channel. All further operations will raise
        ChannelClosedError. This cannot be undone.
        """
        self.state = ChannelState.CLOSED
        user_count = len(self._users)
        self._users.clear()
        self._log_event(
            f"Channel '{self.name}' closed ({user_count} user(s) disconnected)"
        )

    # ─── Read-only accessors ──────────────────────────────────────────────────

    @property
    def users(self) -> dict[str, User]:
        """Read-only snapshot of current users."""
        return dict(self._users)

    @property
    def user_count(self) -> int:
        return len(self._users)

    @property
    def messages(self) -> list[Message]:
        """Read-only copy of the message log."""
        return list(self._messages)

    @property
    def message_count(self) -> int:
        return len(self._messages)

    @property
    def event_log(self) -> list[str]:
        """Read-only audit trail of all channel events."""
        return list(self._event_log)

    def get_user(self, username: str) -> User:
        return self._require_user(username)

    def is_user_connected(self, username: str) -> bool:
        return username in self._users

    def get_messages_from(self, sender: str) -> list[Message]:
        return [m for m in self._messages if m.sender == sender]

    def __repr__(self) -> str:
        return (
            f"IntercomChannel(name={self.name!r}, "
            f"state={self.state.name}, "
            f"users={self.user_count}/{self.max_users})"
        )
