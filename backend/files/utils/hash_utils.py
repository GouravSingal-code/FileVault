"""SHA-256 hashing utilities for file deduplication."""
import hashlib

SMALL_FILE_CHUNK = 8 * 1024      # 8 KB
LARGE_FILE_CHUNK = 64 * 1024     # 64 KB
LARGE_FILE_THRESHOLD = 10 * 1024 * 1024  # 10 MB


def compute_sha256(file_obj) -> str:
    """
    Compute the SHA-256 hash of a Django UploadedFile or any file-like object.

    Uses larger read chunks for files > 10 MB to reduce syscall overhead.
    Rewinds the file to position 0 before reading and after.
    """
    file_obj.seek(0)
    size = _get_size(file_obj)
    chunk_size = LARGE_FILE_CHUNK if size > LARGE_FILE_THRESHOLD else SMALL_FILE_CHUNK

    hasher = hashlib.sha256()
    while True:
        chunk = file_obj.read(chunk_size)
        if not chunk:
            break
        hasher.update(chunk)

    file_obj.seek(0)
    return hasher.hexdigest()


def compute_sha256_from_bytes(data: bytes) -> str:
    """Compute SHA-256 hash directly from a bytes object."""
    return hashlib.sha256(data).hexdigest()


def _get_size(file_obj) -> int:
    """Return the size of a file-like object without changing its position."""
    current = file_obj.tell()
    file_obj.seek(0, 2)
    size = file_obj.tell()
    file_obj.seek(current)
    return size
