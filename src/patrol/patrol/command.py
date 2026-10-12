import math

# допустимые значения параметров: (минимум, максимум)
LIMITS = {
    'linear_speed': (0.0, 1.0),
    'turn_rate': (-1.0, 1.0),
    'publish_hz': (1.0, 30.0),
}


def choose_command(pose, linear_speed=0.5, turn_rate=0.3):
    """Вернуть (linear_x, angular_z) по последней позе."""
    if pose is None:
        # позы ещё не было - стоим
        return 0.0, 0.0
    return linear_speed, turn_rate


def check_param(name, value):
    """Вернуть текст ошибки или None, если значение допустимо."""
    low, high = LIMITS[name]
    if not math.isfinite(value):
        return f'{name}: значение должно быть конечным числом'
    if not low <= value <= high:
        return f'{name}: допустимо от {low} до {high}, получено {value}'
    return None
