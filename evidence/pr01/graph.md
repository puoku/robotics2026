# ПР01. Граф ROS 2

Среда: Docker, образ `osrf/ros:jazzy-desktop-full` (Ubuntu 24.04, ROS 2 Jazzy, `rmw_fastrtps_cpp`), хост macOS на M4, образ работает через эмуляцию amd64.
Все три терминала открыты в одном контейнере (`docker exec -it pr01 bash`). Опыт проведён 21.09.2026, домены 16 и 17.

## 1. Исправный граф (все в домене 16)

Терминал A: `ros2 run turtlesim turtlesim_node`, терминал B: `ros2 run turtlesim turtle_teleop_key`. Стрелками в B черепаха двигалась. Терминал C:

```
$ ros2 node list --no-daemon --spin-time 2
/teleop_turtle
/turtlesim
```

Под эмуляцией двух секунд на discovery хватает не всегда: первые запуски вернули пустой список, после повтора появились обе ноды.

```
$ ros2 topic list -t
/parameter_events [rcl_interfaces/msg/ParameterEvent]
/rosout [rcl_interfaces/msg/Log]
/turtle1/cmd_vel [geometry_msgs/msg/Twist]
/turtle1/color_sensor [turtlesim/msg/Color]
/turtle1/pose [turtlesim/msg/Pose]
```

```
$ ros2 node info /turtlesim
/turtlesim
  Subscribers:
    /parameter_events: rcl_interfaces/msg/ParameterEvent
    /turtle1/cmd_vel: geometry_msgs/msg/Twist
  Publishers:
    /parameter_events: rcl_interfaces/msg/ParameterEvent
    /rosout: rcl_interfaces/msg/Log
    /turtle1/color_sensor: turtlesim/msg/Color
    /turtle1/pose: turtlesim/msg/Pose
  Service Servers:
    /clear: std_srvs/srv/Empty
    /kill: turtlesim/srv/Kill
    /reset: std_srvs/srv/Empty
    /spawn: turtlesim/srv/Spawn
    /turtle1/set_pen: turtlesim/srv/SetPen
    /turtle1/teleport_absolute: turtlesim/srv/TeleportAbsolute
    /turtle1/teleport_relative: turtlesim/srv/TeleportRelative
    /turtlesim/describe_parameters: rcl_interfaces/srv/DescribeParameters
    /turtlesim/get_parameter_types: rcl_interfaces/srv/GetParameterTypes
    /turtlesim/get_parameters: rcl_interfaces/srv/GetParameters
    /turtlesim/get_type_description: type_description_interfaces/srv/GetTypeDescription
    /turtlesim/list_parameters: rcl_interfaces/srv/ListParameters
    /turtlesim/set_parameters: rcl_interfaces/srv/SetParameters
    /turtlesim/set_parameters_atomically: rcl_interfaces/srv/SetParametersAtomically
  Service Clients:

  Action Servers:
    /turtle1/rotate_absolute: turtlesim/action/RotateAbsolute
  Action Clients:

$ ros2 topic type /turtle1/pose
turtlesim/msg/Pose
$ POSE_TYPE=$(ros2 topic type /turtle1/pose)
$ ros2 topic echo /turtle1/pose --once
x: 8.986166954040527
y: 3.0984725952148438
theta: -0.41600000858306885
linear_velocity: 0.0
angular_velocity: 0.0
---
```

Черепаха уже не в центре (старт около 5.54, 5.54) — её сдвинули стрелками.

### Ноды и роли

| Нода | Роль |
|---|---|
| `/turtlesim` | симулятор: подписан на `/turtle1/cmd_vel`, публикует позу `/turtle1/pose` и `/turtle1/color_sensor`, даёт сервисы (`/spawn`, `/kill`, `/reset` и др.) |
| `/teleop_turtle` | читает стрелки с клавиатуры и публикует команды скорости в `/turtle1/cmd_vel` |

### Топики

| Топик | Тип | Публикует | Подписан |
|---|---|---|---|
| `/turtle1/cmd_vel` | `geometry_msgs/msg/Twist` | `/teleop_turtle` | `/turtlesim` |
| `/turtle1/pose` | `turtlesim/msg/Pose` | `/turtlesim` | в опыте — CLI (`echo`, `hz`) |
| `/turtle1/color_sensor` | `turtlesim/msg/Color` | `/turtlesim` | — |
| `/rosout` | `rcl_interfaces/msg/Log` | ноды (логи) | — |
| `/parameter_events` | `rcl_interfaces/msg/ParameterEvent` | ноды | ноды |

