"""
test_intercom.py
----------------
Full pytest test suite for the IntercomChannel simulation.

Test strategy:
  - Unit tests:       each method tested in isolation with clear preconditions
  - Edge cases:       boundary values, empty inputs, state conflicts
  - Regression tests: scenarios that catch previously identified failure modes
  - Integration:      multi-step workflows simulating realistic usage

Run with:  pytest test_intercom.py -v
Report:    pytest test_intercom.py -v --tb=short > test_report.txt

Author: Lia Wilkinson
"""

import pytest
import time
from intercom_channel import (
    IntercomChannel,
    ChannelState,
    UserState,
    ChannelClosedError,
    ChannelLockedError,
    UserNotFoundError,
    UserAlreadyConnectedError,
    UserMutedError,
    UserAlreadyTalkingError,
    CapacityExceededError,
    MessageTooLongError,
)


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def channel():
    """A fresh, active channel for each test."""
    return IntercomChannel(name="Flight Deck", max_users=5)


@pytest.fixture
def channel_with_users(channel):
    """Channel pre-populated with three users."""
    channel.join("Alice")
    channel.join("Bob")
    channel.join("Charlie")
    return channel


# ══════════════════════════════════════════════════════════════════════════════
# 1. CHANNEL CREATION
# ══════════════════════════════════════════════════════════════════════════════

class TestChannelCreation:

    def test_channel_is_active_on_creation(self, channel):
        assert channel.state == ChannelState.ACTIVE

    def test_channel_has_correct_name(self, channel):
        assert channel.name == "Flight Deck"

    def test_channel_has_correct_capacity(self, channel):
        assert channel.max_users == 5

    def test_channel_starts_empty(self, channel):
        assert channel.user_count == 0

    def test_channel_has_no_messages_on_creation(self, channel):
        assert channel.message_count == 0

    def test_channel_id_is_assigned(self, channel):
        assert channel.channel_id is not None
        assert len(channel.channel_id) > 0

    def test_custom_channel_id_is_preserved(self):
        ch = IntercomChannel(name="Control", channel_id="CTRL-001")
        assert ch.channel_id == "CTRL-001"

    def test_channel_name_is_stripped(self):
        ch = IntercomChannel(name="  Ground Control  ")
        assert ch.name == "Ground Control"

    def test_empty_name_raises(self):
        with pytest.raises(ValueError):
            IntercomChannel(name="")

    def test_whitespace_name_raises(self):
        with pytest.raises(ValueError):
            IntercomChannel(name="   ")

    def test_zero_capacity_raises(self):
        with pytest.raises(ValueError):
            IntercomChannel(name="Test", max_users=0)

    def test_negative_capacity_raises(self):
        with pytest.raises(ValueError):
            IntercomChannel(name="Test", max_users=-1)

    def test_creation_is_logged(self, channel):
        assert any("created" in entry for entry in channel.event_log)


# ══════════════════════════════════════════════════════════════════════════════
# 2. USER JOIN
# ══════════════════════════════════════════════════════════════════════════════

class TestUserJoin:

    def test_user_can_join(self, channel):
        user = channel.join("Alice")
        assert channel.is_user_connected("Alice")

    def test_join_returns_user_object(self, channel):
        user = channel.join("Alice")
        assert user.username == "Alice"

    def test_joined_user_is_in_connected_state(self, channel):
        user = channel.join("Alice")
        assert user.state == UserState.CONNECTED

    def test_user_count_increments(self, channel):
        channel.join("Alice")
        assert channel.user_count == 1
        channel.join("Bob")
        assert channel.user_count == 2

    def test_duplicate_join_raises(self, channel):
        channel.join("Alice")
        with pytest.raises(UserAlreadyConnectedError):
            channel.join("Alice")

    def test_capacity_exactly_met(self):
        ch = IntercomChannel(name="Full", max_users=2)
        ch.join("Alice")
        ch.join("Bob")
        assert ch.user_count == 2

    def test_join_beyond_capacity_raises(self):
        ch = IntercomChannel(name="Full", max_users=2)
        ch.join("Alice")
        ch.join("Bob")
        with pytest.raises(CapacityExceededError):
            ch.join("Charlie")

    def test_join_locked_channel_raises(self, channel):
        channel.lock()
        with pytest.raises(ChannelLockedError):
            channel.join("Alice")

    def test_join_closed_channel_raises(self, channel):
        channel.close()
        with pytest.raises(ChannelClosedError):
            channel.join("Alice")

    def test_empty_username_raises(self, channel):
        with pytest.raises(ValueError):
            channel.join("")

    def test_whitespace_username_raises(self, channel):
        with pytest.raises(ValueError):
            channel.join("   ")

    def test_username_is_stripped_on_join(self, channel):
        channel.join("  Alice  ")
        assert channel.is_user_connected("Alice")

    def test_join_is_logged(self, channel):
        channel.join("Alice")
        assert any("Alice" in entry and "joined" in entry for entry in channel.event_log)


