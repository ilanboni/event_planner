from enum import Enum


class Domain(str, Enum):
    GENERAL = "general"
    SPACE = "space"
    DESIGN = "design"
    BUDGET = "budget"
    VENDORS = "vendors"
    GUESTS = "guests"
    TIMELINE = "timeline"
    ENTERTAINMENT = "entertainment"


class DecisionSource(str, Enum):
    CLIENT_STATED_DIRECTLY = "client_stated_directly"
    CLIENT_APPROVED_RECOMMENDATION = "client_approved_recommendation"
    LEAD_RESOLVED_CONFLICT = "lead_resolved_conflict"
    ARCHIVIST_EXTRACTED_AND_CONFIRMED = "archivist_extracted_and_confirmed"


class IssueStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    AWAITING_CLIENT_INPUT = "awaiting_client_input"
    AWAITING_SPECIALIST = "awaiting_specialist"
    RESOLVED = "resolved"
    DEFERRED = "deferred"


class IssuePriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VendorCategory(str, Enum):
    VENUE = "venue"
    CATERING = "catering"
    PHOTOGRAPHY = "photography"
    VIDEOGRAPHY = "videography"
    DJ = "dj"
    BAND = "band"
    FLORIST = "florist"
    DECOR = "decor"
    ACTIVITIES = "activities"
    HAIR_MAKEUP = "hair_makeup"
    TRANSPORTATION = "transportation"
    STATIONERY = "stationery"
    OTHER = "other"


class VendorStatus(str, Enum):
    CONSIDERING = "considering"
    QUOTE_RECEIVED = "quote_received"
    PENDING_APPROVAL = "pending_approval"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class BudgetStatus(str, Enum):
    HEALTHY = "healthy"
    WATCH = "watch"
    AT_RISK = "at_risk"
    OVER = "over"


class SeatingStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    DRAFT_READY = "draft_ready"
    CONFIRMED = "confirmed"


class TimelineDraftStatus(str, Enum):
    NOT_STARTED = "not_started"
    DRAFT = "draft"
    REVIEWED = "reviewed"
    CONFIRMED = "confirmed"


class FileType(str, Enum):
    FLOOR_PLAN = "floor_plan"
    LOGO = "logo"
    COLOR_REFERENCE = "color_reference"
    INSPIRATION_IMAGE = "inspiration_image"
    INVITATION = "invitation"
    VENDOR_QUOTE = "vendor_quote"
    VENDOR_CONTRACT = "vendor_contract"
    GUEST_LIST = "guest_list"
    PLANNING_DOCUMENT = "planning_document"
    PHOTO = "photo"
    OTHER = "other"


class AttachmentType(str, Enum):
    PHOTO = "photo"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"


class MessageDirection(str, Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
