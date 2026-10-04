# Робототехника — практические работы

Среда: Docker, образ `osrf/ros:jazzy-desktop-full` (Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic).
Хост — macOS на Apple Silicon, образ запускается через эмуляцию amd64.

## Подготовка

Course kit текущей недели (сейчас `v1-w03`) скачивается со страницы курса «Инструменты и входные файлы» и распаковывается в `.course-kit/` (в git не попадает):

```bash
mkdir -p .course-kit
tar -xzf robotics-course-kit-v1-w03-7fbfd3e8161a.tar.gz -C .course-kit
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

Остановить контейнер: `docker rm -f ros`.
