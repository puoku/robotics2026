from geometry_msgs.msg import Twist
from patrol.command import check_param, choose_command, LIMITS
from rcl_interfaces.msg import SetParametersResult
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from turtlesim.msg import Pose


class Patrol(Node):

    def __init__(self):
        super().__init__('patrol')
        self.linear_speed = self.declare_parameter('linear_speed', 0.5).value
        self.turn_rate = self.declare_parameter('turn_rate', 0.3).value
        self.publish_hz = self.declare_parameter('publish_hz', 10.0).value
        self.pose = None
        self.pose_sub = self.create_subscription(
            Pose, '/turtle1/pose', self.on_pose, 10)
        # имя относительное, на /turtle1/cmd_vel переводится через remap
        self.cmd_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.timer = self.create_timer(1.0 / self.publish_hz, self.on_timer)
        self.add_on_set_parameters_callback(self.on_params)

    def on_pose(self, msg):
        self.pose = msg

    def on_timer(self):
        linear_x, angular_z = choose_command(
            self.pose, self.linear_speed, self.turn_rate)
        cmd = Twist()
        cmd.linear.x = linear_x
        cmd.angular.z = angular_z
        self.cmd_pub.publish(cmd)

    def on_params(self, params):
        # сначала проверяем все значения, состояние меняем только потом
        for p in params:
            if p.name in LIMITS:
                error = check_param(p.name, p.value)
                if error:
                    self.get_logger().warn(f'отклонено: {error}')
                    return SetParametersResult(successful=False, reason=error)
        for p in params:
            if p.name == 'linear_speed':
                self.linear_speed = p.value
            elif p.name == 'turn_rate':
                self.turn_rate = p.value
            elif p.name == 'publish_hz':
                self.set_rate(p.value)
        return SetParametersResult(successful=True)

    def set_rate(self, hz):
        period = 1.0 / hz
        # старый таймер удаляем, чтобы не работали два сразу
        self.destroy_timer(self.timer)
        self.timer = self.create_timer(period, self.on_timer)
        self.publish_hz = hz
        self.get_logger().info(f'publish_hz = {hz}, период {period:.3f} с')


def main():
    rclpy.init()
    node = Patrol()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
