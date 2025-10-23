from datetime import datetime, timedelta


def get_date_range(period_str, custom_start=None, custom_end=None):
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
    else:
        start_date = today - timedelta(days=6)
        end_date = today

    return start_date.strftime('%Y-%m-%d 00:00:00'), end_date.strftime('%Y-%m-%d 23:59:59')