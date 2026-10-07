from rest_framework.views import exception_handler


def handler(exc, context):
    """Bentuk error seragam: {"success": false, "error": "...", "detail": ...}."""
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    if isinstance(data, dict) and 'detail' in data and len(data) == 1:
        msg = str(data['detail'])
        detail = None
    else:
        msg = 'Data tidak valid.' if response.status_code == 400 else 'Permintaan gagal.'
        detail = data
    response.data = {'success': False, 'error': msg, 'detail': detail}
    return response