# ══════════════════════════════════════════════════════════════════════════════
# 3. USER LEAVE
# ══════════════════════════════════════════════════════════════════════════════

class TestUserLeave:

    def test_user_can_leave(self, channel_with_users):
        channel_with_users.leave("Alice")
        assert not channel_with_users.is_user_connected("Alice")

    def test_user_count_decrements(self, channel_with_users):
        channel_with_users.leave("Alice")
        assert channel_with_users.user_count == 2

    def test_other_users_unaffected_by_leave(self, channel_with_users):
        channel_with_users.leave("Alice")
        assert channel_with_users.is_user_connected("Bob")
        assert channel_with_users.is_user_connected("Charlie")

    def test_leave_nonexistent_user_raises(self, channel):
        with pytest.raises(UserNotFoundError):
            channel.leave("Nobody")

    def test_leave_closed_channel_raises(self, channel_with_users):
        channel_with_users.close()
        with pytest.raises(ChannelClosedError):
            channel_with_users.leave("Alice")

    def test_user_can_rejoin_after_leaving(self, channel):
        channel.join("Alice")
        channel.leave("Alice")
        channel.join("Alice")  # Should not raise
        assert channel.is_user_connected("Alice")

    def test_leave_frees_capacity(self):
        ch = IntercomChannel(name="Tight", max_users=1)
        ch.join("Alice")
        ch.leave("Alice")
        ch.join("Bob")  # Should not raise CapacityExceededError
        assert ch.is_user_connected("Bob")

    def test_leave_is_logged(self, channel_with_users):
        channel_with_users.leave("Bob")
        assert any("Bob" in entry and "left" in entry for entry in channel_with_users.event_log)


# ══════════════════════════════════════════════════════════════════════════════
# 4. MUTE / UNMUTE
# ══════════════════════════════════════════════════════════════════════════════

class TestMuteUnmute:

    def test_mute_sets_user_state(self, channel_with_users):
        channel_with_users.mute("Alice")
        assert channel_with_users.get_user("Alice").state == UserState.MUTED

    def test_unmute_returns_to_connected(self, channel_with_users):
        channel_with_users.mute("Alice")
        channel_with_users.unmute("Alice")
        assert channel_with_users.get_user("Alice").state == UserState.CONNECTED

    def test_muting_nonexistent_user_raises(self, channel):
        with pytest.raises(UserNotFoundError):
            channel.mute("Ghost")

    def test_unmuting_nonexistent_user_raises(self, channel):
        with pytest.raises(UserNotFoundError):
            channel.unmute("Ghost")

    def test_mute_on_closed_channel_raises(self, channel_with_users):
        channel_with_users.close()
        with pytest.raises(ChannelClosedError):
            channel_with_users.mute("Alice")

    def test_muting_talking_user_stops_talking(self, channel_with_users):
        channel_with_users.start_talking("Alice")
        channel_with_users.mute("Alice")
        assert channel_with_users.get_user("Alice").state == UserState.MUTED

    def test_mute_only_affects_target_user(self, channel_with_users):
        channel_with_users.mute("Alice")
        assert channel_with_users.get_user("Bob").state == UserState.CONNECTED

    def test_mute_is_logged(self, channel_with_users):
        channel_with_users.mute("Charlie")
        assert any("Charlie" in e and "muted" in e for e in channel_with_users.event_log)

    def test_unmute_is_logged(self, channel_with_users):
        channel_with_users.mute("Charlie")
        channel_with_users.unmute("Charlie")
        assert any("Charlie" in e and "unmuted" in e for e in channel_with_users.event_log)


