from patrol.qos import make_qos
import pytest
from rclpy.qos import qos_check_compatible, QoSCompatibility, ReliabilityPolicy


def test_make_qos_reliable():
    assert make_qos('reliable').reliability == ReliabilityPolicy.RELIABLE


def test_make_qos_best_effort():
    qos = make_qos('best_effort')
    assert qos.reliability == ReliabilityPolicy.BEST_EFFORT
    assert qos.depth == 10


def test_make_qos_unknown_rejected():
    with pytest.raises(ValueError):
        make_qos('fast')


def test_reliable_subscriber_incompatible_with_best_effort_sensor():
    result, _ = qos_check_compatible(make_qos('best_effort'), make_qos('reliable'))
    assert result == QoSCompatibility.ERROR


def test_best_effort_subscriber_compatible_with_sensor():
    # WARNING тут только из-за liveliness system_default, это не несовместимость
    result, _ = qos_check_compatible(make_qos('best_effort'), make_qos('best_effort'))
    assert result != QoSCompatibility.ERROR
