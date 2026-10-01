def choose_command(pose):
    """Вернуть (linear_x, angular_z) по последней позе."""
    if pose is None:
        # позы ещё не было - стоим
        return 0.0, 0.0
    return 0.5, 0.3
