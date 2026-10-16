from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

RELIABILITY = {
    'reliable': ReliabilityPolicy.RELIABLE,
    'best_effort': ReliabilityPolicy.BEST_EFFORT,
}


def make_qos(reliability, depth=10):
    """Вернуть профиль QoS по имени политики надёжности."""
    if reliability not in RELIABILITY:
        raise ValueError(
            f'reliability: ожидается reliable или best_effort, '
            f'получено {reliability}')
    return QoSProfile(
        reliability=RELIABILITY[reliability],
        history=HistoryPolicy.KEEP_LAST,
        depth=depth)
