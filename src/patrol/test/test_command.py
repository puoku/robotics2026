import math

from patrol.command import check_param, choose_command
from turtlesim.msg import Pose


def test_no_pose_gives_zero_command():
    assert choose_command(None) == (0.0, 0.0)


def test_pose_gives_forward_and_turn():
    pose = Pose(x=5.5, y=5.5, theta=0.0)
    assert choose_command(pose) == (0.5, 0.3)


def test_command_uses_parameters():
    pose = Pose(x=5.5, y=5.5, theta=0.0)
    assert choose_command(pose, 0.2, -0.4) == (0.2, -0.4)


def test_rate_change_10_to_5_allowed():
    assert check_param('publish_hz', 10.0) is None
    assert check_param('publish_hz', 5.0) is None


def test_zero_rate_rejected():
    assert check_param('publish_hz', 0.0) is not None


def test_negative_rate_rejected():
    assert check_param('publish_hz', -5.0) is not None


def test_nan_rate_rejected():
    assert check_param('publish_hz', math.nan) is not None


def test_speed_and_turn_limits():
    assert check_param('linear_speed', 1.0) is None
    assert check_param('linear_speed', 1.5) is not None
    assert check_param('turn_rate', -1.0) is None
    assert check_param('turn_rate', -2.0) is not None
