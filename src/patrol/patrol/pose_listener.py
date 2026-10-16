from patrol.qos import make_qos
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from turtlesim.msg import Pose


class PoseListener(Node):

    def __init__(self):
        super().__init__('pose_listener')
        reliability = self.declare_parameter('reliability', 'best_effort').value
        self.count = 0
        self.pose_sub = self.create_subscription(
            Pose, 'sensor_pose', self.on_pose, make_qos(reliability))
        self.timer = self.create_timer(2.0, self.report)
        self.get_logger().info(f'подписка на sensor_pose, {reliability}')

    def on_pose(self, msg):
        self.count += 1

    def report(self):
        self.get_logger().info(f'получено сообщений: {self.count}')


def main():
    rclpy.init()
    node = PoseListener()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
