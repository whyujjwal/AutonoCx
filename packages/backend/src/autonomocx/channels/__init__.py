"""AutonoCX channel adapters.

Each adapter normalises a specific communication channel (web chat,
WhatsApp, email, voice, SMS) into a common message interface that the
orchestration engine can consume.
"""

from .base import ChannelAdapter, InboundMessage, OutboundMessage
from .email import EmailAdapter
from .sms import SMSAdapter
from .voice import VoiceAdapter
from .webchat import WebChatAdapter
from .whatsapp import WhatsAppAdapter

__all__ = [
    "ChannelAdapter",
    "InboundMessage",
    "OutboundMessage",
    "EmailAdapter",
    "SMSAdapter",
    "VoiceAdapter",
    "WebChatAdapter",
    "WhatsAppAdapter",
]
