from datetime import datetime, timedelta

def get_date_range(period_str, custom_start=None, custom_end=None):
    """
    Mendapatkan rentang tanggal mulai dan selesai berdasarkan string periode atau input kustom.
    
    :param period_str: String periode seperti 'last_7_days', 'last_30_days', 'this_month', atau 'custom'.
    :param custom_start: Tanggal mulai kustom dalam format YYYY-MM-DD.
    :param custom_end: Tanggal selesai kustom dalam format YYYY-MM-DD.
    :return: Tuple berisi (start_date_string, end_date_string).
    """
    if custom_start and custom_end:
        start_date_str = f"{custom_start} 00:00:00"
        end_date_str = f"{custom_end} 23:59:59"
        return start_date_str, end_date_str

    today = datetime.now()
    if period_str == 'last_30_days':
        start_date = today - timedelta(days=29)
        end_date = today
    elif period_str == 'this_month':
        start_date = today.replace(day=1)
        end_date = today
    else:  # Default ke 7 hari terakhir
        start_date = today - timedelta(days=6)
        end_date = today
        
    return start_date.strftime('%Y-%m-%d 00:00:00'), end_date.strftime('%Y-%m-%d 23:59:59')