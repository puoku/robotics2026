# ПР03. Нода patrol

Среда: Docker, `osrf/ros:jazzy-desktop-full`, `ROS_DOMAIN_ID=16`. Опыт 01.10.2026.
Терминал A — `ros2 launch turtle_bringup sim.launch.py`, B — нода `patrol`, C — проверки.

## Что делает нода

- подписка на `/turtle1/pose` (`turtlesim/msg/Pose`), callback `on_pose` только сохраняет последнее сообщение в `self.pose`;
- таймер 0.1 с, callback `on_timer` публикует `geometry_msgs/msg/Twist` в относительный топик `cmd_vel`;
- команду выбирает функция `choose_command(pose)` из `patrol/command.py`: позы нет — `(0.0, 0.0)`, поза есть — `linear.x=0.5`, `angular.z=0.3`.

Подписка, издатель и таймер сохранены в полях объекта (`self.pose_sub`, `self.cmd_pub`, `self.timer`).

## Роли init, spin, callback и Ctrl+C

- `rclpy.init()` — запускает ROS в этом процессе (создаёт контекст). Без него ноду создать нельзя. Сюда же попадают аргументы запуска, в том числе remap из `--ros-args`.
- `rclpy.spin(node)` — цикл, который ждёт события (пришло сообщение, сработал таймер) и вызывает нужный callback. Пока spin не запущен, callback'и не вызываются, хотя подписка и таймер уже созданы.
- callback — функция, которую вызывает spin: `on_pose` при каждом сообщении позы, `on_timer` каждые 0.1 с. Callback'и короткие и выполняются по очереди в одном потоке.
- Ctrl+C — прерывает spin (KeyboardInterrupt), после этого в `finally` нода удаляется и ROS завершается. Нода при этом ничего не печатает и не отправляет команду остановки:

```
root@c8f8c6cbc218:/work# ros2 run patrol patrol
^Croot@c8f8c6cbc218:/work#
```

## Тесты

```
$ python3 -m pytest src/patrol/test
src/patrol/test/test_command.py ..
src/patrol/test/test_copyright.py s
src/patrol/test/test_flake8.py .
src/patrol/test/test_pep257.py .
4 passed, 1 skipped
```

Полный вывод в `tests.txt`. `test_command.py` — мои тесты `choose_command`: без позы и с обычной позой. Остальные три создал `ros2 pkg create` (стиль кода), copyright пропускается самим шаблоном.

## Сбой: относительный cmd_vel

Терминал B: `ros2 run patrol patrol`. Терминал C:

```
$ ros2 node list --no-daemon --spin-time 2
/patrol
/turtlesim
$ ros2 node info /patrol
/patrol
  Subscribers:
    /turtle1/pose: turtlesim/msg/Pose
  Publishers:
    /cmd_vel: geometry_msgs/msg/Twist
    /parameter_events: rcl_interfaces/msg/ParameterEvent
    /rosout: rcl_interfaces/msg/Log
  ...
$ ros2 topic info /cmd_vel --verbose
Type: geometry_msgs/msg/Twist

Publisher count: 1

Node name: patrol
Endpoint type: PUBLISHER
...

Subscription count: 0

$ ros2 topic info /turtle1/cmd_vel --verbose
Type: geometry_msgs/msg/Twist

Publisher count: 0

Subscription count: 1

Node name: turtlesim
Endpoint type: SUBSCRIPTION
...
$ ros2 topic echo /cmd_vel --once
linear:
  x: 0.5
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: 0.3
---
$ ros2 topic echo /turtle1/pose --once
x: 5.544444561004639
y: 5.544444561004639
theta: 0.0
linear_velocity: 0.0
angular_velocity: 0.0
---
```

Через 3 с поза та же. Нода работает: позу получает (команда уже 0.5 / 0.3, а не нулевая), публикует. Но относительное имя `cmd_vel` в корневом namespace превратилось в `/cmd_vel`, а turtlesim подписан на `/turtle1/cmd_vel`. У `/cmd_vel` подписчиков нет, черепаха стоит.

`node list` с `--spin-time 2` под эмуляцией нашёл обе ноды только с четвёртой попытки, `node info` и `topic info` тоже сработали со второго раза — discovery медленный.

## Исправление: remap

В B остановил ноду (Ctrl+C) и запустил с remap, код не менял:

```
$ ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
```

Терминал C:

```
$ ros2 node info /patrol
/patrol
  Subscribers:
    /turtle1/pose: turtlesim/msg/Pose
  Publishers:
    /parameter_events: rcl_interfaces/msg/ParameterEvent
    /rosout: rcl_interfaces/msg/Log
    /turtle1/cmd_vel: geometry_msgs/msg/Twist
$ ros2 topic info /cmd_vel --verbose
Unknown topic '/cmd_vel'
$ ros2 topic info /turtle1/cmd_vel --verbose
Type: geometry_msgs/msg/Twist

Publisher count: 1

Node name: patrol
Endpoint type: PUBLISHER
...

Subscription count: 1

Node name: turtlesim
Endpoint type: SUBSCRIPTION
...
$ ros2 topic echo /turtle1/pose --once
x: 3.9220128059387207
y: 7.609179973602295
theta: -1.8143706321716309
linear_velocity: 0.5
angular_velocity: 0.30000001192092896
---
```

Частота команды за 10 секунд (09:45:07–09:45:17):

```
$ timeout -s INT 10s ros2 topic hz /turtle1/cmd_vel
average rate: 10.012
	min: 0.098s max: 0.102s std dev: 0.00149s window: 11
...
average rate: 10.002
	min: 0.097s max: 0.103s std dev: 0.00128s window: 65
```

Около 10 Гц — соответствует таймеру 0.1 с. Поза после замера: `x: 7.195, y: 7.413`, скорости 0.5 и 0.3 — черепаха едет по кругу.

## Остановка

После Ctrl+C в B:

```
$ ros2 topic echo /turtle1/pose --once
x: 3.8880012035369873
y: 7.428396224975586
theta: -1.7039412260055542
linear_velocity: 0.0
angular_velocity: 0.0
---
$ ros2 topic info /turtle1/cmd_vel
Type: geometry_msgs/msg/Twist
Publisher count: 0
Subscription count: 1
```

Через 5 с поза та же. Нода при остановке нулевую команду не отправляет: процесс просто исчезает, и команды перестают приходить. Останавливается сам turtlesim — он перестаёт двигать черепаху, когда новых команд нет около секунды. То есть исчезновение издателя — это не команда «стоп», и остановку нужно проверять по позе, а не по тому, что процесса больше нет.

## До / сбой / после

| | Сбой | После remap |
|---|---|---|
| Запуск | `ros2 run patrol patrol` | `... --ros-args -r cmd_vel:=/turtle1/cmd_vel` |
| Топик издателя | `/cmd_vel` | `/turtle1/cmd_vel` |
| Подписчиков у него | 0 | 1 (`turtlesim`) |
| Поза | не меняется (5.544, 5.544) | меняется, скорости 0.5 / 0.3 |
| Частота команды | — | 10.0 Гц |

Причина сбоя — имя топика: относительное `cmd_vel` разрешается в `/cmd_vel`, а не в `/turtle1/cmd_vel`. Remap меняет имя при запуске, без правки кода.
