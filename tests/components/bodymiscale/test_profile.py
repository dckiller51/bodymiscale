"""Tests for bodymiscale profile.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from custom_components.bodymiscale.const import (
    CONF_NEAREST_TOLERANCE,
    CONF_NOTIFY_WEIGHT_MAX,
    CONF_NOTIFY_WEIGHT_MIN,
    DOMAIN,
    EVENT_MOBILE_APP_NOTIFICATION_ACTION,
    HANDLERS,
    PROFILE_METHOD_NEAREST,
)
from custom_components.bodymiscale.profile import (
    NearestWeightFilter,
    NotificationCoordinator,
    NotificationFilter,
    build_profile_filter,
)

# ===========================================================================
# NearestWeightFilter
# ===========================================================================


def _make_handler_with_weight(name: str, current_weight: float | None) -> MagicMock:
    h = MagicMock()
    h.config = {CONF_NAME: name}
    h.current_weight = current_weight
    return h


def _setup_hass_handlers(hass: HomeAssistant, handlers: dict) -> None:
    hass.data[DOMAIN] = {HANDLERS: handlers}


async def test_nearest_accepts_when_closest(hass: HomeAssistant) -> None:
    """NearestWeightFilter accepts the user whose stored weight is nearest."""
    handlers = {
        "alice": _make_handler_with_weight("Alice", 65.0),
        "bob": _make_handler_with_weight("Bob", 80.0),
    }
    _setup_hass_handlers(hass, handlers)

    f = NearestWeightFilter()
    config = {CONF_NAME: "Alice", CONF_NEAREST_TOLERANCE: 10.0}
    assert f.accepts(hass, config, 66.0) is True


async def test_nearest_rejects_when_not_closest(hass: HomeAssistant) -> None:
    """NearestWeightFilter rejects if another user is closer."""
    handlers = {
        "alice": _make_handler_with_weight("Alice", 65.0),
        "bob": _make_handler_with_weight("Bob", 80.0),
    }
    _setup_hass_handlers(hass, handlers)

    f = NearestWeightFilter()
    config = {CONF_NAME: "Alice", CONF_NEAREST_TOLERANCE: 20.0}
    assert f.accepts(hass, config, 78.0) is False


async def test_nearest_rejects_outside_tolerance(hass: HomeAssistant) -> None:
    """NearestWeightFilter rejects when best distance exceeds tolerance."""
    handlers = {
        "alice": _make_handler_with_weight("Alice", 65.0),
    }
    _setup_hass_handlers(hass, handlers)

    f = NearestWeightFilter()
    config = {CONF_NAME: "Alice", CONF_NEAREST_TOLERANCE: 3.0}
    assert f.accepts(hass, config, 70.0) is False


async def test_nearest_rejects_missing_name(hass: HomeAssistant) -> None:
    """NearestWeightFilter rejects when CONF_NAME is absent."""
    _setup_hass_handlers(hass, {})
    f = NearestWeightFilter()
    assert f.accepts(hass, {}, 65.0) is False


async def test_nearest_rejects_no_current_weight(hass: HomeAssistant) -> None:
    """NearestWeightFilter rejects when no handler has a current weight."""
    handlers = {
        "alice": _make_handler_with_weight("Alice", None),
    }
    _setup_hass_handlers(hass, handlers)

    f = NearestWeightFilter()
    config = {CONF_NAME: "Alice"}
    assert f.accepts(hass, config, 65.0) is False


async def test_nearest_rejects_user_not_in_handlers(hass: HomeAssistant) -> None:
    """NearestWeightFilter rejects when user is not found in any handler."""
    handlers = {
        "bob": _make_handler_with_weight("Bob", 80.0),
    }
    _setup_hass_handlers(hass, handlers)

    f = NearestWeightFilter()
    config = {CONF_NAME: "Alice", CONF_NEAREST_TOLERANCE: 10.0}
    assert f.accepts(hass, config, 65.0) is False


async def test_nearest_tie_broken_alphabetically(hass: HomeAssistant) -> None:
    """On equal distance, NearestWeightFilter accepts the alphabetically first user."""
    handlers = {
        "alice": _make_handler_with_weight("Alice", 70.0),
        "bob": _make_handler_with_weight("Bob", 70.0),
    }
    _setup_hass_handlers(hass, handlers)

    f_alice = NearestWeightFilter()
    f_bob = NearestWeightFilter()

    assert (
        f_alice.accepts(hass, {CONF_NAME: "Alice", CONF_NEAREST_TOLERANCE: 5.0}, 70.0)
        is True
    )
    assert (
        f_bob.accepts(hass, {CONF_NAME: "Bob", CONF_NEAREST_TOLERANCE: 5.0}, 70.0)
        is False
    )


async def test_nearest_default_tolerance_is_5(hass: HomeAssistant) -> None:
    """NearestWeightFilter uses 5 kg as default tolerance when not configured."""
    handlers = {
        "alice": _make_handler_with_weight("Alice", 65.0),
    }
    _setup_hass_handlers(hass, handlers)

    f = NearestWeightFilter()
    config = {CONF_NAME: "Alice"}

    assert f.accepts(hass, config, 69.0) is True
    assert f.accepts(hass, config, 71.0) is False


async def test_nearest_case_insensitive_name_match(hass: HomeAssistant) -> None:
    """NearestWeightFilter matches names case-insensitively."""
    handlers = {
        "alice": _make_handler_with_weight("ALICE", 65.0),
    }
    _setup_hass_handlers(hass, handlers)

    f = NearestWeightFilter()
    config = {CONF_NAME: "alice", CONF_NEAREST_TOLERANCE: 5.0}
    assert f.accepts(hass, config, 65.0) is True


# ===========================================================================
# build_profile_filter
# ===========================================================================


def test_build_profile_filter_nearest() -> None:
    """build_profile_filter with method=nearest returns NearestWeightFilter."""
    f = build_profile_filter({"profile_method": PROFILE_METHOD_NEAREST})
    assert isinstance(f, NearestWeightFilter)


# ===========================================================================
# NotificationCoordinator — register / unregister
# ===========================================================================


def _make_coordinator(hass: HomeAssistant) -> NotificationCoordinator:
    return NotificationCoordinator(hass)


def _make_handler_mock(
    config: dict | None = None,
    entry_id: str = "entry_1",
) -> MagicMock:
    handler = MagicMock()
    handler.config = config or {}
    handler.accept_pending_measurement = MagicMock()
    return handler


def _make_filter() -> NotificationFilter:
    return NotificationFilter()


async def test_coordinator_register_and_has_entries(hass: HomeAssistant) -> None:
    """has_entries() must return True after register()."""
    coord = _make_coordinator(hass)
    notify_filter = _make_filter()
    handler = _make_handler_mock()

    coord.register(
        entry_id="entry_1",
        user_name="Alice",
        notify_filter=notify_filter,
        device_id="device_abc",
        handler=handler,
    )
    assert coord.has_entries() is True
    coord.unload()


async def test_coordinator_unregister_removes_entry(hass: HomeAssistant) -> None:
    """unregister() must remove the entry; has_entries() returns False when empty."""
    coord = _make_coordinator(hass)
    coord.register(
        entry_id="entry_1",
        user_name="Alice",
        notify_filter=_make_filter(),
        device_id="device_abc",
        handler=_make_handler_mock(),
    )

    coord.unregister("entry_1")
    assert coord.has_entries() is False
    coord.unload()


async def test_coordinator_unregister_unknown_id_is_noop(hass: HomeAssistant) -> None:
    """unregister() with an unknown entry_id must not raise."""
    coord = _make_coordinator(hass)
    coord.unregister("does_not_exist")
    coord.unload()


async def test_coordinator_unload_clears_all_entries(hass: HomeAssistant) -> None:
    """unload() must remove all entries and cancel the event listener."""
    coord = _make_coordinator(hass)
    coord.register(
        entry_id="e1",
        user_name="Alice",
        notify_filter=_make_filter(),
        device_id="d1",
        handler=_make_handler_mock(),
    )
    coord.register(
        entry_id="e2",
        user_name="Bob",
        notify_filter=_make_filter(),
        device_id="d2",
        handler=_make_handler_mock(),
    )
    coord.unload()
    assert coord.has_entries() is False


# ===========================================================================
# NotificationCoordinator — event routing
# ===========================================================================


async def test_on_notification_action_confirms_matching_user(
    hass: HomeAssistant,
) -> None:
    """mobile_app_notification_action with matching name must confirm the filter."""
    coord = _make_coordinator(hass)
    notify_filter = _make_filter()
    handler = _make_handler_mock()

    coord.register(
        entry_id="e1",
        user_name="Alice",
        notify_filter=notify_filter,
        device_id="d1",
        handler=handler,
    )

    hass.bus.async_fire(
        EVENT_MOBILE_APP_NOTIFICATION_ACTION,
        {"action": "ALICE"},
    )
    await hass.async_block_till_done()

    assert notify_filter.is_confirmed() is True
    handler.accept_pending_measurement.assert_called_once()
    coord.unload()


async def test_on_notification_action_case_insensitive(hass: HomeAssistant) -> None:
    """Action matching must be case-insensitive."""
    coord = _make_coordinator(hass)
    notify_filter = _make_filter()
    handler = _make_handler_mock()

    coord.register(
        entry_id="e1",
        user_name="Alice",
        notify_filter=notify_filter,
        device_id="d1",
        handler=handler,
    )

    hass.bus.async_fire(
        EVENT_MOBILE_APP_NOTIFICATION_ACTION,
        {"action": "alice"},
    )
    await hass.async_block_till_done()

    assert notify_filter.is_confirmed() is True
    coord.unload()


async def test_on_notification_action_ignores_unrelated_action(
    hass: HomeAssistant,
) -> None:
    """Action that does not match any registered user must be silently ignored."""
    coord = _make_coordinator(hass)
    notify_filter = _make_filter()
    handler = _make_handler_mock()

    coord.register(
        entry_id="e1",
        user_name="Alice",
        notify_filter=notify_filter,
        device_id="d1",
        handler=handler,
    )

    hass.bus.async_fire(
        EVENT_MOBILE_APP_NOTIFICATION_ACTION,
        {"action": "BOB"},
    )
    await hass.async_block_till_done()

    assert notify_filter.is_confirmed() is False
    handler.accept_pending_measurement.assert_not_called()
    coord.unload()


async def test_on_notification_action_routes_to_correct_user(
    hass: HomeAssistant,
) -> None:
    """When multiple users are registered, only the tapped one is confirmed."""
    coord = _make_coordinator(hass)
    filter_alice = _make_filter()
    filter_bob = _make_filter()
    handler_alice = _make_handler_mock()
    handler_bob = _make_handler_mock()

    coord.register("e_alice", "Alice", filter_alice, "device_shared", handler_alice)
    coord.register("e_bob", "Bob", filter_bob, "device_shared", handler_bob)

    hass.bus.async_fire(
        EVENT_MOBILE_APP_NOTIFICATION_ACTION,
        {"action": "BOB"},
    )
    await hass.async_block_till_done()

    assert filter_bob.is_confirmed() is True
    assert filter_alice.is_confirmed() is False
    handler_bob.accept_pending_measurement.assert_called_once()
    handler_alice.accept_pending_measurement.assert_not_called()
    coord.unload()


# ===========================================================================
# NotificationCoordinator — async_notify weight pre-filter
# ===========================================================================


async def test_async_notify_skips_out_of_weight_range(hass: HomeAssistant) -> None:
    """async_notify must not call notify service for users outside their weight range."""
    coord = _make_coordinator(hass)
    handler = _make_handler_mock(
        config={
            CONF_NOTIFY_WEIGHT_MIN: 50.0,
            CONF_NOTIFY_WEIGHT_MAX: 70.0,
        }
    )

    coord.register("e1", "Alice", _make_filter(), "d1", handler)

    with patch(
        "homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock
    ) as mock_call:
        await coord.async_notify(80.0)

    mock_call.assert_not_called()
    coord.unload()


async def test_async_notify_calls_service_for_in_range_user(
    hass: HomeAssistant,
) -> None:
    """async_notify must call the notify service for users within their weight range."""
    coord = _make_coordinator(hass)
    handler = _make_handler_mock(
        config={
            CONF_NOTIFY_WEIGHT_MIN: 50.0,
            CONF_NOTIFY_WEIGHT_MAX: 80.0,
        }
    )

    coord.register("e1", "Alice", _make_filter(), "d1", handler)

    with (
        patch.object(
            coord,
            "_resolve_notify_service",
            new=AsyncMock(return_value="mobile_app_d1"),
        ),
        patch(
            "homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock
        ) as mock_call,
    ):
        await coord.async_notify(65.0)

    mock_call.assert_called_once()
    call_args = mock_call.call_args
    assert call_args[0][0] == "notify"
    assert call_args[0][1] == "mobile_app_d1"
    coord.unload()


async def test_async_notify_no_entries_is_noop(hass: HomeAssistant) -> None:
    """async_notify with no registered entries must do nothing and not raise."""
    coord = _make_coordinator(hass)

    with patch(
        "homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock
    ) as mock_call:
        await coord.async_notify(65.0)

    mock_call.assert_not_called()
    coord.unload()


async def test_async_notify_without_weight_filter_always_sends(
    hass: HomeAssistant,
) -> None:
    """Users without weight range config must always receive the notification."""
    coord = _make_coordinator(hass)
    handler = _make_handler_mock(config={})
    coord.register("e1", "Alice", _make_filter(), "d1", handler)

    with (
        patch.object(
            coord,
            "_resolve_notify_service",
            new=AsyncMock(return_value="mobile_app_d1"),
        ),
        patch(
            "homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock
        ) as mock_call,
    ):
        await coord.async_notify(65.0)

    mock_call.assert_called_once()
    coord.unload()


async def test_async_notify_groups_users_on_same_device(hass: HomeAssistant) -> None:
    """Users on the same device must share a single notification call."""
    coord = _make_coordinator(hass)
    shared_device = "device_shared"

    coord.register(
        "e1", "Alice", _make_filter(), shared_device, _make_handler_mock(config={})
    )
    coord.register(
        "e2", "Bob", _make_filter(), shared_device, _make_handler_mock(config={})
    )

    with (
        patch.object(
            coord,
            "_resolve_notify_service",
            new=AsyncMock(return_value="mobile_app_shared"),
        ),
        patch(
            "homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock
        ) as mock_call,
    ):
        await coord.async_notify(70.0)

    assert mock_call.call_count == 1
    call_data = mock_call.call_args[0][2]
    action_titles = [a["title"] for a in call_data["data"]["actions"]]
    assert "Alice" in action_titles
    assert "Bob" in action_titles
    coord.unload()


async def test_async_notify_sends_separate_notifications_for_different_devices(
    hass: HomeAssistant,
) -> None:
    """Users on different devices must receive separate notification calls."""
    coord = _make_coordinator(hass)

    coord.register(
        "e1", "Alice", _make_filter(), "device_alice", _make_handler_mock(config={})
    )
    coord.register(
        "e2", "Bob", _make_filter(), "device_bob", _make_handler_mock(config={})
    )

    async def mock_resolve(device_id: str) -> str:
        return f"mobile_app_{device_id}"

    with (
        patch.object(coord, "_resolve_notify_service", new=mock_resolve),
        patch(
            "homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock
        ) as mock_call,
    ):
        await coord.async_notify(70.0)

    assert mock_call.call_count == 2
    coord.unload()


async def test_async_notify_no_users_after_weight_filter(hass: HomeAssistant) -> None:
    """async_notify logs and returns early when all users fail weight pre-filter."""
    coord = _make_coordinator(hass)
    handler = MagicMock()
    handler.config = {CONF_NOTIFY_WEIGHT_MIN: 60.0, CONF_NOTIFY_WEIGHT_MAX: 70.0}

    coord.register("e1", "Alice", NotificationFilter(), "d1", handler)

    with patch(
        "homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock
    ) as mock_call:
        await coord.async_notify(80.0)

    mock_call.assert_not_called()
    coord.unload()


async def test_async_notify_resolve_returns_none_skips_device(
    hass: HomeAssistant,
) -> None:
    """async_notify skips a device when _resolve_notify_service returns None."""
    coord = _make_coordinator(hass)
    handler = MagicMock()
    handler.config = {}

    coord.register("e1", "Alice", NotificationFilter(), "d1", handler)

    with (
        patch.object(
            coord, "_resolve_notify_service", new=AsyncMock(return_value=None)
        ),
        patch(
            "homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock
        ) as mock_call,
    ):
        await coord.async_notify(65.0)

    mock_call.assert_not_called()
    coord.unload()


async def test_async_notify_message_format_error_falls_back(
    hass: HomeAssistant,
) -> None:
    """async_notify falls back to default message when format fails."""
    coord = _make_coordinator(hass)
    handler = MagicMock()
    handler.config = {}

    coord.register("e1", "Alice", NotificationFilter(), "d1", handler)

    bad_translations = {"weighing_title": "Title", "weighing_message": "{bad_key}"}

    with (
        patch.object(
            coord,
            "_get_notify_translations",
            new=AsyncMock(return_value=bad_translations),
        ),
        patch.object(
            coord,
            "_resolve_notify_service",
            new=AsyncMock(return_value="mobile_app_d1"),
        ),
        patch(
            "homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock
        ) as mock_call,
    ):
        await coord.async_notify(65.0)

    mock_call.assert_called_once()
    call_data = mock_call.call_args[0][2]
    assert "65" in call_data["message"]
    coord.unload()


# ===========================================================================
# _resolve_notify_service — all 3 strategies
# ===========================================================================


def _make_device(
    name: str = "Smartphone Alice",
    identifiers: set | None = None,
) -> MagicMock:
    device = MagicMock()
    device.name = name
    device.identifiers = identifiers or {("mobile_app", "alice_phone_id")}
    return device


async def test_resolve_device_not_in_registry(hass: HomeAssistant) -> None:
    """Must return None and log a warning when device_id is unknown."""
    coord = _make_coordinator(hass)

    with patch("custom_components.bodymiscale.profile.dr.async_get") as mock_dev_reg:
        mock_dev_reg.return_value.async_get.return_value = None
        result = await coord._resolve_notify_service("unknown_device_id")

    assert result is None
    coord.unload()


async def test_resolve_strategy1_exact_match(hass: HomeAssistant) -> None:
    """Strategy 1: mobile_app identifier builds service name directly."""
    coord = _make_coordinator(hass)
    device = _make_device(identifiers={("mobile_app", "smartphone_alice")})

    with (
        patch("custom_components.bodymiscale.profile.dr.async_get") as mock_dev_reg,
        patch("custom_components.bodymiscale.profile.er.async_get"),
    ):
        mock_dev_reg.return_value.async_get.return_value = device
        hass.services._services.setdefault("notify", {})
        hass.services._services["notify"]["mobile_app_smartphone_alice"] = MagicMock()

        result = await coord._resolve_notify_service("device_123")

    assert result == "mobile_app_smartphone_alice"
    coord.unload()


async def test_resolve_strategy1_case_insensitive(hass: HomeAssistant) -> None:
    """Strategy 1: case-insensitive fallback when exact candidate not found."""
    coord = _make_coordinator(hass)
    device = _make_device(identifiers={("mobile_app", "SmartphoneAlice")})

    registered_services = {"mobile_app_smartphonealice": MagicMock()}

    def fake_has_service(self_reg, domain: str, service: str) -> bool:
        return service in registered_services

    def fake_async_services(self_reg):
        return {"notify": registered_services}

    with (
        patch("custom_components.bodymiscale.profile.dr.async_get") as mock_dev_reg,
        patch("custom_components.bodymiscale.profile.er.async_get"),
        patch(
            "homeassistant.core.ServiceRegistry.has_service",
            fake_has_service,
        ),
        patch(
            "homeassistant.core.ServiceRegistry.async_services",
            fake_async_services,
        ),
    ):
        mock_dev_reg.return_value.async_get.return_value = device
        result = await coord._resolve_notify_service("device_123")

    assert result == "mobile_app_smartphonealice"
    coord.unload()


async def test_resolve_strategy2_entity_unique_id(hass: HomeAssistant) -> None:
    """Strategy 2: match notify service via entity unique_id prefix."""
    coord = _make_coordinator(hass)
    device = _make_device(identifiers={("other_domain", "irrelevant")})

    mock_entry = MagicMock()
    mock_entry.unique_id = "abc123_battery_level"

    with (
        patch("custom_components.bodymiscale.profile.dr.async_get") as mock_dev_reg,
        patch("custom_components.bodymiscale.profile.er.async_get") as mock_ent_reg,
    ):
        mock_dev_reg.return_value.async_get.return_value = device
        mock_ent_reg.return_value.entities.get_entries_for_device_id.return_value = [
            mock_entry
        ]
        hass.services._services.setdefault("notify", {})
        hass.services._services["notify"]["mobile_app_abc123"] = MagicMock()

        result = await coord._resolve_notify_service("device_123")

    assert result == "mobile_app_abc123"
    coord.unload()


async def test_resolve_strategy3_fuzzy_ascii_name(hass: HomeAssistant) -> None:
    """Strategy 3: fuzzy match on normalized ASCII device name."""
    coord = _make_coordinator(hass)
    device = _make_device(
        name="Smartphone Alice",
        identifiers={("other_domain", "irrelevant")},
    )

    with (
        patch("custom_components.bodymiscale.profile.dr.async_get") as mock_dev_reg,
        patch("custom_components.bodymiscale.profile.er.async_get") as mock_ent_reg,
    ):
        mock_dev_reg.return_value.async_get.return_value = device
        mock_ent_reg.return_value.entities.get_entries_for_device_id.return_value = []
        hass.services._services.setdefault("notify", {})
        hass.services._services["notify"]["mobile_app_smartphone_alice"] = MagicMock()

        result = await coord._resolve_notify_service("device_123")

    assert result == "mobile_app_smartphone_alice"
    coord.unload()


async def test_resolve_strategy3_fuzzy_accented_name(hass: HomeAssistant) -> None:
    """Strategy 3: accented display name must match ASCII service name after NFKD normalization."""
    coord = _make_coordinator(hass)
    device = _make_device(
        name="Smartphone Aurélien",
        identifiers={("other_domain", "irrelevant")},
    )

    with (
        patch("custom_components.bodymiscale.profile.dr.async_get") as mock_dev_reg,
        patch("custom_components.bodymiscale.profile.er.async_get") as mock_ent_reg,
    ):
        mock_dev_reg.return_value.async_get.return_value = device
        mock_ent_reg.return_value.entities.get_entries_for_device_id.return_value = []
        hass.services._services.setdefault("notify", {})
        hass.services._services["notify"]["mobile_app_smartphone_aurelien"] = (
            MagicMock()
        )

        result = await coord._resolve_notify_service("device_123")

    assert result == "mobile_app_smartphone_aurelien"
    coord.unload()


async def test_resolve_all_strategies_fail_returns_none(hass: HomeAssistant) -> None:
    """Must return None when no strategy succeeds and log a warning."""
    coord = _make_coordinator(hass)
    device = _make_device(
        name="Unknown Device XYZ",
        identifiers={("other_domain", "irrelevant")},
    )

    with (
        patch("custom_components.bodymiscale.profile.dr.async_get") as mock_dev_reg,
        patch("custom_components.bodymiscale.profile.er.async_get") as mock_ent_reg,
    ):
        mock_dev_reg.return_value.async_get.return_value = device
        mock_ent_reg.return_value.entities.get_entries_for_device_id.return_value = []
        hass.services._services.setdefault("notify", {})

        result = await coord._resolve_notify_service("device_123")

    assert result is None
    coord.unload()


# ===========================================================================
# _get_notify_translations
# ===========================================================================


async def test_get_notify_translations_falls_back_to_en(hass: HomeAssistant) -> None:
    """_get_notify_translations falls back to 'en' when primary language fails."""
    coord = _make_coordinator(hass)

    hass.config.language = "xx"

    translations = await coord._get_notify_translations("xx")
    assert isinstance(translations, dict)
    coord.unload()


async def test_get_notify_translations_handles_corrupt_file(
    hass: HomeAssistant,
) -> None:
    """_get_notify_translations returns empty dict when JSON parsing fails."""
    coord = _make_coordinator(hass)

    with patch("builtins.open", side_effect=Exception("corrupt")):
        translations = await coord._get_notify_translations("en")

    assert translations == {}
    coord.unload()


async def test_get_notify_translations_returns_empty_for_missing_common(
    hass: HomeAssistant,
) -> None:
    """_get_notify_translations returns {} when 'common' key is absent."""
    coord = _make_coordinator(hass)

    fake_json = '{"other_key": {}}'
    with patch("builtins.open", mock_open := MagicMock()):
        mock_open.return_value.__enter__.return_value.read.return_value = fake_json
        with patch("json.load", return_value={"other_key": {}}):
            translations = await coord._get_notify_translations("zz")

    assert translations == {}
    coord.unload()


async def test_get_notify_translations_falls_back_to_english(
    hass: HomeAssistant,
) -> None:
    """_get_notify_translations must return English keys when language file is absent."""
    coord = _make_coordinator(hass)

    import os

    original_exists = os.path.exists

    def fake_exists(path: str) -> bool:
        if path.endswith("zz.json"):
            return False
        return original_exists(path)

    with patch("os.path.exists", side_effect=fake_exists):
        result = await coord._get_notify_translations("zz")

    assert isinstance(result, dict)
    coord.unload()
