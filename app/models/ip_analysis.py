"""Model for the backend's analysis of an IP address."""

from pydantic import BaseModel, IPvAnyAddress


class IpAnalysis(BaseModel):
    """The backend's analysis of an IP address.

    Attributes:
        ip: The analyzed IP address.
        summary: A Markdown summary of the IP address.
    """

    ip: IPvAnyAddress
    summary: str
