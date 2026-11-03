"""Dependency-free reusable candidate parts, extracted and rewritten for CBDK."""
import re
from pathlib import Path

_WINDOWS_RESERVED = {'CON', 'PRN', 'AUX', 'NUL'} | {f'COM{i}' for i in range(1, 10)} | {f'LPT{i}' for i in range(1, 10)}


def sanitize_filename(name: str, *, max_chars: int = 120) -> str:
    """Turn a label into a Windows-safe filename segment (not a whole path)."""
    if max_chars < 1:
        raise ValueError('max_chars must be positive')
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', (name or 'Object').strip()).rstrip(' .')
    clean = clean[:max_chars].rstrip(' .') or 'Object'
    if clean.split('.')[0].upper() in _WINDOWS_RESERVED:
        clean = ('_' + clean)[:max_chars]
    return clean


def unique_filename(directory: Path, stem: str, ext: str) -> Path:
    """Return an unused filename; reservation/write must handle races separately."""
    directory = Path(directory)
    base = sanitize_filename(stem)
    extension = ext if ext.startswith('.') else '.' + ext
    candidate = directory / (base + extension)
    index = 1
    while candidate.exists():
        candidate = directory / f'{base}_{index}{extension}'
        index += 1
    return candidate
