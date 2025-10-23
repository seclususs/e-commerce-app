import json
from flask import Flask


def format_rupiah(value):
    try:
        val = float(value)
        return f"Rp {val:,.0f}".replace(',', '.')
    except (ValueError, TypeError, AttributeError):
        return "Rp 0"

def format_percentage(part, whole):
    try:
        part = float(part)
        whole = float(whole)
        if whole == 0:
            return 0
        percentage = round(100 * (whole - part) / whole)
        return max(0, percentage)
    except (ValueError, TypeError):
        return 0

def fromjson_safe_filter(json_str):
    try:
        if not json_str:
            return []
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return []

def tojson_safe_filter(obj):
    try:
        return json.dumps(obj)
    except TypeError:
        return 'null'

def split_filter(value, delimiter):
    if not isinstance(value, str):
        return value
    return value.split(delimiter)

def status_translate_filter(status_en):
    status_map = {
        'Pending': 'Menunggu Pembayaran',
        'Processing': 'Diproses',
        'Shipped': 'Dikirim',
        'Completed': 'Selesai',
        'Cancelled': 'Dibatalkan',
        'Menunggu Pembayaran': 'Menunggu Pembayaran',
        'Diproses': 'Diproses',
        'Dikirim': 'Dikirim',
        'Selesai': 'Selesai',
        'Dibatalkan': 'Dibatalkan',
    }
    return status_map.get(status_en, status_en)

def status_class_filter(status_en):
    class_map = {
        'Pending': 'pending',
        'Processing': 'processing',
        'Shipped': 'shipped',
        'Completed': 'completed',
        'Cancelled': 'cancelled',
        'Menunggu Pembayaran': 'pending',
        'Diproses': 'processing',
        'Dikirim': 'shipped',
        'Selesai': 'completed',
        'Dibatalkan': 'cancelled',
    }
    return class_map.get(status_en, 'pending')

def register_template_filters(app: Flask):
    app.template_filter('rupiah')(format_rupiah)
    app.template_filter('percentage')(format_percentage)
    app.template_filter('tojson_safe')(tojson_safe_filter)
    app.template_filter('fromjson_safe')(fromjson_safe_filter)
    app.template_filter('split')(split_filter)
    app.template_filter('status_translate')(status_translate_filter)
    app.template_filter('status_class')(status_class_filter)