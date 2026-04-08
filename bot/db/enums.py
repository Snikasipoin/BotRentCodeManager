from enum import StrEnum


class AccountStatus(StrEnum):
    AVAILABLE = "available"
    RENTED = "rented"
    EXPIRED = "expired"
    DISABLED = "disabled"


class OrderStatus(StrEnum):
    PENDING_PHOTO = "pending_photo"
    PHOTO_APPROVED = "photo_approved"
    PHOTO_REJECTED = "photo_rejected"
    CREDS_SENT = "creds_sent"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"