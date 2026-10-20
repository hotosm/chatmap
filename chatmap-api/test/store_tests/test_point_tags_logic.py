from datetime import UTC, datetime

from db import MapKey, PointTagChange
from store.point_tags_store import REMOVE, SET, tags_from_changes

STATUS = MapKey(id="k-status", key="status", single=True, closed=True)
TAG = MapKey(id="k-tag", key="tag", single=False, closed=False)


def _at(time):
    return datetime.fromisoformat(f"2026-10-06T{time}:00+00:00").astimezone(UTC)


def _status(time, value_id=None, action=SET, source="manual"):
    return PointTagChange(
        point_id="p-1", key_id=STATUS.id, action=action, value_id=value_id, value=value_id,
        happened_at=_at(time), source=source,
    )


def _tag(time, value, action=SET):
    return PointTagChange(point_id="p-1", key_id=TAG.id, action=action, value=value, happened_at=_at(time), source="manual")


def _newest_first(*changes):
    return sorted(changes, key=lambda change: change.happened_at, reverse=True)


def _status_of(*changes):
    return [(tag.value_id, tag.since, tag.confirmed_at) for tag in tags_from_changes(_newest_first(*changes), STATUS)]


# ---- a key with one value: the status ----

def test_a_point_without_changes_has_no_status():
    assert _status_of() == []


def test_a_confirmation_keeps_since_and_moves_confirmed_at():
    # 08:30 group A: "the center opened"; 11:00 group B: "still open"
    assert _status_of(_status("08:30", "open"), _status("11:00", "open")) == [("open", _at("08:30"), _at("11:00"))]


def test_a_message_linked_late_does_not_override_a_newer_one():
    # At 11:30 someone links a message of 07:50: "it is closed"
    changes = (_status("08:30", "open"), _status("11:00", "open"), _status("07:50", "closed"))

    assert _status_of(*changes) == [("open", _at("08:30"), _at("11:00"))]


def test_a_new_value_starts_over_since():
    assert _status_of(_status("08:30", "open"), _status("12:00", "closed")) == [
        ("closed", _at("12:00"), _at("12:00")),
    ]


def test_since_counts_from_the_first_of_the_last_run_of_the_same_value():
    changes = (_status("08:00", "open"), _status("09:00", "closed"), _status("10:00", "open"), _status("11:00", "open"))

    assert _status_of(*changes) == [("open", _at("10:00"), _at("11:00"))]


def test_removing_the_status_leaves_the_point_without_one():
    assert _status_of(_status("08:30", "open"), _status("09:00", action=REMOVE)) == []


def test_a_status_given_after_removing_it_starts_over():
    changes = (_status("08:30", "open"), _status("09:00", action=REMOVE), _status("10:00", "open"))

    assert _status_of(*changes) == [("open", _at("10:00"), _at("10:00"))]


def test_a_change_whose_value_was_removed_is_skipped():
    # The value of 11:00 was removed later, so its changes kept only the name
    removed = _status("11:00")
    removed.value = "Closed"

    assert _status_of(_status("08:30", "open"), removed) == [("open", _at("08:30"), _at("08:30"))]


def test_the_tag_keeps_how_and_by_whom_the_last_change_came():
    first = _status("08:30", "open", source="message")
    last = _status("11:00", "open", source="manual")
    last.user_id = "user-1"

    [tag] = tags_from_changes(_newest_first(first, last), STATUS)

    assert (tag.source, tag.user_id, tag.single, tag.value) == ("manual", "user-1", True, None)


# ---- a key with many values: free tags ----

def _tags_of(*changes):
    return sorted((tag.value, tag.since, tag.confirmed_at) for tag in tags_from_changes(_newest_first(*changes), TAG))


def test_each_free_tag_has_its_own_history():
    changes = (_tag("08:00", "guard"), _tag("09:00", "pediatrics"), _tag("10:00", "guard"))

    assert _tags_of(*changes) == [("guard", _at("08:00"), _at("10:00")), ("pediatrics", _at("09:00"), _at("09:00"))]


def test_removing_a_free_tag_keeps_the_others():
    changes = (_tag("08:00", "guard"), _tag("09:00", "pediatrics"), _tag("16:00", "pediatrics", REMOVE))

    assert _tags_of(*changes) == [("guard", _at("08:00"), _at("08:00"))]
