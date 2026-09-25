# ПР02. Команды и наблюдения

Среда: Docker, `osrf/ros:jazzy-desktop-full`, репозиторий смонтирован в `/work`, `ROS_DOMAIN_ID=16`. Опыт 25.09.2026.

## 1. Корень работы

```
$ cd "$(git rev-parse --show-toplevel)"
$ pwd
/work
$ ls -a
.
..
.course-kit
.git
.github
.gitignore
AI_USAGE.md
README.md
evidence
robotics-course-kit-v1-w03-7fbfd3e8161a.tar.gz
robotics-course-kit-v1-w03-7fbfd3e8161a.tar.gz.sha256.txt
$ mkdir -p src evidence/pr02
$ printenv ROS_DISTRO ROS_DOMAIN_ID
jazzy
16
$ ros2 pkg prefix turtlesim
/opt/ros/jazzy
```

`ros2 pkg prefix turtlesim` — где установлен пакет turtlesim (`/opt/ros/jazzy`), а `pwd` — где я сейчас нахожусь (корень репозитория). Это разные вещи.

### Три команды Linux

| Команда | Зачем | Результат |
|---|---|---|
| `pwd` | показать текущий каталог | `/work` — корень репозитория, он же корень workspace |
| `mkdir -p src evidence/pr02` | создать каталоги, в том числе вложенные, без ошибки если уже есть | появились `src/` и `evidence/pr02/` |
| `colcon build ... 2>&1 \| tee evidence/pr02/build-empty.txt` | собрать пакет, вывод показать в терминале и сразу записать в файл | сборка прошла, лог в `build-empty.txt` |

`>` перенаправляет вывод команды в файл (файл перезаписывается), на экран при этом ничего не идёт. `|` передаёт вывод одной команды на вход другой, например в `tee`, который и показывает его, и пишет в файл. `2>&1` добавляет к выводу ещё и stderr.

`source` выполняет файл в текущем shell, поэтому переменные окружения (`ROS_DISTRO`, пути к пакетам) остаются в этом терминале. Обычный запуск программы создаёт новый процесс, и его переменные пропадают вместе с ним.

## 2. Пустой пакет

```
$ cd src
$ ros2 pkg create --build-type ament_python --license Apache-2.0 turtle_bringup --dependencies launch launch_ros turtlesim
$ cd ..
$ ls src/turtle_bringup
LICENSE
package.xml
resource
setup.cfg
setup.py
test
turtle_bringup
```

В `package.xml` и `setup.py` заменил описание и сопровождающего (генератор поставил `root` и `TODO`).

```
$ set -o pipefail
$ colcon build --symlink-install --packages-select turtle_bringup 2>&1 | tee evidence/pr02/build-empty.txt
Starting >>> turtle_bringup
Finished <<< turtle_bringup [1.23s]

Summary: 1 package finished [1.34s]
$ source install/setup.bash
$ ros2 pkg prefix turtle_bringup
/work/install/turtle_bringup
```

Пакет найден в `install` моего workspace, но нода не появилась: сборка и `source` процессы не запускают.

## 3. Launch-файл

Добавил `launch/sim.launch.py` и строку для него в `data_files` в `setup.py`, пересобрал:

```
$ colcon build --symlink-install --packages-select turtle_bringup 2>&1 | tee evidence/pr02/build.txt
Starting >>> turtle_bringup
Finished <<< turtle_bringup [1.19s]

Summary: 1 package finished [1.28s]
$ ls "$(ros2 pkg prefix turtle_bringup)/share/turtle_bringup/launch"
sim.launch.py
```

Терминал A: `ros2 launch turtle_bringup sim.launch.py`. Окна нет: в Docker на macOS turtlesim работает с `QT_QPA_PLATFORM=offscreen`, других экземпляров turtlesim перед запуском не было. Проверка в C:

```
$ ros2 node list --no-daemon --spin-time 2
/turtlesim
$ ps -eo pid,args | grep -E "ros2 launch|turtlesim_node"
  181 /usr/bin/python3 /opt/ros/jazzy/bin/ros2 launch turtle_bringup sim.launch.py
  184 /opt/ros/jazzy/lib/turtlesim/turtlesim_node --ros-args
```

Launch (pid 181) запустил turtlesim_node (pid 184). Остановка Ctrl+C в A:

```
^C[WARNING] [launch]: user interrupted with ctrl-c (SIGINT)
[turtlesim_node-1] [INFO] [1790323541.620243793] [rclcpp]: signal_handler(SIGINT/SIGTERM)
[INFO] [turtlesim_node-1]: process has finished cleanly [pid 184]
```

