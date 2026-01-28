def safe_file_url(file_field):
    if not file_field:
        return None
    try:
        return file_field.url
    except Exception:
        return None
