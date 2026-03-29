from __future__ import annotations

import re

from utils.enums import FileType

# ── MIME type mappings ────────────────────────────────────────────────────────

_IMAGE_MIMES = {
    "image/jpeg", "image/jpg", "image/png", "image/webp",
    "image/gif", "image/tiff", "image/bmp", "image/heic",
}
_PDF_MIME = "application/pdf"
_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_XLSX_MIMES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
}

# ── Filename keyword sets ─────────────────────────────────────────────────────

_INVITATION_FILENAME_KEYWORDS = {
    "invit",        # invitation, invite, invito, invitación
    "invitacion",
    "invitação",
    "einladung",    # German
    "convite",      # Portuguese
    "rsvp",
    "save_the_date",
    "savethedate",
    "save-the-date",
}

_FLOOR_PLAN_KEYWORDS = {
    "floor", "plan", "layout", "planimetria", "pianta", "blueprint",
    "floorplan", "floor_plan", "venue_map", "table_layout", "seating_plan",
}

_LOGO_KEYWORDS = {"logo", "brand", "logotype", "monogram", "crest"}

_VENDOR_QUOTE_KEYWORDS = {
    "quote", "quotation", "preventivo", "devis", "offerta", "angebot",
    "estimate", "proposal", "pricing",
}

_VENDOR_CONTRACT_KEYWORDS = {
    "contract", "agreement", "contratto", "contrato", "vertrag",
    "terms", "signed", "service_agreement",
}

_GUEST_LIST_KEYWORDS = {
    "guest", "guests", "guestlist", "guest_list", "rsvp_list",
    "invitees", "lista_ospiti", "lista_invitati",
}

# ── Text content signals ──────────────────────────────────────────────────────

_INVITATION_TEXT_PATTERNS = [
    r"\b(cordially\s+invited|you\s+are\s+invited|joins?\s+us)\b",
    r"\b(rsvp|r\.s\.v\.p\.)\b",
    r"\b(dress\s+code|black\s+tie|cocktail\s+attire)\b",
    r"\b(celebrat(e|ion)|ceremony|reception)\b.{0,60}\b(invite|join|honour|honor)\b",
    r"\b(bat\s+mitzvah|bar\s+mitzvah|bat-mitzvah)\b",
    r"\b(kindly\s+(request|invited)|pleasure\s+of\s+your\s+company)\b",
    r"\b(save\s+the\s+date)\b",
    r"\b(siete\s+invitados|siamo\s+lieti\s+di\s+invitarvi|vous\s+êtes\s+invités)\b",
]

_VENDOR_QUOTE_TEXT_PATTERNS = [
    r"\b(total|subtotal|vat|iva|tax)\b.{0,30}€",
    r"€\s*[\d.,]+",
    r"\b(valid\s+until|validity|scadenza\s+offerta)\b",
    r"\b(per\s+person|per\s+head|a\s+persona)\b",
]

_CONTRACT_TEXT_PATTERNS = [
    r"\b(this\s+agreement|hereby\s+agree|terms\s+and\s+conditions)\b",
    r"\b(signature|signed\s+by|firma)\b",
    r"\b(payment\s+due|deposit|caparra|acconto)\b",
]


# ── Public API ────────────────────────────────────────────────────────────────

def classify_file(
    filename: str,
    mime_type: str | None,
    extracted_text: str | None = None,
) -> FileType:
    """
    Determine the FileType for an uploaded file.

    Uses filename, MIME type, and optionally extracted text.
    Returns FileType.PLANNING_DOCUMENT as the safe fallback for unclear cases.
    Invitation detection uses both filename keywords and text signals.
    """
    name = filename.lower().replace(" ", "_").replace("-", "_")
    mime = (mime_type or "").lower()
    text = (extracted_text or "").lower()

    # ── Invitation — check first because it overlaps with PDF/image ──────────
    if _is_invitation(name, mime, text):
        return FileType.INVITATION

    # ── Floor plan ────────────────────────────────────────────────────────────
    if _any_keyword(name, _FLOOR_PLAN_KEYWORDS):
        return FileType.FLOOR_PLAN

    # ── Logo ──────────────────────────────────────────────────────────────────
    if _any_keyword(name, _LOGO_KEYWORDS):
        return FileType.LOGO

    # ── Vendor contract (check before quote: more specific) ───────────────────
    if _any_keyword(name, _VENDOR_CONTRACT_KEYWORDS) or _matches_any(text, _CONTRACT_TEXT_PATTERNS):
        return FileType.VENDOR_CONTRACT

    # ── Vendor quote ──────────────────────────────────────────────────────────
    if _any_keyword(name, _VENDOR_QUOTE_KEYWORDS) or _matches_any(text, _VENDOR_QUOTE_TEXT_PATTERNS):
        return FileType.VENDOR_QUOTE

    # ── Guest list ────────────────────────────────────────────────────────────
    if _any_keyword(name, _GUEST_LIST_KEYWORDS) or mime in _XLSX_MIMES:
        return FileType.GUEST_LIST

    # ── Image without specific keyword → inspiration or color reference ───────
    if mime in _IMAGE_MIMES:
        if _any_keyword(name, {"color", "palette", "colore", "farbe", "couleur", "swatch"}):
            return FileType.COLOR_REFERENCE
        if _any_keyword(name, {"inspiration", "inspo", "mood", "moodboard", "reference", "ref"}):
            return FileType.INSPIRATION_IMAGE
        # Generic image — could be decoration or reference; treat as inspiration
        return FileType.INSPIRATION_IMAGE

    # ── DOCX ──────────────────────────────────────────────────────────────────
    if mime == _DOCX_MIME:
        return FileType.PLANNING_DOCUMENT

    # ── PDF without stronger signal ───────────────────────────────────────────
    if mime == _PDF_MIME:
        return FileType.PLANNING_DOCUMENT

    return FileType.OTHER


def is_visual_file(file_type: FileType) -> bool:
    """Return True for file types that benefit from vision-model processing."""
    return file_type in {
        FileType.INVITATION,
        FileType.FLOOR_PLAN,
        FileType.LOGO,
        FileType.COLOR_REFERENCE,
        FileType.INSPIRATION_IMAGE,
        FileType.PHOTO,
    }


# ── Internal helpers ──────────────────────────────────────────────────────────

def _is_invitation(name: str, mime: str, text: str) -> bool:
    """
    Return True if the file is confidently an invitation.

    Requires either a strong filename signal, or a text signal combined
    with an appropriate file type (PDF or image).
    """
    has_filename_signal = _any_keyword(name, _INVITATION_FILENAME_KEYWORDS)
    has_text_signal = _matches_any(text, _INVITATION_TEXT_PATTERNS)
    is_visual_or_pdf = mime in _IMAGE_MIMES or mime == _PDF_MIME

    if has_filename_signal:
        return True
    if has_text_signal and is_visual_or_pdf:
        return True
    return False


def _any_keyword(name: str, keywords: set[str]) -> bool:
    return any(kw in name for kw in keywords)


def _matches_any(text: str, patterns: list[str]) -> bool:
    if not text:
        return False
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
