"""Input validation helpers."""
import os
from django.conf import settings


def validate_file_extension(filename: str) -> tuple[bool, str]:
    """
    Return (True, '') if the file extension is in the allow-list,
    otherwise (False, <reason>).
    """
    if not filename:
        return False, 'Filename is empty.'

    _, ext = os.path.splitext(filename.lower())
    if not ext:
        return False, 'File has no extension.'

    allowed = getattr(settings, 'ALLOWED_FILE_EXTENSIONS', set())
    if ext not in allowed:
        return False, f'File extension "{ext}" is not allowed.'

    return True, ''


def validate_file_size(size: int) -> tuple[bool, str]:
    """Return (True, '') if the file size is within the configured limit."""
    max_bytes = getattr(settings, 'MAX_FILE_SIZE_MB', 5) * 1024 * 1024
    if size > max_bytes:
        mb = max_bytes // (1024 * 1024)
        return False, f'File size exceeds the maximum allowed size of {mb} MB.'
    return True, ''


def validate_user_id(user_id: str) -> tuple[bool, str]:
    """Return (True, '') for a non-empty, reasonably-sized UserId header value."""
    if not user_id:
        return False, 'UserId header is required.'
    if len(user_id) > 255:
        return False, 'UserId is too long (max 255 characters).'
    return True, ''
