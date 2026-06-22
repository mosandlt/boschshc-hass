"""Tests for APK-batch 3 WalkTest entities + SmartSensitivity number entities.

Covers:
- SHCWalkTestButton (start)
- SHCWalkTestStopButton (stop)
- WalkStateSensor
- SmartSensitivitySecurityLevelNumber
- SmartSensitivityComfortLevelNumber

Run with:
  PYTHONPATH="<lib>:<hass>" PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
  python3 -m pytest tests/bosch_shc/test_apk_walktest_and_sensitivity.py -q -o addopts=
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: F401

from custom_components.bosch_shc.button import (
    SHCWalkTestButton,
    SHCWalkTestStopButton,
    async_setup_entry as button_setup_entry,
)
from custom_components.bosch_shc.sensor import WalkStateSensor
from custom_components.bosch_shc.number import (
    SmartSensitivitySecurityLevelNumber,
    SmartSensitivityComfortLevelNumber,
    async_setup_entry as number_setup_entry,
)
from custom_components.bosch_shc.const import DATA_SESSION, DATA_SHC, DOMAIN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_md2(**kwargs):
    defaults = dict(name="MD2", id="md1", root_device_id="root1", serial="SER1",
                    supports_silentmode=False, supports_batterylevel=False)
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_button_session(**helper_lists):
    defaults = dict(
        smoke_detectors=[],
        twinguards=[],
        motion_detectors2=[],
        userdefinedstates=[],
    )
    defaults.update(helper_lists)
    device_helper = SimpleNamespace(**defaults)
    return SimpleNamespace(
        device_helper=device_helper,
        userdefinedstates=[],
        scenarios=[],
        subscribe=lambda *a, **kw: None,
    )


def _make_number_session(**helper_lists):
    defaults = dict(
        thermostats=[],
        roomthermostats=[],
        micromodule_impulse_relays=[],
        heating_circuits=[],
        motion_detectors2=[],
    )
    defaults.update(helper_lists)
    device_helper = SimpleNamespace(**defaults)
    return SimpleNamespace(device_helper=device_helper)


def _make_button_hass_and_entry(session):
    entry_id = "E1"
    hass = SimpleNamespace(
        data={
            DOMAIN: {entry_id: {
                DATA_SESSION: session,
                DATA_SHC: SimpleNamespace(
                    name="SHC", id="shc", identifiers={("bosch_shc", "shc")},
                    manufacturer="Bosch", model="SHC"),
            }}
        }
    )
    config_entry = SimpleNamespace(
        options={},
        entry_id=entry_id,
        unique_id="UID1",
        async_on_unload=MagicMock(),
    )
    return hass, config_entry


def _make_number_hass_and_entry(session):
    entry_id = "E1"
    hass = SimpleNamespace(
        data={DOMAIN: {entry_id: {DATA_SESSION: session}}}
    )
    config_entry = SimpleNamespace(options={}, entry_id=entry_id,
                                   async_on_unload=MagicMock())
    return hass, config_entry


async def _async_setup_buttons(session):
    hass, config_entry = _make_button_hass_and_entry(session)
    entities = []

    def add_entities(new_ents, *args, **kwargs):
        entities.extend(new_ents)

    await button_setup_entry(hass, config_entry, add_entities)
    return entities


def _setup_buttons(session):
    return asyncio.run(_async_setup_buttons(session))


async def _async_setup_numbers(session):
    hass, config_entry = _make_number_hass_and_entry(session)
    entities = []

    def add_entities(new_ents, *args, **kwargs):
        entities.extend(new_ents)

    await number_setup_entry(hass, config_entry, add_entities)
    return entities


def _setup_numbers(session):
    return asyncio.run(_async_setup_numbers(session))


# ---------------------------------------------------------------------------
# WalkTest start button — setup entry
# ---------------------------------------------------------------------------


class TestWalkTestButtonSetup:
    def test_walk_test_button_created_when_walk_state_present(self):
        from boschshcpy.services_impl import WalkTestService
        md2 = _fake_md2(walk_state=WalkTestService.WalkState.UNKNOWN)
        session = _make_button_session(motion_detectors2=[md2])
        entities = _setup_buttons(session)
        types = [type(e).__name__ for e in entities]
        assert "SHCWalkTestButton" in types

    def test_walk_test_button_skipped_when_no_walk_state_attr(self):
        md2 = _fake_md2()  # no walk_state attr
        session = _make_button_session(motion_detectors2=[md2])
        entities = _setup_buttons(session)
        types = [type(e).__name__ for e in entities]
        assert "SHCWalkTestButton" not in types

    def test_walk_test_button_skipped_when_walk_state_is_none(self):
        md2 = _fake_md2(walk_state=None)
        session = _make_button_session(motion_detectors2=[md2])
        entities = _setup_buttons(session)
        types = [type(e).__name__ for e in entities]
        assert "SHCWalkTestButton" not in types

    def test_walk_test_stop_button_created_alongside_start(self):
        from boschshcpy.services_impl import WalkTestService
        md2 = _fake_md2(walk_state=WalkTestService.WalkState.UNKNOWN)
        session = _make_button_session(motion_detectors2=[md2])
        entities = _setup_buttons(session)
        types = [type(e).__name__ for e in entities]
        assert "SHCWalkTestStopButton" in types

    def test_walk_test_stop_button_skipped_when_no_walk_state(self):
        md2 = _fake_md2()  # no walk_state attr
        session = _make_button_session(motion_detectors2=[md2])
        entities = _setup_buttons(session)
        types = [type(e).__name__ for e in entities]
        assert "SHCWalkTestStopButton" not in types


# ---------------------------------------------------------------------------
# SHCWalkTestButton — unit tests
# ---------------------------------------------------------------------------


class TestSHCWalkTestButton:
    def _make(self):
        dev = _fake_md2()
        b = SHCWalkTestButton.__new__(SHCWalkTestButton)
        b._device = dev
        b._attr_unique_id = f"{dev.root_device_id}_{dev.id}_walk_test"
        b._attr_name = "Walk Test"
        return b

    def test_unique_id(self):
        b = self._make()
        assert b._attr_unique_id == "root1_md1_walk_test"

    def test_press_calls_service_set_walk_state_request(self):
        from boschshcpy.services_impl import WalkTestService
        calls = []
        svc = SimpleNamespace(
            set_walk_state_request=lambda v: calls.append(v)
        )
        dev = _fake_md2(_walktest_service=svc)
        b = SHCWalkTestButton.__new__(SHCWalkTestButton)
        b._device = dev
        b.press()
        assert calls == [WalkTestService.WalkStateRequest.WALK_STATE_START]

    def test_press_no_service_does_not_raise(self):
        dev = _fake_md2()  # no _walktest_service
        b = SHCWalkTestButton.__new__(SHCWalkTestButton)
        b._device = dev
        b.press()  # must not raise

    def test_press_with_async_setter(self):
        """When device has async_set_walk_state_request, press falls back to service."""
        from boschshcpy.services_impl import WalkTestService
        calls = []
        svc = SimpleNamespace(
            set_walk_state_request=lambda v: calls.append(v)
        )

        async def _async_setter(value):
            pass

        dev = _fake_md2(
            async_set_walk_state_request=_async_setter,
            _walktest_service=svc,
        )
        b = SHCWalkTestButton.__new__(SHCWalkTestButton)
        b._device = dev
        # In test context there's no running loop so RuntimeError is caught
        # and service.set_walk_state_request is called.
        b.press()
        assert WalkTestService.WalkStateRequest.WALK_STATE_START in calls


# ---------------------------------------------------------------------------
# SHCWalkTestStopButton — unit tests
# ---------------------------------------------------------------------------


class TestSHCWalkTestStopButton:
    def _make(self):
        dev = _fake_md2()
        b = SHCWalkTestStopButton.__new__(SHCWalkTestStopButton)
        b._device = dev
        b._attr_unique_id = f"{dev.root_device_id}_{dev.id}_walk_test_stop"
        b._attr_name = "Walk Test Stop"
        return b

    def test_unique_id(self):
        b = self._make()
        assert b._attr_unique_id == "root1_md1_walk_test_stop"

    def test_press_calls_service_stop(self):
        from boschshcpy.services_impl import WalkTestService
        calls = []
        svc = SimpleNamespace(
            set_walk_state_request=lambda v: calls.append(v)
        )
        dev = _fake_md2(_walktest_service=svc)
        b = SHCWalkTestStopButton.__new__(SHCWalkTestStopButton)
        b._device = dev
        b.press()
        assert calls == [WalkTestService.WalkStateRequest.STOP]

    def test_press_no_service_does_not_raise(self):
        dev = _fake_md2()  # no _walktest_service
        b = SHCWalkTestStopButton.__new__(SHCWalkTestStopButton)
        b._device = dev
        b.press()  # must not raise

    def test_press_with_async_setter_falls_back_to_service(self):
        from boschshcpy.services_impl import WalkTestService
        calls = []
        svc = SimpleNamespace(
            set_walk_state_request=lambda v: calls.append(v)
        )

        async def _async_setter(value):
            pass

        dev = _fake_md2(
            async_set_walk_state_request=_async_setter,
            _walktest_service=svc,
        )
        b = SHCWalkTestStopButton.__new__(SHCWalkTestStopButton)
        b._device = dev
        b.press()
        assert WalkTestService.WalkStateRequest.STOP in calls

    def test_icon(self):
        b = self._make()
        assert b._attr_icon == "mdi:stop"


# ---------------------------------------------------------------------------
# WalkStateSensor — unit tests
# ---------------------------------------------------------------------------


class TestWalkStateSensor:
    def _make(self, walk_state_name="UNKNOWN"):
        from boschshcpy.services_impl import WalkTestService
        val = WalkTestService.WalkState[walk_state_name]
        dev = _fake_md2(walk_state=val)
        s = WalkStateSensor.__new__(WalkStateSensor)
        s._device = dev
        s._attr_unique_id = f"{dev.root_device_id}_{dev.id}_walk_state"
        s._attr_name = "Walk Test State"
        return s

    def test_unique_id(self):
        s = self._make()
        assert s._attr_unique_id == "root1_md1_walk_state"

    def test_native_value_unknown(self):
        s = self._make("UNKNOWN")
        assert s.native_value == "UNKNOWN"

    def test_native_value_walk_test_started(self):
        s = self._make("WALK_TEST_STARTED")
        assert s.native_value == "WALK_TEST_STARTED"

    def test_native_value_stopped(self):
        s = self._make("STOPPED")
        assert s.native_value == "STOPPED"

    def test_native_value_none_when_walk_state_is_none(self):
        dev = _fake_md2(walk_state=None)
        s = WalkStateSensor.__new__(WalkStateSensor)
        s._device = dev
        assert s.native_value is None

    def test_native_value_attribute_error_returns_none(self):
        dev = _fake_md2()  # no walk_state attr
        s = WalkStateSensor.__new__(WalkStateSensor)
        s._device = dev
        assert s.native_value is None

    def test_options_list(self):
        s = self._make()
        assert "WALK_TEST_STARTED" in s._attr_options
        assert "STOPPED" in s._attr_options
        assert "UNKNOWN" in s._attr_options


# ---------------------------------------------------------------------------
# WalkStateSensor — setup entry (part of sensor.py)
# ---------------------------------------------------------------------------


class TestWalkStateSensorSetup:
    def _run_sensor_setup(self, md2_list):
        from custom_components.bosch_shc.sensor import async_setup_entry as sensor_setup
        from custom_components.bosch_shc.const import DATA_SHC

        entry_id = "E1"
        emma = SimpleNamespace(
            name="EMMA", id="com.bosch.tt.emma.applink",
            root_device_id="root_emma", serial="EMMA_SER",
            supports_batterylevel=False,
        )
        device_helper = SimpleNamespace(
            thermostats=[],
            wallthermostats=[],
            roomthermostats=[],
            twinguards=[],
            smart_plugs=[],
            light_switches_bsm=[],
            micromodule_light_controls=[],
            micromodule_shutter_controls=[],
            micromodule_blinds=[],
            smart_plugs_compact=[],
            motion_detectors=[],
            motion_detectors2=list(md2_list),
            shutter_contacts=[],
            shutter_contacts2=[],
            smoke_detectors=[],
            universal_switches=[],
            water_leakage_detectors=[],
        )
        session = SimpleNamespace(device_helper=device_helper, emma=emma)
        hass = SimpleNamespace(
            data={
                DOMAIN: {entry_id: {
                    DATA_SESSION: session,
                    DATA_SHC: SimpleNamespace(
                        name="SHC", id="shc",
                        identifiers={("bosch_shc", "shc")},
                        manufacturer="Bosch", model="SHC",
                    ),
                }}
            }
        )
        config_entry = SimpleNamespace(
            options={},
            entry_id=entry_id,
            async_on_unload=MagicMock(),
        )
        entities = []

        def add_entities(new_ents, *args, **kwargs):
            entities.extend(new_ents)

        with patch(
            "custom_components.bosch_shc.sensor.async_migrate_to_new_unique_id",
            new=AsyncMock(return_value=None),
        ):
            asyncio.run(sensor_setup(hass, config_entry, add_entities))

        return entities

    def test_walk_state_sensor_created_when_walk_state_present(self):
        from boschshcpy.services_impl import WalkTestService
        md2 = _fake_md2(walk_state=WalkTestService.WalkState.UNKNOWN)
        entities = self._run_sensor_setup([md2])
        types = [type(e).__name__ for e in entities]
        assert "WalkStateSensor" in types

    def test_walk_state_sensor_skipped_when_walk_state_none(self):
        md2 = _fake_md2(walk_state=None)
        entities = self._run_sensor_setup([md2])
        types = [type(e).__name__ for e in entities]
        assert "WalkStateSensor" not in types


# ---------------------------------------------------------------------------
# SmartSensitivitySecurityLevelNumber
# ---------------------------------------------------------------------------


class TestSmartSensitivitySecurityLevelNumber:
    def _make(self, manual_level=3):
        sensitivity_dict = {"context": "SECURITY", "automaticLevel": 5, "manualLevel": manual_level}

        def _get_sensitivity(c):
            return sensitivity_dict

        dev = _fake_md2(get_smart_sensitivity=_get_sensitivity)
        n = SmartSensitivitySecurityLevelNumber.__new__(SmartSensitivitySecurityLevelNumber)
        n._device = dev
        n._attr_unique_id = (
            f"{dev.root_device_id}_{dev.id}_smart_sensitivity_security"
        )
        n._attr_name = "Security Sensitivity Level"
        return n

    def test_unique_id(self):
        n = self._make()
        assert n._attr_unique_id == "root1_md1_smart_sensitivity_security"

    def test_native_value_returns_manual_level(self):
        n = self._make(manual_level=7)
        assert n.native_value == 7.0

    def test_native_value_none_when_get_returns_none(self):
        def _get_none(c):
            return None

        dev = _fake_md2(get_smart_sensitivity=_get_none)
        n = SmartSensitivitySecurityLevelNumber.__new__(SmartSensitivitySecurityLevelNumber)
        n._device = dev
        assert n.native_value is None

    def test_set_native_value_calls_service(self):
        from boschshcpy.services_impl import SmartSensitivityControlService
        calls = []
        ctx = SmartSensitivityControlService.SmartSensitivityContext.SECURITY
        svc = SimpleNamespace(
            set_manual_level=lambda c, v: calls.append((c, v))
        )
        dev = _fake_md2(
            get_smart_sensitivity=lambda c: {"manualLevel": 5},
            _smart_sensitivity_control_service=svc,
        )
        n = SmartSensitivitySecurityLevelNumber.__new__(SmartSensitivitySecurityLevelNumber)
        n._device = dev
        n.set_native_value(8.0)
        assert len(calls) == 1
        assert calls[0][0] == ctx
        assert calls[0][1] == 8

    def test_set_native_value_no_service_does_not_raise(self):
        dev = _fake_md2(get_smart_sensitivity=lambda c: {"manualLevel": 5})
        n = SmartSensitivitySecurityLevelNumber.__new__(SmartSensitivitySecurityLevelNumber)
        n._device = dev
        n.set_native_value(3.0)  # must not raise

    def test_created_when_get_smart_sensitivity_present(self):
        md2 = _fake_md2(get_smart_sensitivity=lambda c: {"manualLevel": 5})
        session = _make_number_session(motion_detectors2=[md2])
        entities = _setup_numbers(session)
        types = [type(e).__name__ for e in entities]
        assert "SmartSensitivitySecurityLevelNumber" in types

    def test_skipped_when_get_smart_sensitivity_absent(self):
        md2 = _fake_md2()  # no get_smart_sensitivity attr
        session = _make_number_session(motion_detectors2=[md2])
        entities = _setup_numbers(session)
        types = [type(e).__name__ for e in entities]
        assert "SmartSensitivitySecurityLevelNumber" not in types

    def test_entity_category_config(self):
        from homeassistant.helpers.entity import EntityCategory
        n = SmartSensitivitySecurityLevelNumber.__new__(SmartSensitivitySecurityLevelNumber)
        assert n._attr_entity_category == EntityCategory.CONFIG

    def test_native_min_value(self):
        n = SmartSensitivitySecurityLevelNumber.__new__(SmartSensitivitySecurityLevelNumber)
        assert n._attr_native_min_value == 0.0

    def test_native_max_value(self):
        n = SmartSensitivitySecurityLevelNumber.__new__(SmartSensitivitySecurityLevelNumber)
        assert n._attr_native_max_value == 10.0

    def test_native_step(self):
        n = SmartSensitivitySecurityLevelNumber.__new__(SmartSensitivitySecurityLevelNumber)
        assert n._attr_native_step == 1.0


# ---------------------------------------------------------------------------
# SmartSensitivityComfortLevelNumber
# ---------------------------------------------------------------------------


class TestSmartSensitivityComfortLevelNumber:
    def _make(self, manual_level=2):
        def _get_sensitivity(c):
            return {"context": "COMFORT", "automaticLevel": 3, "manualLevel": manual_level}

        dev = _fake_md2(get_smart_sensitivity=_get_sensitivity)
        n = SmartSensitivityComfortLevelNumber.__new__(SmartSensitivityComfortLevelNumber)
        n._device = dev
        n._attr_unique_id = (
            f"{dev.root_device_id}_{dev.id}_smart_sensitivity_comfort"
        )
        n._attr_name = "Comfort Sensitivity Level"
        return n

    def test_unique_id(self):
        n = self._make()
        assert n._attr_unique_id == "root1_md1_smart_sensitivity_comfort"

    def test_native_value_returns_manual_level(self):
        n = self._make(manual_level=4)
        assert n.native_value == 4.0

    def test_native_value_none_when_get_returns_none(self):
        def _get_none(c):
            return None

        dev = _fake_md2(get_smart_sensitivity=_get_none)
        n = SmartSensitivityComfortLevelNumber.__new__(SmartSensitivityComfortLevelNumber)
        n._device = dev
        assert n.native_value is None

    def test_set_native_value_calls_service(self):
        from boschshcpy.services_impl import SmartSensitivityControlService
        calls = []
        ctx = SmartSensitivityControlService.SmartSensitivityContext.COMFORT
        svc = SimpleNamespace(
            set_manual_level=lambda c, v: calls.append((c, v))
        )
        dev = _fake_md2(
            get_smart_sensitivity=lambda c: {"manualLevel": 2},
            _smart_sensitivity_control_service=svc,
        )
        n = SmartSensitivityComfortLevelNumber.__new__(SmartSensitivityComfortLevelNumber)
        n._device = dev
        n.set_native_value(5.0)
        assert len(calls) == 1
        assert calls[0][0] == ctx
        assert calls[0][1] == 5

    def test_set_native_value_no_service_does_not_raise(self):
        dev = _fake_md2(get_smart_sensitivity=lambda c: {"manualLevel": 2})
        n = SmartSensitivityComfortLevelNumber.__new__(SmartSensitivityComfortLevelNumber)
        n._device = dev
        n.set_native_value(4.0)  # must not raise

    def test_created_when_guard_present(self):
        md2 = _fake_md2(get_smart_sensitivity=lambda c: {"manualLevel": 2})
        session = _make_number_session(motion_detectors2=[md2])
        entities = _setup_numbers(session)
        types = [type(e).__name__ for e in entities]
        assert "SmartSensitivityComfortLevelNumber" in types

    def test_skipped_when_guard_absent(self):
        md2 = _fake_md2()  # no get_smart_sensitivity attr
        session = _make_number_session(motion_detectors2=[md2])
        entities = _setup_numbers(session)
        types = [type(e).__name__ for e in entities]
        assert "SmartSensitivityComfortLevelNumber" not in types

    def test_entity_category_config(self):
        from homeassistant.helpers.entity import EntityCategory
        n = SmartSensitivityComfortLevelNumber.__new__(SmartSensitivityComfortLevelNumber)
        assert n._attr_entity_category == EntityCategory.CONFIG
