# ПР02. Типы сообщений

Типы взяты из `ros2 topic list -t` и `ros2 topic type` в моей среде (Jazzy).

| Топик | Тип | Кто публикует | Кто подписан | Зачем |
|---|---|---|---|---|
| `/turtle1/cmd_vel` | `geometry_msgs/msg/Twist` | teleop или `ros2 topic pub` | `/turtlesim` | команда скорости |
| `/turtle1/pose` | `turtlesim/msg/Pose` | `/turtlesim` | в опыте — `ros2 topic echo` | текущая поза черепахи |

## geometry_msgs/msg/Twist

```
$ ros2 interface show geometry_msgs/msg/Twist
# This expresses velocity in free space broken into its linear and angular parts.

Vector3  linear
	float64 x
	float64 y
	float64 z
Vector3  angular
	float64 x
	float64 y
	float64 z
```

- `linear` — линейная скорость по осям x, y, z. В опыте задавался только `linear.x` — вперёд/назад по направлению черепахи, остальные поля нулевые.
- `angular` — угловая скорость вокруг осей x, y, z, рад/с. Для поворота на плоскости нужен только `angular.z`: плюс — налево (против часовой), минус — направо.

В опыте `{linear: {x: 1.0}, angular: {z: 0.5}}` — вперёд со скоростью 1 и поворот налево 0.5 рад/с, получается движение по дуге.

## turtlesim/msg/Pose

```
x: 5.544444561004639
y: 5.544444561004639
theta: 0.0
linear_velocity: 0.0
angular_velocity: 0.0
```

`x`, `y` — координаты черепахи, `theta` — угол поворота в радианах, `linear_velocity` и `angular_velocity` — текущие скорости.
