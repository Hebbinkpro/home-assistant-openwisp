"""Adds config flow for OpenWisp."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, CONF_VERIFY_SSL
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from slugify import slugify

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult

from .api import (
    OpenWispApiClient,
    OpenWispApiClientAuthenticationError,
    OpenWispApiClientCommunicationError,
    OpenWispApiClientError,
    OpenWispOrganization,
)
from .const import DOMAIN, LOGGER

CONF_ORGANIZATION = "organization"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_VERIFY_SSL, default=True): bool,
    }
)


def create_openwisp_client(
    hass: config_entries.HomeAssistant, data: dict[str, Any]
) -> OpenWispApiClient:
    """Create an OpenWISP API client for the given config entry."""
    return OpenWispApiClient(
        host=data[CONF_HOST],
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        session=async_create_clientsession(hass, verify_ssl=data[CONF_VERIFY_SSL]),
    )


class HubInfo(NamedTuple):
    """OpenWISP controller information."""

    name: str
    organizations: list[OpenWispOrganization]


async def _validate_input(
    hass: config_entries.HomeAssistant, data: dict[str, Any]
) -> HubInfo:
    """Validate the user input allows us to connect."""
    client = create_openwisp_client(hass, data)
    await client.async_authenticate()
    name = client.hostname
    organizations = await client.async_get_organizations()
    return HubInfo(name, organizations)


class OpenWispFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for OpenWisp."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow for a new integration."""
        self._openwisp_opts: dict[str, Any] = {}
        self._name: str = ""
        self._organizations: list[OpenWispOrganization] = []

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        info: HubInfo | None = None
        if user_input is not None:
            info = await self._test_credentials(user_input, _errors)

        if info is None or user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors=_errors,
            )

        if info is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=_errors
            )

        self._openwisp_opts.update(user_input)
        self._name = info.name
        self._organizations = info.organizations

        if len(self._organizations) > 1:
            return await self.async_step_organization()
        return await self.async_step_organization(
            {CONF_ORGANIZATION: self._organizations[0].id}
        )

    async def async_step_organization(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Handle step to select an organization to manage."""
        _errors = {}
        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(
                        CONF_ORGANIZATION, "organization"
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=str(org.id),
                                    label=org.name,
                                )
                                for org in self._organizations
                            ],
                            multiple=False,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            )
            return self.async_show_form(
                step_id="organization", data_schema=schema, errors=_errors
            )

        await self.async_set_unique_id(
            f"{slugify(self._name)}_{user_input[CONF_ORGANIZATION]}"
        )
        self._abort_if_unique_id_configured()

        self._openwisp_opts.update(user_input)
        org_name = next(
            org
            for org in self._organizations
            if org.id == user_input[CONF_ORGANIZATION]
        ).name
        display_name = f"{self._name} ({org_name})"
        return self.async_create_entry(title=display_name, data=self._openwisp_opts)

    async def _test_credentials(
        self, data: dict[str, Any], errors: dict[str, str]
    ) -> HubInfo | None:
        """Validate credentials."""
        try:
            info = await _validate_input(self.hass, data)
            if len(info.organizations) > 0:
                return info
            errors["base"] = "no_organizations_found"

        except OpenWispApiClientAuthenticationError as exception:
            LOGGER.warning(exception)
            errors["base"] = "auth"
        except OpenWispApiClientCommunicationError as exception:
            LOGGER.error(exception)
            errors["base"] = "connection"
        except OpenWispApiClientError as exception:
            LOGGER.exception(exception)
            errors["base"] = "unknown"
        return None
