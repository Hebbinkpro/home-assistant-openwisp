"""Test API classes"""

from uuid import UUID

from custom_components.openwisp.api import OpenWispDevice, OpenWispOrganization

DEFAULT_ID = "12345678-1234-1234-1234-123456789abc"
DATE_CREATED = "2026-02-15T00:00:00+01:00"
DATE_MODIFIED = "2026-02-16T00:00:00+01:00"


def test_organization_from_filled_dict():
    data = {
        "id": DEFAULT_ID,
        "name": "default",
        "is_active": True,
        "slug": "default",
        "description": "Test organization",
        "url": "https://example.org/",
        "created": DATE_CREATED,
        "modified": DATE_MODIFIED,
    }

    org = OpenWispOrganization.from_dict(data)

    assert isinstance(org, OpenWispOrganization)
    assert org.id == UUID(DEFAULT_ID)
    assert org.name == "default"


def test_organization_from_minimal_dict():
    org = OpenWispOrganization.from_dict({"id": DEFAULT_ID})

    assert isinstance(org, OpenWispOrganization)
    assert org.id == UUID(DEFAULT_ID)
    assert org.name == ""


def test_organization_from_empty_dict():
    # this should fail
    try:
        OpenWispOrganization.from_dict({})
        assert False
    except:
        assert True


def test_device_from_filled_dict():

    data = {
        "id": DEFAULT_ID,
        "name": "Test device",
        "organization": DEFAULT_ID,
        "group": DEFAULT_ID,
        "mac_address": "aa:bb:cc:dd:ee:ff",
        "last_ip": "192.168.1.10",
        "management_ip": "192.168.1.1",
        "model": "Test Model",
        "os": "Linux",
        "system": "OpenWrt",
        "notes": "Test device notes",
        "config": {},
        "monitoring": {},
        "created": DATE_CREATED,
        "modified": DATE_MODIFIED,
        "data": None,
    }

    device = OpenWispDevice.from_dict(data)

    assert isinstance(device, OpenWispDevice)
    assert device.id == UUID(DEFAULT_ID)
    assert device.name == "Test device"


def test_device_from_minimal_dict():

    data = {
        "id": DEFAULT_ID,
    }

    device = OpenWispDevice.from_dict(data)

    assert isinstance(device, OpenWispDevice)
    assert device.id == UUID(DEFAULT_ID)
    assert device.name == ""


def test_device_from_empty_dict():
    # this should fail
    try:
        OpenWispDevice.from_dict({})
        assert False
    except:
        assert True
