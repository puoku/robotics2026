# Робототехника — практические работы

Среда: Docker, образ `osrf/ros:jazzy-desktop-full` (Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic).
Хост — macOS на Apple Silicon, образ запускается через эмуляцию amd64.

## Подготовка

Course kit `v1-w02` скачивается со страницы курса «Инструменты и входные файлы» и распаковывается в `.course-kit/` (в git не попадает):

```bash
mkdir -p .course-kit
tar -xzf robotics-course-kit-v1.tar.gz -C .course-kit
```

Контейнер запускается один раз из корня репозитория, репозиторий монтируется в `/work`:

```bash
docker pull --platform linux/amd64 osrf/ros:jazzy-desktop-full
docker run -d --name pr01 --platform linux/amd64 \
  -v "$PWD":/work -w /work -e QT_QPA_PLATFORM=offscreen \
  osrf/ros:jazzy-desktop-full sleep infinity
```

Окна у turtlesim нет (`QT_QPA_PLATFORM=offscreen`), поза публикуется как обычно.

Каждый терминал открывается в этом же контейнере:

```bash
docker exec -it pr01 bash
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

Остановить контейнер: `docker rm -f pr01`.
