"""File path generation utilities."""
import os
import uuid
from django.utils import timezone


def generate_file_upload_path(instance, filename: str) -> str:
    """
    Generate a unique, collision-free upload path for a file.

    Path format: uploads/<year>/<month>/<uuid>/<original_filename>

    This structure:
    - Avoids directory listing issues at scale (files spread across date dirs)
    - Uses UUID to ensure uniqueness even for identical filenames
    - Preserves the original filename for human readability
    """
    today = timezone.now()
    unique_dir = str(uuid.uuid4())
    return os.path.join('uploads', str(today.year), f'{today.month:02d}', unique_dir, filename)
