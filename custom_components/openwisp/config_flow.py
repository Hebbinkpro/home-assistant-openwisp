"""Adds config flow for OpenWisp."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME, CONF_VERIFY_SSL
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.loader import async_get_loaded_integration
from slugify import slugify

from .api import (
    OpenWispApiClient,
    OpenWispApiClientAuthenticationError,
    OpenWispApiClientCommunicationError,
    OpenWispApiClientError,
)
from .const import DOMAIN, LOGGER


class OpenWispFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for OpenWisp."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                await self._test_credentials(
                    url=user_input[CONF_URL],
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    verify_ssl=user_input[CONF_VERIFY_SSL],
                )
            except OpenWispApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except OpenWispApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except OpenWispApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    ## Do NOT use this in production code
                    ## The unique_id should never be something that can change
                    ## https://developers.home-assistant.io/docs/config_entries_config_flow_handler#unique-ids
                    unique_id=slugify(user_input[CONF_USERNAME])
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data=user_input,
                )

        integration = async_get_loaded_integration(self.hass, DOMAIN)
        assert integration.documentation is not None, (  # noqa: S101
            "Integration documentation URL is not set in manifest.json"
        )

        return self.async_show_form(
            step_id="user",
            description_placeholders={
                "documentation_url": integration.documentation,
            },
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_URL,
                        default=(user_input or {}).get(CONF_URL, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.URL,
                        )
                    ),
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or {}).get(CONF_USERNAME, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                        ),
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                    vol.Optional(
                        CONF_VERIFY_SSL,
                        default=(user_input or {}).get(CONF_VERIFY_SSL, True),
                    ): selector.BooleanSelector(
                        selector.BooleanSelectorConfig(),
                    ),
                },
            ),
            errors=_errors,
        )

    async def _test_credentials(
        self, url: str, username: str, password: str, *, verify_ssl: bool = True
    ) -> None:
        """Validate credentials."""
        client = OpenWispApiClient(
            url=url,
            username=username,
            password=password,
            session=async_create_clientsession(self.hass),
            verify_ssl=verify_ssl,
        )
        await client.async_authenticate()
