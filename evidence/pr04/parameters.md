# ПР04. Параметры patrol

Среда: Docker, `osrf/ros:jazzy-desktop-full`, `ROS_DOMAIN_ID=16`. Опыт 12.10.2026.
Терминал A — `ros2 launch turtle_bringup sim.launch.py`, B — `ros2 run patrol patrol --ros-args -r cmd_vel:=/turtle1/cmd_vel`, C — команды ниже.

## Что сделано в коде

- параметры `linear_speed` (0.5), `turn_rate` (0.3), `publish_hz` (10.0) объявлены в `__init__`;
- `check_param(name, value)` в `patrol/command.py` — чистая функция: значение должно быть конечным числом в пределах `linear_speed` 0–1, `turn_rate` −1–1, `publish_hz` 1–30. Возвращает текст ошибки или `None`;
- `on_params` — callback `add_on_set_parameters_callback`. Сначала проверяет все пришедшие значения, и только если все допустимы, меняет поля и таймер. Иначе возвращает `successful=False` с причиной, состояние не трогает;
- `set_rate(hz)` — удаляет старый таймер (`destroy_timer`) и создаёт новый с периодом `1/publish_hz`, так что одновременно работает один таймер.

Коммиты: `e909964` — параметры с проверкой, `a42be7c` — проверка частоты временно отключена (дефект), `099dae5` — проверка возвращена (это коммит реализации в `report.json`).

## 1. Исправная версия (e909964)

```
$ ros2 param list /patrol
  linear_speed
  publish_hz
  start_type_description_service
  turn_rate
  use_sim_time
$ ros2 param get /patrol linear_speed
Double value is: 0.5
$ ros2 param get /patrol turn_rate
Double value is: 0.3
$ ros2 param get /patrol publish_hz
Double value is: 10.0
$ timeout -s INT 10s ros2 topic hz /turtle1/cmd_vel
average rate: 10.000
	min: 0.096s max: 0.102s std dev: 0.00139s window: 65
$ ros2 param set /patrol publish_hz 5.0
Set parameter successful
$ timeout -s INT 10s ros2 topic hz /turtle1/cmd_vel
average rate: 5.001
	min: 0.197s max: 0.203s std dev: 0.00182s window: 31
$ ros2 param set /patrol publish_hz 0.0
Setting parameter failed: publish_hz: допустимо от 1.0 до 30.0, получено 0.0
$ ros2 param set /patrol publish_hz -5.0
Setting parameter failed: publish_hz: допустимо от 1.0 до 30.0, получено -5.0
$ ros2 param get /patrol publish_hz
Double value is: 5.0
$ timeout -s INT 10s ros2 topic hz /turtle1/cmd_vel
average rate: 5.001
	min: 0.197s max: 0.203s std dev: 0.00220s window: 31
$ ros2 param set /patrol linear_speed 1.5
Setting parameter failed: linear_speed: допустимо от 0.0 до 1.0, получено 1.5
$ ros2 param set /patrol linear_speed 0.2
Set parameter successful
$ ros2 topic echo /turtle1/cmd_vel --once
linear:
  x: 0.2
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: 0.3
---
```

Первый `ros2 param list /patrol` ответил `Node not found` (discovery ещё не закончился), повтор выдал список выше.

Вывод ноды в терминале B:

```
[INFO] [1791793057.769298093] [patrol]: publish_hz = 5.0, период 0.200 с
[WARN] [1791793069.634120251] [patrol]: отклонено: publish_hz: допустимо от 1.0 до 30.0, получено 0.0
[WARN] [1791793072.870038461] [patrol]: отклонено: publish_hz: допустимо от 1.0 до 30.0, получено -5.0
[WARN] [1791793088.006359218] [patrol]: отклонено: linear_speed: допустимо от 0.0 до 1.0, получено 1.5
```

10 → 5 Гц меняет поток, 0 и −5 отклонены, частота осталась 5. Смена `linear_speed` сразу видна в команде.

## 2. Сбой: проверка частоты отключена (a42be7c)

В `check_param` добавлено:

```python
    if name == 'publish_hz':
        return None  # временно: проверка частоты отключена
```

Те же тесты на этой версии:

```
$ python3 -m pytest src/patrol/test
FAILED src/patrol/test/test_command.py::test_zero_rate_rejected - AssertionEr...
FAILED src/patrol/test/test_command.py::test_negative_rate_rejected - Asserti...
FAILED src/patrol/test/test_command.py::test_nan_rate_rejected - AssertionErr...
==================== 3 failed, 7 passed, 1 skipped in 0.28s ====================
```

Пересобрал, в B перезапустил ноду. Терминал C:

