"""Profile identification strategies for bodymiscale.

Four strategies:

  NONE   (method 4 — manual / no filter)
  ID     (method 1 — numeric profile ID from scale)
  WEIGHT (method 2 — weight range [min, max[)
  NOTIFY (method 3 — interactive push notification to mobile device)

For NOTIFY: when a weight change occurs the integration's
NotificationCoordinator sends an interactive push notification to the
configured mobile device.  The user taps their name; HA fires the standard
``mobile_app_notification_action`` event.  The coordinator routes the
confirmation to the matching NotificationFilter.
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, cast

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_PROFILE_ID,
    CONF_PROFILE_METHOD,
    CONF_SENSOR_PROFILE_ID,
    CONF_WEIGHT_MAX,
    CONF_WEIGHT_MIN,
    NOTIFICATION_TAG,
    PROFILE_METHOD_ID,
    PROFILE_METHOD_NONE,
    PROFILE_METHOD_NOTIFY,
    PROFILE_METHOD_WEIGHT,
)

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class ProfileFilter(ABC):
    """Decides if a weight measurement belongs to the configured user.

    Called synchronously inside an HA @callback — no I/O, no awaits.
    ``hass.states`` look-ups are fine.
    """

    @abstractmethod
    def accepts(
        self, hass: HomeAssistant, config: dict[str, Any], weight: float
    ) -> bool:
        """Return True if the measurement belongs to this user."""


# ---------------------------------------------------------------------------
# Method 4: no filter (default)
# ---------------------------------------------------------------------------


class NoFilterProfile(ProfileFilter):
    """Accept all measurements regardless of sensor data."""

    def accepts(
        self, hass: HomeAssistant, config: dict[str, Any], weight: float
    ) -> bool:
        """Return True unconditionally."""
        return True


# ---------------------------------------------------------------------------
# Method 1: numeric profile ID
# ---------------------------------------------------------------------------


class ProfileIdFilter(ProfileFilter):
    """Filter measurements by profile ID from the scale sensor."""

    def accepts(
        self, hass: HomeAssistant, config: dict[str, Any], weight: float
    ) -> bool:
        """Return True if the sensor profile ID matches the configured ID."""
        sensor_entity_id: str | None = config.get(CONF_SENSOR_PROFILE_ID)
        expected_id: int | None = config.get(CONF_PROFILE_ID)

        if not sensor_entity_id or expected_id is None:
            _LOGGER.warning(
                "Profile-ID filter: missing config (sensor=%s, id=%s) — rejected",
                sensor_entity_id,
                expected_id,
            )
            return False

        state = hass.states.get(sensor_entity_id)
        if state is None:
            _LOGGER.debug(
                "Profile-ID filter: %s not found — rejected", sensor_entity_id
            )
            return False

        try:
            current_id = int(float(state.state))
        except ValueError, TypeError:
            _LOGGER.debug(
                "Profile-ID filter: state '%s' not numeric — rejected", state.state
            )
            return False

        if current_id != int(expected_id):
            _LOGGER.debug(
                "Profile-ID filter: %s=%d ≠ expected %d — rejected",
                sensor_entity_id,
                current_id,
                int(expected_id),
            )
            return False
        return True


# ---------------------------------------------------------------------------
# Method 2: weight range [min, max[
# ---------------------------------------------------------------------------


class WeightRangeFilter(ProfileFilter):
    """Filter measurements by weight range."""

    def accepts(
        self, hass: HomeAssistant, config: dict[str, Any], weight: float
    ) -> bool:
        """Return True if weight falls within the configured range."""
        w_min: float | None = config.get(CONF_WEIGHT_MIN)
        w_max: float | None = config.get(CONF_WEIGHT_MAX)

        if w_min is None or w_max is None:
            _LOGGER.warning(
                "Weight-range filter: incomplete config (min=%s, max=%s) — rejected",
                w_min,
                w_max,
            )
            return False

        if not (float(w_min) <= weight < float(w_max)):
            _LOGGER.debug(
                "Weight-range filter: %.2f kg not in [%.2f, %.2f[ — rejected",
                weight,
                w_min,
                w_max,
            )
            return False
        return True


# ---------------------------------------------------------------------------
# Method 3: interactive mobile notification
# ---------------------------------------------------------------------------


class NotificationFilter(ProfileFilter):
    """Accept a measurement once the user has tapped the notification.

    The flag is set by NotificationCoordinator.confirm() and consumed (reset)
    here on the first accepts() call that returns True.
    One tap = one accepted measurement.
    """

    def __init__(self) -> None:
        self._confirmed: bool = False

    def confirm(self) -> None:
        """Mark this filter as confirmed when the user taps their name."""
        self._confirmed = True

    def accepts(
        self, hass: HomeAssistant, config: dict[str, Any], weight: float
    ) -> bool:
        """Return True if the user has confirmed via notification."""
        if self._confirmed:
            self._confirmed = False  # consume — one tap, one measurement
            return True
        _LOGGER.debug("Notification filter: no pending confirmation — rejected")
        return False


# ---------------------------------------------------------------------------
# NotificationCoordinator — domain-level singleton
# ---------------------------------------------------------------------------


class NotificationCoordinator:
    """Sends interactive push notifications and routes action events.

    Lifecycle
    ---------
    One instance is created in async_setup_entry when the first NOTIFY entry
    is set up, and stored in hass.data[DOMAIN]["notification_coordinator"].
    It is unloaded when the last NOTIFY entry is removed.

    Flow
    ----
    1. BodyScaleMetricsHandler detects a weight change and calls
       coordinator.async_notify(weight).
    2. The coordinator sends a notification to the configured mobile device(s)
       with one action button per registered user name.
    3. The user taps their name → HA fires mobile_app_notification_action.
    4. _on_notification_action() finds the matching NotificationFilter and
       calls filter.confirm().
    5. On the next weight update (same measurement cycle), the metrics handler
       calls profile_filter.accepts() which returns True once.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        # entry_id → (user_name, NotificationFilter, device_id, handler)
        self._entries: dict[str, tuple[str, NotificationFilter, str, Any]] = {}
        self._remove_listener = hass.bus.async_listen(
            "mobile_app_notification_action",
            self._on_notification_action,
        )

    def register(
        self,
        entry_id: str,
        user_name: str,
        notify_filter: NotificationFilter,
        device_id: str,
        handler: Any,
    ) -> None:
        """Register a config entry with its metrics handler.

        The handler reference is needed so the coordinator can call
        ``handler.accept_pending_measurement()`` after the user confirms
        their identity via the interactive notification.
        """
        self._entries[entry_id] = (user_name, notify_filter, device_id, handler)
        _LOGGER.debug(
            "NotificationCoordinator: registered entry '%s' (device=%s)",
            user_name,
            device_id,
        )

    def unregister(self, entry_id: str) -> None:
        """Remove a config entry."""
        self._entries.pop(entry_id, None)

    def has_entries(self) -> bool:
        """Return True if at least one entry is still registered."""
        return bool(self._entries)

    def unload(self) -> None:
        """Remove the global event listener and clear entries."""
        self._remove_listener()
        self._entries.clear()

    async def _get_notify_translations(self, language: str) -> dict[str, Any]:
        """Load notify translations from the translation file."""
        translations_dir = os.path.join(os.path.dirname(__file__), "translations")

        for lang in (language, "en"):
            path = os.path.join(translations_dir, f"{lang}.json")
            if os.path.exists(path):
                try:

                    def _load(p: str = path) -> dict[str, Any]:
                        with open(p, encoding="utf-8") as f:
                            return cast(dict[str, Any], json.load(f))

                    data: dict[str, Any] = cast(
                        dict[str, Any], await self._hass.async_add_executor_job(_load)
                    )
                    notify: dict[str, Any] = data.get("notify", {})
                    if notify:
                        return dict(notify)
                except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
                    _LOGGER.debug("Failed to load translations for lang=%s", lang)
        return {}

    async def async_notify(self, weight: float) -> None:
        """Send an interactive notification to all registered devices.

        Users sharing a device receive a single notification listing all names.
        Users on separate devices each receive their own notification.
        """
        if not self._entries:
            return

        # Group by device_id so users on the same phone share one notification.
        by_device: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for entry_id, (name, _, device_id, _handler) in self._entries.items():
            by_device[device_id].append((entry_id, name))

        notify_t = await self._get_notify_translations(self._hass.config.language)
        title = notify_t.get("weighing_title", "Bodymiscale — Who is weighing?")
        message_tpl = notify_t.get(
            "weighing_message", "New measurement: {weight:.1f} kg"
        )

        try:
            message = message_tpl.format(weight=weight)
        except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            _LOGGER.debug("Failed to format notification message: %s", message_tpl)
            message = f"New measurement: {weight:.1f} kg"

        for device_id, entry_names in by_device.items():
            service_name = await self._resolve_notify_service(device_id)
            if service_name is None:
                _LOGGER.warning(
                    "NotificationCoordinator: cannot resolve notify service for "
                    "device_id=%s — skipping",
                    device_id,
                )
                continue

            actions = [
                {"action": name.upper(), "title": name} for _, name in entry_names
            ]

            await self._hass.services.async_call(
                "notify",
                service_name,
                {
                    "title": title,
                    "message": message,
                    "data": {
                        "tag": NOTIFICATION_TAG,
                        "actions": actions,
                        # On iOS the actions appear as buttons; on Android as
                        # inline reply options.  Both use the same format.
                    },
                },
            )
            _LOGGER.debug(
                "NotificationCoordinator: sent to %s — actions: %s",
                service_name,
                [a["title"] for a in actions],
            )

    async def _resolve_notify_service(self, device_id: str) -> str | None:
        """Return the notify service name for a mobile_app device_id.

        The mobile_app integration registers a notify service named
        ``mobile_app_<device_id>`` where <device_id> is the *internal*
        identifier set by the companion app — NOT the display name of the
        device.  This internal ID is stored as an identifier on the device
        registry entry under the "mobile_app" domain:
            device.identifiers == {("mobile_app", "<device_id>")}

        Strategy (most-reliable first):
        1. Read the "mobile_app" identifier from the device registry entry
           and build ``mobile_app_<identifier>`` → check it exists.
        2. Iterate all entities linked to the device in the entity registry
           and look for one whose entity_id starts with "sensor." and whose
           unique_id starts with "<something>_" followed by a suffix that
           matches a registered notify service.
        3. Last resort: iterate all registered notify services that start
           with "mobile_app_" and try a case-insensitive substring match
           against every identifier/name fragment of the device.
        """
        dev_reg = dr.async_get(self._hass)
        ent_reg = er.async_get(self._hass)

        device = dev_reg.async_get(device_id)
        if device is None:
            _LOGGER.warning(
                "NotificationCoordinator: device_id=%s not found in registry",
                device_id,
            )
            return None

        # ── Strategy 1: mobile_app identifier (most reliable) ────────────
        # The companion app always registers the device with an identifier
        # tuple ("mobile_app", "<internal_device_id>").
        for domain, identifier in device.identifiers:
            if domain == "mobile_app":
                candidate = f"mobile_app_{identifier}"
                if self._hass.services.has_service("notify", candidate):
                    _LOGGER.debug(
                        "NotificationCoordinator: resolved '%s' via mobile_app identifier",
                        candidate,
                    )
                    return candidate
                # The identifier might have a different casing or suffix —
                # try a case-insensitive match across all notify services.
                identifier_lower = identifier.lower()
                for svc in self._hass.services.async_services().get("notify", {}):
                    if svc.lower() == f"mobile_app_{identifier_lower}":
                        _LOGGER.debug(
                            "NotificationCoordinator: resolved '%s' via mobile_app identifier (case-insensitive)",
                            svc,
                        )
                        return svc

        # ── Strategy 2: entity registry lookup ───────────────────────────
        # Each mobile_app device has entities whose unique_id is built as
        # "<internal_device_id>_<sensor_suffix>".  The internal_device_id
        # portion is the same string used in the notify service name.
        notify_services = set(
            self._hass.services.async_services().get("notify", {}).keys()
        )
        mobile_services = {s for s in notify_services if s.startswith("mobile_app_")}

        for entry in ent_reg.entities.get_entries_for_device_id(device_id):
            unique_id: str = entry.unique_id or ""
            # unique_id format: "<device_id>_<suffix>"  e.g. "abc123_battery_level"
            for svc in mobile_services:
                # Strip "mobile_app_" prefix to get the raw device identifier
                svc_id = svc[len("mobile_app_") :]
                if unique_id.startswith(svc_id):
                    _LOGGER.debug(
                        "NotificationCoordinator: resolved '%s' via entity unique_id match",
                        svc,
                    )
                    return svc

        # ── Strategy 3: fuzzy substring match (last resort) ──────────────
        # Collect all name fragments: display name words + all identifier values.
        fragments = set()
        if device.name:
            # Normalise display name the same way the companion app does.
            normalized = device.name.strip().lower()
            for ch in (" ", "-", ".", "(", ")"):
                normalized = normalized.replace(ch, "_")
            # Remove consecutive/trailing underscores
            while "__" in normalized:
                normalized = normalized.replace("__", "_")
            normalized = normalized.strip("_")
            fragments.add(normalized)

        for _, identifier in device.identifiers:
            fragments.add(identifier.lower())

        for fragment in fragments:
            # Skip overly short fragments to avoid false positives
            if len(fragment) < 3:
                continue
            for svc in mobile_services:
                svc_suffix = svc.lower().replace("mobile_app_", "")
                if fragment in svc_suffix or svc_suffix in fragment:
                    _LOGGER.debug(
                        "NotificationCoordinator: resolved '%s' via fuzzy match (fragment='%s')",
                        svc,
                        fragment,
                    )
                    return svc

        _LOGGER.warning(
            "NotificationCoordinator: could not resolve notify service for "
            "device '%s' (id=%s). "
            "Ensure the Home Assistant Companion App is installed and the device "
            "is registered. Check Developer Tools > Actions > notify.* for the "
            "correct service name.",
            device.name,
            device_id,
        )
        return None

    @callback
    def _on_notification_action(self, event: Event) -> None:
        """Route mobile_app_notification_action to the matching handler.

        This method is a @callback — it runs in the HA event loop thread,
        making it safe to call other @callback methods and schedule coroutines
        via hass.async_create_task().

        Flow:
        1. confirm() arms the NotificationFilter flag.
        2. accept_pending_measurement() replays the stored weight — it is a
           plain method (not a coroutine) so it can be called directly here.
           Internally it calls _process_weight() which schedules async_notify()
           via hass.async_create_task() — safe because we are in the event loop.
        """
        action: str = event.data.get("action", "")

        for _entry_id, (name, notify_filter, _, handler) in self._entries.items():
            if action.upper() == name.upper():
                _LOGGER.debug(
                    "NotificationCoordinator: action '%s' → entry '%s' confirmed",
                    action,
                    name,
                )
                # Step 1: arm the filter so the next accepts() returns True.
                notify_filter.confirm()
                # Step 2: replay the pending measurement synchronously.
                # accept_pending_measurement() is a plain method, safe to call
                # from a @callback because it only calls other @callbacks and
                # schedules coroutines via async_create_task().
                handler.accept_pending_measurement()
                return

        _LOGGER.debug(
            "NotificationCoordinator: action '%s' did not match any user", action
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_FILTERS: dict[str, type[ProfileFilter]] = {
    PROFILE_METHOD_NONE: NoFilterProfile,
    PROFILE_METHOD_ID: ProfileIdFilter,
    PROFILE_METHOD_WEIGHT: WeightRangeFilter,
    PROFILE_METHOD_NOTIFY: NotificationFilter,
}


def build_profile_filter(config: dict[str, Any]) -> ProfileFilter:
    """Instantiate the appropriate ProfileFilter for the given config."""
    method: str = config.get(CONF_PROFILE_METHOD, PROFILE_METHOD_NONE)
    filter_cls = _FILTERS.get(method, NoFilterProfile)
    return filter_cls()
