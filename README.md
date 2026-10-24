# Робототехника — практические работы

Среда: Docker, образ `osrf/ros:jazzy-desktop-full` (Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic).
Хост — macOS на Apple Silicon, образ запускается через эмуляцию amd64.

## Подготовка

Course kit текущей недели (сейчас `v1-w07`) скачивается со страницы курса «Инструменты и входные файлы» и распаковывается в `.course-kit/` (в git не попадает):

```bash
mkdir -p .course-kit
tar -xzf robotics-course-kit-v1-w07-9b7fdd5424d3.tar.gz -C .course-kit
```

Контейнер запускается один раз из корня репозитория, репозиторий монтируется в `/work`:

```bash
docker pull --platform linux/amd64 osrf/ros:jazzy-desktop-full
docker run -d --name ros --platform linux/amd64 \
  -v "$PWD":/work -w /work -e QT_QPA_PLATFORM=offscreen \
  osrf/ros:jazzy-desktop-full sleep infinity
```

Окна у turtlesim нет (`QT_QPA_PLATFORM=offscreen`), поза публикуется как обычно.

Каждый терминал открывается в этом же контейнере:

```bash
docker exec -it ros bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=16
```

## ПР01. Окружение и граф ROS 2

Отчёт среды (терминал C):

```bash
mkdir -p evidence/pr01
ros2 doctor --report > evidence/pr01/doctor.txt 2>&1
```

Исправный граф:

```bash
# терминал A
ros2 run turtlesim turtlesim_node
# терминал B
ros2 run turtlesim turtle_teleop_key
# терминал C
ros2 node list --no-daemon --spin-time 2
ros2 topic list -t
ros2 node info /turtlesim
ros2 topic type /turtle1/pose
POSE_TYPE=$(ros2 topic type /turtle1/pose)
ros2 topic echo /turtle1/pose --once
ros2 topic hz /turtle1/pose   # не меньше 10 секунд, потом Ctrl+C
```

Разрыв связи: в B остановить teleop и запустить в домене 17, в C проверить из домена 17.

```bash
# терминал B
export ROS_DOMAIN_ID=17
ros2 run turtlesim turtle_teleop_key
# терминал C
export ROS_DOMAIN_ID=17
ros2 node list --no-daemon --spin-time 2
timeout 5s ros2 topic echo /turtle1/pose "$POSE_TYPE" --once > evidence/pr01/pose-broken.txt 2>&1
printf 'exit=%s\n' "$?"
```

Ожидается `exit=124`: поза не пришла за 5 секунд.

Восстановление: вернуть домен 16 в B (перезапустить teleop) и повторить ту же проверку в C.

```bash
# терминал B
export ROS_DOMAIN_ID=16
ros2 run turtlesim turtle_teleop_key
# терминал C
export ROS_DOMAIN_ID=16
ros2 node list --no-daemon --spin-time 2
timeout 5s ros2 topic echo /turtle1/pose "$POSE_TYPE" --once > evidence/pr01/pose-fixed.txt 2>&1
printf 'exit=%s\n' "$?"
```

Ожидается `exit=0`.

Проверка на хосте из корня репозитория:

```bash
python3 -m json.tool evidence/pr01/environment.json > /dev/null
python3 .course-kit/v1/tools/check_practice.py PR01 --submission .
```


## ПР02. Пакет turtle_bringup и launch

Workspace — корень репозитория, пакет лежит в `src/turtle_bringup`, запускает turtlesim через `launch/sim.launch.py`.

Пакет создан командой:

```bash
cd src
ros2 pkg create --build-type ament_python --license Apache-2.0 \
  turtle_bringup --dependencies launch launch_ros turtlesim
cd ..
```

Сборка (в терминале, где подключена только `/opt/ros/jazzy/setup.bash`):

```bash
set -o pipefail
colcon build --symlink-install --packages-select turtle_bringup \
  2>&1 | tee evidence/pr02/build.txt
```

Терминал A — запуск:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=16
ros2 pkg prefix turtle_bringup
ls "$(ros2 pkg prefix turtle_bringup)/share/turtle_bringup/launch"
ros2 launch turtle_bringup sim.launch.py
```

Терминал C — проверка графа и позы:

```bash
ros2 node list --no-daemon --spin-time 2
ros2 interface show geometry_msgs/msg/Twist
ros2 topic type /turtle1/pose
ros2 topic echo /turtle1/pose --once
```

Терминал B — одна команда движения, после неё в C снова `ros2 topic echo /turtle1/pose --once`:

```bash
ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 1.0}, angular: {z: 0.5}}'
```

Сбой: издатель на неправильном топике `/cmd_vel`, черепаха не двигается.

```bash
# терминал B
ros2 topic pub --rate 1 --wait-matching-subscriptions 0 \
  /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 1.0}, angular: {z: 0.5}}'