После остановки `ros2 node list --no-daemon --spin-time 2` пустой, процессов launch и turtlesim_node нет — turtlesim завершился вместе с launch. Для опыта ниже launch запущен снова.

Файл `sim.launch.py` в `src` — это только текст на диске. После сборки он лежит в `install/.../share/turtle_bringup/launch`, и его находит `ros2 launch`. Нода `/turtlesim` — это уже запущенный процесс, а сообщения идут между нодами по топикам в графе.

## 4. Команда и движение

```
$ ros2 topic type /turtle1/pose
turtlesim/msg/Pose
$ ros2 topic echo /turtle1/pose --once
x: 5.544444561004639
y: 5.544444561004639
theta: 0.0
linear_velocity: 0.0
angular_velocity: 0.0
---
```

Первый вызов `ros2 topic type` сразу после запуска вернул пустоту — discovery ещё не завершился, повтор через несколько секунд дал тип.

Терминал B:

```
$ ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist '{linear: {x: 1.0}, angular: {z: 0.5}}'
```

Ожидал: вперёд со скоростью 1 и поворот налево — x растёт, y немного растёт, theta около 0.5. Поза после:

```
x: 6.509308815002441
y: 5.796990871429443
theta: 0.5040000081062317
linear_velocity: 0.0
angular_velocity: 0.0
```

Через 2 с поза та же — после одной команды черепаха проехала около секунды и остановилась.

## 5. Ошибка в имени топика

Терминал B, издатель на `/cmd_vel`:

```
$ ros2 topic pub --rate 1 --wait-matching-subscriptions 0 /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 1.0}, angular: {z: 0.5}}'
```

Терминал C:

```
$ ros2 topic info /cmd_vel --verbose
Type: geometry_msgs/msg/Twist

Publisher count: 1

Node name: _ros2cli_497
Node namespace: /
Topic type: geometry_msgs/msg/Twist
Endpoint type: PUBLISHER
...

Subscription count: 0

$ ros2 topic info /turtle1/cmd_vel --verbose
Type: geometry_msgs/msg/Twist

Publisher count: 0

Subscription count: 1

Node name: turtlesim
Node namespace: /
Topic type: geometry_msgs/msg/Twist
Endpoint type: SUBSCRIPTION
...
```

Поза не меняется (x 6.509, y 5.797, скорости 0), черепаха стоит.

Исправлено только имя топика, скорость и домен те же:

```
$ ros2 topic pub --rate 1 --wait-matching-subscriptions 0 /turtle1/cmd_vel geometry_msgs/msg/Twist '{linear: {x: 1.0}, angular: {z: 0.5}}'
```

```
$ ros2 topic info /cmd_vel --verbose
Unknown topic '/cmd_vel'
$ ros2 topic info /turtle1/cmd_vel --verbose
Type: geometry_msgs/msg/Twist

Publisher count: 1

Node name: _ros2cli_630
Endpoint type: PUBLISHER
...

Subscription count: 1

Node name: turtlesim
Endpoint type: SUBSCRIPTION
...
```

Поза раз в пару секунд (`ros2 topic echo /turtle1/pose --once`, числа округлены):

```
x: 7.516  y: 7.827  theta: 1.709   linear_velocity: 1.0  angular_velocity: 0.5
x: 5.418  y: 9.541  theta: -3.086  linear_velocity: 1.0  angular_velocity: 0.5
x: 3.536  y: 7.560  theta: -1.582  linear_velocity: 1.0  angular_velocity: 0.5
```

Черепаха едет по кругу. После Ctrl+C в B поза застыла (x 5.860, y 5.571, скорости 0).

В `ros2 node list` издателя из CLI не видно: имя `_ros2cli_...` начинается с `_`, такие ноды скрыты без `-a`. Его видно в `ros2 topic info --verbose`.

### До / сбой / после

| | До (одна команда) | Сбой | После |
|---|---|---|---|
| Топик издателя | `/turtle1/cmd_vel` | `/cmd_vel` | `/turtle1/cmd_vel` |
| Тип | Twist | Twist | Twist |
| Подписчиков у топика издателя | 1 | 0 | 1 |
| Черепаха | проехала дугу | стоит | едет по кругу |

### Почему правильного типа недостаточно

Издатель и подписчик соединяются, только если совпадают и полное имя топика, и тип (и совместим QoS). Discovery работает: издатель на `/cmd_vel` виден в графе, turtlesim тоже виден. Но turtlesim подписан на `/turtle1/cmd_vel`, а `/cmd_vel` — другой топик, на который никто не подписан, поэтому сообщения никому не доставляются. Обнаружение участников и доставка сообщений — разные вещи: видеть друг друга мало, нужен общий топик.
