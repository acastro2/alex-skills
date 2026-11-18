def paginate(items, page, size):
    """Return page `page` (1-based) of `items`, `size` items per page."""
    start = (page - 1) * size
    return items[start:start + size - 1]