# ══════════════════════════════════════════════════════════════════════════════
# 5. TALKING STATE
# ══════════════════════════════════════════════════════════════════════════════

class TestTalkingState:

    def test_user_can_start_talking(self, channel_with_users):
        channel_with_users.start_talking("Alice")
        assert channel_with_users.get_user("Alice").state == UserState.TALKING

    def test_user_can_stop_talking(self, channel_with_users):
        channel_with_users.start_talking("Alice")
        channel_with_users.stop_talking("Alice")
        assert channel_with_users.get_user("Alice").state == UserState.CONNECTED

    def test_muted_user_cannot_talk(self, channel_with_users):
        channel_with_users.mute("Alice")
        with pytest.raises(UserMutedError):
            channel_with_users.start_talking("Alice")

    def test_only_one_talker_at_a_time(self, channel_with_users):
        channel_with_users.start_talking("Alice")
        with pytest.raises(UserAlreadyTalkingError):
            channel_with_users.start_talking("Bob")

    def test_user_already_talking_raises(self, channel_with_users):
        channel_with_users.start_talking("Alice")
        with pytest.raises(UserAlreadyTalkingError):
            channel_with_users.start_talking("Alice")

    def test_second_user_can_talk_after_first_stops(self, channel_with_users):
        channel_with_users.start_talking("Alice")
        channel_with_users.stop_talking("Alice")
        channel_with_users.start_talking("Bob")  # Should not raise
        assert channel_with_users.get_user("Bob").state == UserState.TALKING

    def test_stop_talking_on_non_talker_is_safe(self, channel_with_users):
        # Should not raise — no-op if user isn't talking
        channel_with_users.stop_talking("Alice")
        assert channel_with_users.get_user("Alice").state == UserState.CONNECTED

    def test_start_talking_nonexistent_user_raises(self, channel):
        with pytest.raises(UserNotFoundError):
            channel.start_talking("Nobody")

    def test_talking_on_closed_channel_raises(self, channel_with_users):
        channel_with_users.close()
        with pytest.raises(ChannelClosedError):
            channel_with_users.start_talking("Alice")

    def test_talking_is_logged(self, channel_with_users):
        channel_with_users.start_talking("Alice")
        assert any("Alice" in e and "talking" in e for e in channel_with_users.event_log)


# ══════════════════════════════════════════════════════════════════════════════
# 6. MESSAGE TRANSMISSION
# ══════════════════════════════════════════════════════════════════════════════

class TestMessageTransmission:

    def test_user_can_transmit_message(self, channel_with_users):
        msg = channel_with_users.transmit("Alice", "Test channel, copy?")
        assert msg is not None

    def test_message_is_logged(self, channel_with_users):
        channel_with_users.transmit("Alice", "Hello")
        assert channel_with_users.message_count == 1

    def test_message_has_correct_sender(self, channel_with_users):
        msg = channel_with_users.transmit("Bob", "Radio check")
        assert msg.sender == "Bob"

    def test_message_has_correct_content(self, channel_with_users):
        msg = channel_with_users.transmit("Alice", "Go for launch")
        assert msg.content == "Go for launch"

    def test_message_has_channel_id(self, channel_with_users):
        msg = channel_with_users.transmit("Alice", "Test")
        assert msg.channel_id == channel_with_users.channel_id

    def test_message_has_timestamp(self, channel_with_users):
        before = time.time()
        msg = channel_with_users.transmit("Alice", "Test")
        after = time.time()
        assert before <= msg.timestamp <= after

    def test_message_has_unique_id(self, channel_with_users):
        msg1 = channel_with_users.transmit("Alice", "First")
        msg2 = channel_with_users.transmit("Bob", "Second")
        assert msg1.id != msg2.id

    def test_muted_user_cannot_transmit(self, channel_with_users):
        channel_with_users.mute("Alice")
        with pytest.raises(UserMutedError):
            channel_with_users.transmit("Alice", "Can you hear me?")

    def test_nonexistent_user_cannot_transmit(self, channel):
        with pytest.raises(UserNotFoundError):
            channel.transmit("Ghost", "Hello?")

    def test_empty_message_raises(self, channel_with_users):
        with pytest.raises(ValueError):
            channel_with_users.transmit("Alice", "")

    def test_whitespace_message_raises(self, channel_with_users):
        with pytest.raises(ValueError):
            channel_with_users.transmit("Alice", "   ")

    def test_message_at_max_length_is_accepted(self, channel_with_users):
        msg = channel_with_users.transmit("Alice", "x" * IntercomChannel.MAX_MESSAGE_LENGTH)
        assert msg is not None

    def test_message_exceeding_max_length_raises(self, channel_with_users):
        with pytest.raises(MessageTooLongError):
            channel_with_users.transmit("Alice", "x" * (IntercomChannel.MAX_MESSAGE_LENGTH + 1))

    def test_transmit_on_closed_channel_raises(self, channel_with_users):
        channel_with_users.close()
        with pytest.raises(ChannelClosedError):
            channel_with_users.transmit("Alice", "Hello?")

    def test_get_messages_from_sender(self, channel_with_users):
        channel_with_users.transmit("Alice", "First")
        channel_with_users.transmit("Bob", "Not Alice")
        channel_with_users.transmit("Alice", "Second")
        alice_msgs = channel_with_users.get_messages_from("Alice")
        assert len(alice_msgs) == 2
        assert all(m.sender == "Alice" for m in alice_msgs)

    def test_multiple_messages_accumulate(self, channel_with_users):
        for i in range(5):
            channel_with_users.transmit("Alice", f"Message {i}")
        assert channel_with_users.message_count == 5

    def test_talking_user_can_still_transmit_text(self, channel_with_users):
        channel_with_users.start_talking("Alice")
        msg = channel_with_users.transmit("Alice", "Transmitting now")
        assert msg is not None