### Частота /turtle1/pose

`ros2 topic hz /turtle1/pose` работал 15 с (15:27:11–15:27:26), остановлен сигналом INT, как Ctrl+C. Последний вывод:

```
average rate: 62.488
	min: 0.011s max: 0.022s std dev: 0.00206s window: 757
```

Итого около 62.5 Гц, это совпадает с таймером turtlesim 16 мс. Поза публикуется и когда черепаха стоит.

## 2. Сбой: teleop в домене 17

В B остановил teleop (Ctrl+C) и запустил заново с `export ROS_DOMAIN_ID=17`. Стрелки черепаху больше не двигают. Симулятор в A всё время в домене 16. Терминал C:

```
$ export ROS_DOMAIN_ID=17
$ ros2 node list --no-daemon --spin-time 2
/teleop_turtle
$ ros2 topic info /turtle1/cmd_vel
Type: geometry_msgs/msg/Twist
Publisher count: 1
Subscription count: 0
$ timeout 5s ros2 topic echo /turtle1/pose "$POSE_TYPE" --once > evidence/pr01/pose-broken.txt 2>&1
$ printf 'exit=%s\n' "$?"
exit=124
```

`/teleop_turtle` виден, `/turtlesim` нет. Поза за 5 секунд не пришла, `exit=124` — это истечение таймаута, файл `pose-broken.txt` пустой.
Тот же топик из домена 16 в это же время:

```
$ ros2 topic info /turtle1/cmd_vel
Type: geometry_msgs/msg/Twist
Publisher count: 0
Subscription count: 1
$ ros2 topic echo /turtle1/pose --once
x: 8.986166954040527
y: 3.0984725952148438
theta: -0.41600000858306885
linear_velocity: 0.0
angular_velocity: 0.0
---
```

Команды teleop уходят в домен 17, где их никто не читает, а симулятор в 16 их не получает. Поза не изменилась, хотя стрелки в B нажимались.

## 3. Восстановление: teleop снова в домене 16

В B снова Ctrl+C, `export ROS_DOMAIN_ID=16`, запуск teleop. В C тот же тест, поменял только домен и имя файла:

```
$ export ROS_DOMAIN_ID=16
$ ros2 node list --no-daemon --spin-time 2
/teleop_turtle
/turtlesim
$ ros2 topic info /turtle1/cmd_vel
Type: geometry_msgs/msg/Twist
Publisher count: 1
Subscription count: 1
$ timeout 5s ros2 topic echo /turtle1/pose "$POSE_TYPE" --once > evidence/pr01/pose-fixed.txt 2>&1
$ printf 'exit=%s\n' "$?"
exit=0
```

Первый `node list` показал только `/teleop_turtle`, повтор — обе ноды. В `pose-fixed.txt` пришла поза `x: 7.146…, y: 1.640…` — черепаха снова поехала от стрелок.

## Сравнение

| | До | Сбой | После |
|---|---|---|---|
| Домен A (turtlesim) | 16 | 16 | 16 |
| Домен B (teleop) | 16 | 17 | 16 |
| Домен C (проверка) | 16 | 17 | 16 |
| `node list` в домене C | обе ноды | только `/teleop_turtle` | обе ноды |
| `/turtle1/cmd_vel` в домене 16 (pub/sub) | — | 0 / 1 | 1 / 1 |
| Поза в C | пришла | не пришла, `exit=124` | пришла, `exit=0` |
| Стрелки двигают черепаху | да | нет | да |

## Почему так

`ROS_DOMAIN_ID` — номер домена DDS. Участники находят друг друга только внутри одного домена (у разных доменов разные порты discovery), поэтому teleop и CLI в домене 17 не видят симулятор из 16, и сообщения между ними не ходят.
Домен читается при старте ноды, `export` на уже работающую ноду не влияет. Поэтому teleop пришлось перезапускать после каждой смены домена, а симулятор всё время работал в 16 и его трогать было не нужно. Установка ROS тоже ни при чём: всё ПО то же самое, поменялось только значение переменной у одного участника.
Тип позы в чужом домене передан явно (`$POSE_TYPE`): издателя там нет, и CLI не у кого узнать тип топика.
