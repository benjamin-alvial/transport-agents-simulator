def format_time(time_in_seconds: float) -> str:
    """Format a simulation time (in seconds) as a human-readable string.

    Args:
        time_in_seconds: Absolute simulation time in seconds.

    Returns:
        A string of the form ``"Xs"``, ``"XmYs"``, or ``"XhYmZs"``.
    """
    if time_in_seconds < 60:
        return f"{time_in_seconds:.1f}s"
    if time_in_seconds < 3600:
        m = int(time_in_seconds // 60)
        s = time_in_seconds % 60
        return f"{m}m{s:04.1f}s"
    h = int(time_in_seconds // 3600)
    m = int((time_in_seconds % 3600) // 60)
    s = time_in_seconds % 60
    return f"{h}h{m:02d}m{s:04.1f}s"
