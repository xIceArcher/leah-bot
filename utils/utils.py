from datetime import timedelta


def format_time_delta(td: timedelta):
    total_seconds = td.total_seconds()

    total_minutes, seconds = divmod(total_seconds, 60)
    total_hours, minutes = divmod(total_minutes, 60)
    days, hours = divmod(total_hours, 24)

    time_string = ''

    if days:
        time_string += f'{int(days)}d '

    if hours:
        time_string += f'{int(hours)}h '

    if minutes:
        time_string += f'{int(minutes)}m '

    if seconds:
        time_string += f'{int(seconds)}s'

    return time_string.strip()
