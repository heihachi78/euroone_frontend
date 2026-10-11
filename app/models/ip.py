"""Model for the IP address sent to the backend, and validation of user input."""

from ipaddress import IPv4Address, IPv6Address

from pydantic import BaseModel, IPvAnyAddress, ValidationError, field_validator

EMPTY_IP_MESSAGE = "Please enter an IP address."


class Ip(BaseModel):
    """A public unicast IPv4 or IPv6 address.

    Attributes:
        ip: The address; an IPv4-mapped IPv6 address is stored as its IPv4 address.
    """

    ip: IPvAnyAddress

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, value: IPv4Address | IPv6Address) -> IPv4Address | IPv6Address:
        """Accept only public unicast addresses, and unwrap IPv4-mapped ones.

        Args:
            value: The address that pydantic parsed.

        Returns:
            The IPv4 address for an IPv4-mapped IPv6 address such as
            `::ffff:8.8.8.8`, otherwise `value` unchanged.

        Raises:
            ValueError: If the address has an IPv6 scope ID, or is not a public
                unicast address (for example private, loopback or multicast).
        """
        if isinstance(value, IPv6Address) and value.scope_id is not None:
            raise ValueError("IP address must not contain a scope ID")
        if not value.is_global or value.is_multicast:
            raise ValueError("IP address must be a public unicast address")
        if isinstance(value, IPv6Address) and value.ipv4_mapped is not None:
            return value.ipv4_mapped
        return value


def ip_error(value: str) -> str | None:
    """Check whether user input is a valid `Ip`.

    Leading and trailing whitespace is ignored.

    Args:
        value: The text the user entered.

    Returns:
        `None` if the input is valid, otherwise the error message to show the user.
    """
    value = value.strip()
    if not value:
        return EMPTY_IP_MESSAGE
    try:
        Ip(ip=value)  # pyright: ignore[reportArgumentType]
    except ValidationError as error:
        return error.errors()[0]["msg"].removeprefix("Value error, ")
    return None