# терминал C
ros2 topic info /cmd_vel --verbose
ros2 topic info /turtle1/cmd_vel --verbose
```

Ожидается: у `/cmd_vel` 1 издатель и 0 подписчиков, у `/turtle1/cmd_vel` 0 издателей и 1 подписчик (`turtlesim`).

Исправление: в B остановить издателя (Ctrl+C), заменить только имя на `/turtle1/cmd_vel` и повторить ту же проверку в C. Ожидается 1 издатель и 1 подписчик на `/turtle1/cmd_vel`, черепаха едет по кругу. После остановки издателя черепаха останавливается.

Проверка на хосте из корня репозитория:

```bash
python3 -m py_compile src/turtle_bringup/launch/sim.launch.py
python3 .course-kit/v1/tools/check_practice.py PR02 --submission .
```

## ПР03. Нода patrol

Пакет `src/patrol`: нода `/patrol` подписана на `/turtle1/pose` и по таймеру 0.1 с публикует `Twist` в относительный топик `cmd_vel`. Пока позы нет — нулевая команда, после первой позы — `linear.x=0.5`, `angular.z=0.3`. Выбор команды вынесен в функцию `choose_command` (`patrol/command.py`), тесты в `test/test_command.py`.

Пакет создан командой:

```bash
cd src
ros2 pkg create --build-type ament_python --node-name patrol patrol \
  --dependencies rclpy geometry_msgs
cd ..
```

Сборка и тесты:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select turtle_bringup patrol
source install/setup.bash
python3 -m pytest src/patrol/test 2>&1 | tee evidence/pr03/tests.txt
```

Терминал A — turtlesim:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=16
ros2 launch turtle_bringup sim.launch.py
```

Сбой: нода без remap публикует в `/cmd_vel`, черепаха стоит.

```bash
# терминал B
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=16
ros2 run patrol patrol
# терминал C
ros2 node list --no-daemon --spin-time 2
ros2 topic info /cmd_vel --verbose
ros2 topic info /turtle1/cmd_vel --verbose
ros2 topic echo /turtle1/pose --once
```

Исправление: в B остановить ноду (Ctrl+C) и запустить с remap, в C повторить проверку и измерить частоту команды за 10 секунд.

```bash
# терминал B
ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel
# терминал C
ros2 topic info /turtle1/cmd_vel --verbose
ros2 topic echo /turtle1/pose --once
timeout -s INT 10s ros2 topic hz /turtle1/cmd_vel
```

Ожидается около 10 Гц, черепаха едет по кругу. После Ctrl+C в B черепаха останавливается.

Проверка на хосте из корня репозитория:

```bash
python3 .course-kit/v1/tools/check_practice.py PR03 --submission .
```

## ПР04. Параметры patrol

У ноды `/patrol` три параметра:

| Параметр | По умолчанию | Допустимо |
|---|---|---|
| `linear_speed` | 0.5 | 0 … 1 |
| `turn_rate` | 0.3 | −1 … 1 |
| `publish_hz` | 10.0 | 1 … 30 |

Значения проверяет функция `check_param` (`patrol/command.py`) до того, как нода что-то меняет. Недопустимое значение отклоняется, прежнее остаётся. При смене `publish_hz` старый таймер удаляется и создаётся новый с периодом `1/publish_hz`.

Сборка и тесты:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select turtle_bringup patrol
source install/setup.bash
python3 -m pytest src/patrol/test 2>&1 | tee evidence/pr04/tests.txt
```

Запуск: в A `ros2 launch turtle_bringup sim.launch.py`, в B `ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel`. В C:

```bash
ros2 param list /patrol
ros2 param get /patrol publish_hz
timeout -s INT 10s ros2 topic hz /turtle1/cmd_vel
ros2 param set /patrol publish_hz 5.0
timeout -s INT 10s ros2 topic hz /turtle1/cmd_vel
ros2 param set /patrol publish_hz 0.0
ros2 param get /patrol publish_hz
timeout -s INT 10s ros2 topic hz /turtle1/cmd_vel
```

Ожидается: 10 Гц, после `5.0` — 5 Гц, `0.0` отклонён (`Setting parameter failed`), частота остаётся 5.

Сервис и действие turtlesim:

```bash
ros2 service call /clear std_srvs/srv/Empty
ros2 action list -t
```

Проверка на хосте из корня репозитория:

```bash
python3 .course-kit/v1/tools/check_practice.py PR04 --submission .
```

## ПР05. Launch, QoS и запись

Пакет `src/course_bringup` с `launch/patrol.launch.py` поднимает систему одной командой: глобальный turtlesim и в пространстве имён (`robot_a` по умолчанию) ноды `patrol`, `pose_relay` и `pose_listener`. Ноды из `src/patrol`:

