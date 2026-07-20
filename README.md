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


## Notes

### Rate Limiting
The OpenWISP API has a default rate limit of 100 login requests per day (look [here](https://openwisp.io/docs/stable/users/user/settings.html#openwisp-users-auth-throttle-rate) for more information).
This limit will likely not cause any issues with normal usage of the integration; however, when developing or testing this may cause issues.
To avoid this, you can change the rate limit of the controller by setting the `OPENWISP_USERS_AUTH_THROTTLE_RATE` value (default is `"100/day"`) in 
e.g. `<Root of your OpenWISP Controller>/customization/configuration/django/custom_django_settings.py` to `"100/hour"`.