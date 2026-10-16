from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, GroupAction, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description():
    namespace = LaunchConfiguration('namespace')
    record = LaunchConfiguration('record')
    bag_dir = LaunchConfiguration('bag_dir')
    reliability = LaunchConfiguration('subscriber_reliability')

    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='robot_a'),
        DeclareLaunchArgument('record', default_value='false'),
        DeclareLaunchArgument('bag_dir', default_value='evidence/pr05/bag'),
        DeclareLaunchArgument('subscriber_reliability', default_value='best_effort'),
        LogInfo(msg=['namespace: ', namespace,
                     ', subscriber_reliability: ', reliability,
                     ', record: ', record]),
        # один turtlesim на всю систему, без namespace
        Node(package='turtlesim', executable='turtlesim_node', output='screen'),
        GroupAction([
            PushRosNamespace(namespace),
            Node(package='patrol', executable='patrol', output='screen',
                 remappings=[('cmd_vel', '/turtle1/cmd_vel')]),
            Node(package='patrol', executable='pose_relay', output='screen'),
            Node(package='patrol', executable='pose_listener', output='screen',
                 parameters=[{'reliability': reliability}]),
        ]),
        ExecuteProcess(
            cmd=['ros2', 'bag', 'record', '-s', 'mcap', '-o', bag_dir,
                 '--topics', ['/', namespace, '/sensor_pose']],
            output='screen',
            condition=IfCondition(record)),
    ])