# ══════════════════════════════════════════════════════════════════════════════
# 7. CHANNEL LIFECYCLE (LOCK / UNLOCK / CLOSE)
# ══════════════════════════════════════════════════════════════════════════════

class TestChannelLifecycle:

    def test_lock_sets_state(self, channel):
        channel.lock()
        assert channel.state == ChannelState.LOCKED

    def test_unlock_returns_to_active(self, channel):
        channel.lock()
        channel.unlock()
        assert channel.state == ChannelState.ACTIVE

    def test_existing_users_can_operate_in_locked_channel(self, channel_with_users):
        channel_with_users.lock()
        channel_with_users.transmit("Alice", "Still here")  # Should not raise
        assert channel_with_users.message_count == 1

    def test_new_user_cannot_join_locked_channel(self, channel):
        channel.lock()
        with pytest.raises(ChannelLockedError):
            channel.join("Newcomer")

    def test_new_user_can_join_after_unlock(self, channel):
        channel.lock()
        channel.unlock()
        channel.join("Newcomer")  # Should not raise
        assert channel.is_user_connected("Newcomer")

    def test_close_sets_state(self, channel):
        channel.close()
        assert channel.state == ChannelState.CLOSED

    def test_close_removes_all_users(self, channel_with_users):
        channel_with_users.close()
        assert channel_with_users.user_count == 0

    def test_close_is_permanent(self, channel):
        channel.close()
        with pytest.raises(ChannelClosedError):
            channel.lock()

    def test_lock_on_closed_channel_raises(self, channel):
        channel.close()
        with pytest.raises(ChannelClosedError):
            channel.lock()

    def test_unlock_on_closed_channel_raises(self, channel):
        channel.close()
        with pytest.raises(ChannelClosedError):
            channel.unlock()

    def test_close_is_logged(self, channel):
        channel.close()
        assert any("closed" in e for e in channel.event_log)

    def test_lock_on_already_locked_channel(self, channel):
        channel.lock()
        channel.lock()  # Should not raise — idempotent
        assert channel.state == ChannelState.LOCKED


# ══════════════════════════════════════════════════════════════════════════════
# 8. AUDIT / EVENT LOG
# ══════════════════════════════════════════════════════════════════════════════

