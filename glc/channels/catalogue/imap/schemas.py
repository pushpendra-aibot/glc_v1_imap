"""Channel-specific Pydantic types for the imap adapter. Add types
here as needed; the canonical ChannelMessage / ChannelReply envelope
lives in glc.channels.envelope."""

from __future__ import annotations

from pydantic import BaseModel, Field

class ImapConfig(BaseModel):
    """Configuration mapping for IMAP/SMTP environment variables."""
    imap_host: str = Field(default="", description="IMAP server hostname")
    imap_user: str = Field(default="", description="IMAP account username")
    imap_password: str = Field(default="", description="IMAP account password")
    smtp_host: str = Field(default="", description="SMTP server hostname")
    smtp_user: str = Field(default="", description="SMTP account username")
    smtp_password: str = Field(default="", description="SMTP account password")
