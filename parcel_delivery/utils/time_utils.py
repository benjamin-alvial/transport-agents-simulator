def format_time(time_in_seconds: float) -> str:
    if time_in_seconds < 60:
        formatted_time = f"{time_in_seconds:.1f}s"
    elif time_in_seconds < 3600:
        m = int(time_in_seconds // 60)
        s = time_in_seconds % 60
        formatted_time = f"{m}m{s:04.1f}s"
    else:
        h = int(time_in_seconds // 3600)
        m = int((time_in_seconds % 3600) // 60)
        s = time_in_seconds % 60
        formatted_time = f"{h}h{m:02d}m{s:04.1f}s"
    return formatted_time