from patrol.command import choose_command
from turtlesim.msg import Pose


def test_no_pose_gives_zero_command():
    assert choose_command(None) == (0.0, 0.0)


def test_pose_gives_forward_and_turn():
    pose = Pose(x=5.5, y=5.5, theta=0.0)
    assert choose_command(pose) == (0.5, 0.3)