- `pose_relay` читает `/turtle1/pose` и публикует относительный `sensor_pose` с QoS best_effort;
- `pose_listener` подписан на `sensor_pose`, надёжность задаётся параметром `reliability`, раз в 2 с пишет число полученных сообщений;
- профиль QoS собирает функция `make_qos` (`patrol/qos.py`), тесты в `test/test_qos.py`.

Аргументы launch: `namespace` (robot_a), `subscriber_reliability` (best_effort), `record` (false), `bag_dir` (evidence/pr05/bag). Выход `cmd_vel` у patrol переназначен на `/turtle1/cmd_vel`. При `record:=true` запускается `ros2 bag record -s mcap` для `/<namespace>/sensor_pose`.

Сборка и тесты:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select turtle_bringup patrol course_bringup
source install/setup.bash
colcon test --packages-select patrol course_bringup
colcon test-result --verbose
```

Сбой: reliable-подписчик против best_effort-сенсора (терминал A — launch, C — проверки):

```bash
# A
ros2 launch course_bringup patrol.launch.py \
  namespace:=robot_a subscriber_reliability:=reliable record:=false
# C
ros2 topic list
ros2 topic info -v /robot_a/sensor_pose
timeout 10s ros2 topic echo /robot_a/sensor_pose --qos-reliability reliable --once
```

Ожидается: топик виден, сообщений нет (timeout, код 124), в логах launch предупреждение `incompatible QoS ... RELIABILITY`, `pose_listener` пишет `получено сообщений: 0`.

Исправление и запись:

```bash
# A
ros2 launch course_bringup patrol.launch.py \
  namespace:=robot_a subscriber_reliability:=best_effort \
  record:=true bag_dir:=evidence/pr05/bag
# C
timeout 10s ros2 topic echo /robot_a/sensor_pose --qos-reliability best_effort --once
```

После Ctrl+C в A запись закрывается. Повтор той же записи:

```bash
# A
ros2 bag play evidence/pr05/bag --loop \
  --qos-profile-overrides-path config/qos-overrides.yaml
# C
timeout 10s ros2 topic echo /robot_a/sensor_pose --qos-reliability reliable --once
timeout 10s ros2 topic echo /robot_a/sensor_pose --qos-reliability best_effort --once
ros2 bag info evidence/pr05/bag
```

`timeout 10s` вместо 3 с: под эмуляцией amd64 сам запуск `ros2 topic echo` занимает около 1.7 с.

Проверка на хосте из корня репозитория:

```bash
python3 .course-kit/v1/tools/check_practice.py PR05 --submission .
```

## ПР06. Модель робота и tf2

Пакет `src/course_description`: `urdf/vehicle.urdf.xacro` — Ackermann-робот по размерам из `models/course_ackermann/model.sdf` (база 0.8 м, колея 0.62 м, радиус колеса 0.12 м), корень дерева `base_link`, сенсоры `camera_link`, `lidar_link`, `imu_link` на фиксированных сочленениях. `launch/display.launch.py` запускает `robot_state_publisher` с развёрнутым Xacro, при `rviz:=true` — ещё RViz. Структурные тесты модели в `test/test_model.py`.

Сборка, проверка модели и тесты:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select course_description
source install/setup.bash
xacro src/course_description/urdf/vehicle.urdf.xacro > /tmp/vehicle.urdf
check_urdf /tmp/vehicle.urdf
colcon test --packages-select course_description
colcon test-result --verbose
```

Терминал A — `ros2 launch course_description display.launch.py`. Терминал C:

```bash
ros2 topic info /tf_static --verbose
timeout 10 ros2 topic echo /tf_static tf2_msgs/msg/TFMessage --once \
  --qos-durability transient_local --qos-reliability reliable
timeout 10 ros2 topic echo /tf_static tf2_msgs/msg/TFMessage --once \
  --qos-durability volatile --qos-reliability reliable
ros2 run tf2_ros tf2_echo base_link lidar_link
ros2 run tf2_tools view_frames
```

Ожидается: `/tf_static` reliable + transient local; поздний подписчик transient local получает преобразования (exit 0), volatile — нет (exit 124); `lidar_link` в `base_link` на `0.28 0 0.38`. Тип указан явно и таймаут 10 с: под эмуляцией CLI не всегда успевает определить тип за 4 с.

RViz (на macOS через RoboStack, в Docker нет экрана), из корня репозитория:

```bash
ros2 run robot_state_publisher robot_state_publisher --ros-args \
  -p robot_description:="$(xacro src/course_description/urdf/vehicle.urdf.xacro)"
rviz2 -d src/course_description/rviz/vehicle.rviz
```

Проверка на хосте из корня репозитория:

```bash
python3 .course-kit/v1/tools/check_practice.py PR06 --submission .
```

Остановить контейнер: `docker rm -f ros`.
