# OpenWISP Integration for Home Assistant

[![Version](https://img.shields.io/github/v/release/hebbinkpro/home-assistant-openwisp?label=version)](https://github.com/hebbinkpro/home-assistant-openwisp/releases/latest)
[![Lint](https://github.com/Hebbinkpro/home-assistant-openwisp/actions/workflows/lint.yml/badge.svg)](https://github.com/Hebbinkpro/home-assistant-openwisp/actions/workflows/lint.yml)
[![Validate](https://github.com/Hebbinkpro/home-assistant-openwisp/actions/workflows/validate.yml/badge.svg)](https://github.com/Hebbinkpro/home-assistant-openwisp/actions/workflows/validate.yml)

Custom Home Assistant integration for OpenWISP devices and monitoring.

## Installation

You can install the integration using [HACS](https://hacs.xyz/). In HACS add the
integration (https://github.com/Hebbinkpro/home-assistant-openwisp)
under [Custom Repositories](https://hacs.xyz/docs/faq/custom_repositories/).

You can also add the integration manually by copying `custom_components/openwisp` into
`<HASS config directory>/custom_components`.


## Wi-Fi

Every Wi-Fi client in the open Wi-Fi sessions of the organization gets a
`device_tracker`. Its attributes show the device, SSID, interface and signal it
was last seen on. Roaming closes the session on one device and opens one on the
next, possibly one monitoring report apart, so a client is only reported away
once it has been missing for three minutes.

Every wireless interface of a device gets a sensor with its number of clients
(peers for an 802.11s mesh interface) and its SSID, channel, frequency, TX power
and noise as attributes.

The data is as fresh as the monitoring reports of the devices: the
openwisp-monitoring agent sends one every 5 minutes by default. For presence
detection set its `interval` lower, e.g. to `60` in a template:

```json
{"openwisp-monitoring": [{"config_name": "monitoring", "config_value": "monitoring", "interval": "60"}]}
```

The API user needs view permissions on devices, device data, Wi-Fi sessions and
Wi-Fi clients.

## Notes

### Rate Limiting
The OpenWISP API has a default rate limit of 100 login requests per day (look [here](https://openwisp.io/docs/stable/users/user/settings.html#openwisp-users-auth-throttle-rate) for more information).
This limit will likely not cause any issues with normal usage of the integration; however, when developing or testing this may cause issues.
To avoid this, you can change the rate limit of the controller by setting the `OPENWISP_USERS_AUTH_THROTTLE_RATE` value (default is `"100/day"`) in 
e.g. `<Root of your OpenWISP Controller>/customization/configuration/django/custom_django_settings.py` to `"100/hour"`.