```
$ ros2 param get /patrol publish_hz
Double value is: 10.0
$ timeout -s INT 10s ros2 topic hz /turtle1/cmd_vel
average rate: 9.999
	min: 0.097s max: 0.103s std dev: 0.00137s window: 64
$ timeout 20s ros2 param set /patrol publish_hz 0.0
!rclpy.ok()
exit=124
$ ros2 node list --no-daemon --spin-time 2
/turtlesim
$ ros2 topic info /turtle1/cmd_vel
Type: geometry_msgs/msg/Twist
Publisher count: 0
Subscription count: 1
$ timeout -s INT 6s ros2 topic hz /turtle1/cmd_vel
WARNING: topic [/turtle1/cmd_vel] does not appear to be published yet
$ ros2 topic echo /turtle1/pose --once
x: 3.7772984504699707
y: 7.315724849700928
theta: -1.343882441520691
linear_velocity: 0.0
angular_velocity: 0.0
---
```

Терминал B (конец вывода):

```
  File "/work/build/patrol/patrol/patrol.py", line 50, in on_params
    self.set_rate(p.value)
  File "/work/build/patrol/patrol/patrol.py", line 54, in set_rate
    period = 1.0 / hz
             ~~~~^~~~
ZeroDivisionError: float division by zero
[ros2run]: Process exited with failure 1
```

Ноль прошёл мимо проверки, `set_rate` попытался посчитать период `1.0 / 0.0`. Исключение вылетело из callback параметров прямо в `rclpy.spin`, и нода завершилась. `ros2 param set` ответа не дождался (сервис параметров умер вместе с нодой, `timeout` дал 124), `/patrol` пропала из графа, издателей у `/turtle1/cmd_vel` нет, черепаха остановилась.

## 3. Проверка возвращена (099dae5)

Те же тесты: `10 passed, 1 skipped` (полный вывод в `tests.txt`). Пересобрал, в B перезапустил ноду. Терминал C, тот же опыт:

```
$ ros2 param get /patrol publish_hz
Double value is: 10.0
$ ros2 param set /patrol publish_hz 5.0
Set parameter successful
$ timeout -s INT 10s ros2 topic hz /turtle1/cmd_vel
average rate: 5.000
	min: 0.198s max: 0.203s std dev: 0.00148s window: 31
$ timeout 20s ros2 param set /patrol publish_hz 0.0
Setting parameter failed: publish_hz: допустимо от 1.0 до 30.0, получено 0.0
exit=0
$ ros2 param get /patrol publish_hz
Double value is: 5.0
$ timeout -s INT 10s ros2 topic hz /turtle1/cmd_vel
average rate: 5.002
	min: 0.198s max: 0.202s std dev: 0.00147s window: 31
```

Терминал B:

```
[INFO] [1791793419.315562761] [patrol]: publish_hz = 5.0, период 0.200 с
[WARN] [1791793431.202940877] [patrol]: отклонено: publish_hz: допустимо от 1.0 до 30.0, получено 0.0
```

Ноль отклонён до изменения таймера: значение осталось 5.0, поток тот же 5 Гц, нода жива. `ros2 node list --no-daemon --spin-time 2` в этот момент показал только `/turtlesim` — discovery под эмуляцией не успел, при этом поток команд от `/patrol` шёл (5.002 Гц).

## Сравнение

| | Исправная | Проверка отключена | Проверка возвращена |
|---|---|---|---|
| `publish_hz 5.0` | принято, 5.0 Гц | — | принято, 5.0 Гц |
| `publish_hz 0.0` | отклонено | нода упала, `ZeroDivisionError` | отклонено |
| `publish_hz` после нуля | 5.0 | ноды нет | 5.0 |
| Поток `/turtle1/cmd_vel` | 5.0 Гц | нет издателя | 5.0 Гц |
| Тесты 0 / −5 / NaN | проходят | 3 падают | проходят |

## Сервис /clear и действие rotate_absolute

```
$ ros2 service type /clear
std_srvs/srv/Empty
$ ros2 service call /clear std_srvs/srv/Empty
waiting for service to become available...
requester: making request: std_srvs.srv.Empty_Request()

response:
std_srvs.srv.Empty_Response()

$ ros2 action list -t
/turtle1/rotate_absolute [turtlesim/action/RotateAbsolute]
$ ros2 action info /turtle1/rotate_absolute
Action: /turtle1/rotate_absolute
Action clients: 0
Action servers: 1
    /turtlesim
$ ros2 interface show turtlesim/action/RotateAbsolute
# The desired heading in radians
float32 theta
---
# The angular displacement in radians to the starting position
float32 delta
---
# The remaining rotation in radians
float32 remaining
```

Запрос сервиса — это один вызов и один ответ: `/clear` очищает след и сразу отвечает, промежуточных сообщений нет. Цель действия выполняется долго: сервер принимает цель (поворот к `theta`), во время выполнения шлёт feedback (`remaining`), в конце возвращает результат (`delta`), а цель можно отменить.
