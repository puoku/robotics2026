from patrol.qos import make_qos
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from turtlesim.msg import Pose


class PoseRelay(Node):

    def __init__(self):
        super().__init__('pose_relay')
        self.pose_sub = self.create_subscription(
            Pose, '/turtle1/pose', self.on_pose, 10)
        # сенсорный поток: best_effort, имя относительное
        self.pose_pub = self.create_publisher(
            Pose, 'sensor_pose', make_qos('best_effort'))

    def on_pose(self, msg):
        self.pose_pub.publish(msg)


def main():
    rclpy.init()
    node = PoseRelay()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