class TestAuditLog:

    def test_event_log_is_not_empty_after_creation(self, channel):
        assert len(channel.event_log) > 0

    def test_event_log_grows_with_actions(self, channel):
        initial = len(channel.event_log)
        channel.join("Alice")
        assert len(channel.event_log) > initial

    def test_event_log_returns_copy(self, channel):
        log = channel.event_log
        log.append("Injected entry")
        assert "Injected entry" not in channel.event_log

    def test_messages_returns_copy(self, channel_with_users):
        channel_with_users.transmit("Alice", "Hello")
        msgs = channel_with_users.messages
        msgs.clear()
        assert channel_with_users.message_count == 1

    def test_users_returns_copy(self, channel_with_users):
        snapshot = channel_with_users.users
        snapshot.clear()
        assert channel_with_users.user_count == 3


# ══════════════════════════════════════════════════════════════════════════════
# 9. INTEGRATION / REALISTIC WORKFLOW TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegrationWorkflows:

    def test_full_broadcast_workflow(self):
        """Simulates a realistic mission-control communication sequence."""
        ch = IntercomChannel(name="Mission Control", max_users=10)

        # Crew joins
        ch.join("FlightDirector")
        ch.join("CAPCOM")
        ch.join("Engineer")

        # Director holds the floor and transmits a go/no-go call
        ch.start_talking("FlightDirector")
        msg = ch.transmit("FlightDirector", "All stations, go/no-go for launch. CAPCOM?")
        ch.stop_talking("FlightDirector")

        # CAPCOM responds
        ch.start_talking("CAPCOM")
        ch.transmit("CAPCOM", "Go, Flight.")
        ch.stop_talking("CAPCOM")

        # Engineer is muted (background noise)
        ch.mute("Engineer")
        with pytest.raises(UserMutedError):
            ch.transmit("Engineer", "I have a concern...")

        # Engineer unmuted to speak
        ch.unmute("Engineer")
        ch.transmit("Engineer", "All systems nominal.")

        # Lock channel before launch (no new observers)
        ch.lock()
        with pytest.raises(ChannelLockedError):
            ch.join("Observer")

        assert ch.message_count == 3  # muted transmit raises before logging
        assert ch.user_count == 3

    def test_channel_capacity_cycle(self):
        """Users fill, leave, and new user takes the freed slot."""
        ch = IntercomChannel(name="Tight", max_users=2)
        ch.join("Alice")
        ch.join("Bob")

        with pytest.raises(CapacityExceededError):
            ch.join("Charlie")

        ch.leave("Alice")
        ch.join("Charlie")
        assert ch.is_user_connected("Charlie")
        assert not ch.is_user_connected("Alice")

    def test_floor_handoff_sequence(self):
        """Simulates a clean floor handoff between three users."""
        ch = IntercomChannel(name="Handoff Test", max_users=5)
        for name in ["Alpha", "Bravo", "Charlie"]:
            ch.join(name)

        ch.start_talking("Alpha")
        ch.stop_talking("Alpha")
        ch.start_talking("Bravo")
        ch.stop_talking("Bravo")
        ch.start_talking("Charlie")
        ch.stop_talking("Charlie")

        for name in ["Alpha", "Bravo", "Charlie"]:
            assert ch.get_user(name).state == UserState.CONNECTED

    def test_message_history_integrity(self):
        """Ensures message ordering and attribution are correct."""
        ch = IntercomChannel(name="Log Test", max_users=5)
        ch.join("Alice")
        ch.join("Bob")

        ch.transmit("Alice", "First")
        ch.transmit("Bob", "Second")
        ch.transmit("Alice", "Third")

        msgs = ch.messages
        assert msgs[0].sender == "Alice"
        assert msgs[1].sender == "Bob"
        assert msgs[2].sender == "Alice"
        assert msgs[0].timestamp <= msgs[1].timestamp <= msgs[2].timestamp

    def test_post_close_state_is_clean(self):
        """After close, user count is zero and further ops raise."""
        ch = IntercomChannel(name="Closing", max_users=5)
        ch.join("Alice")
        ch.join("Bob")
        ch.close()

        assert ch.user_count == 0
        assert ch.state == ChannelState.CLOSED

        with pytest.raises(ChannelClosedError):
            ch.join("Anyone")
        with pytest.raises(ChannelClosedError):
            ch.transmit("Alice", "Hello?")

    def test_repr_is_informative(self):
        ch = IntercomChannel(name="Debug", max_users=3)
        ch.join("Alice")
        r = repr(ch)
        assert "Debug" in r
        assert "ACTIVE" in r
        assert "1/3" in r
