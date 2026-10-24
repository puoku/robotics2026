# ПР06. Системы координат модели

Модель `src/course_description/urdf/vehicle.urdf.xacro`, размеры из `models/course_ackermann/model.sdf` (course kit v1-w07). Единицы СИ, оси по REP-103: x — вперёд, y — влево, z — вверх. Корень дерева — `base_link`, начало на оси колёс по центру машины.

Параметры Xacro: `wheel_base` 0.8 м, `track` 0.62 м, `wheel_radius` 0.12 м, `wheel_width` 0.07 м; корпус 1.05 × 0.52 × 0.22 м, центр на высоте 0.12 м, 12 кг.

## Связи

| Родитель | Дочернее звено | Сочленение | Ожидаемое преобразование (xyz, м; rpy = 0) | Публикует | Канал |
|---|---|---|---|---|---|
| `base_link` | `camera_link` | `camera_joint`, fixed | 0.28 0 0.38 | robot_state_publisher | `/tf_static` |
| `base_link` | `lidar_link` | `lidar_joint`, fixed | 0.28 0 0.38 | robot_state_publisher | `/tf_static` |
| `base_link` | `imu_link` | `imu_joint`, fixed | 0.28 0 0.38 | robot_state_publisher | `/tf_static` |
| `base_link` | `front_left_knuckle` | `front_left_steering_joint`, revolute z, ±0.55 рад | 0.4 0.31 0 + поворот рулём | robot_state_publisher по `/joint_states` | `/tf` |
| `base_link` | `front_right_knuckle` | `front_right_steering_joint`, revolute z, ±0.55 рад | 0.4 −0.31 0 + поворот рулём | robot_state_publisher по `/joint_states` | `/tf` |
| `front_left_knuckle` | `front_left_wheel` | `front_left_wheel_joint`, continuous y | 0 0 0 + вращение колеса | robot_state_publisher по `/joint_states` | `/tf` |
| `front_right_knuckle` | `front_right_wheel` | `front_right_wheel_joint`, continuous y | 0 0 0 + вращение колеса | robot_state_publisher по `/joint_states` | `/tf` |
| `base_link` | `rear_left_wheel` | `rear_left_wheel_joint`, continuous y | −0.4 0.31 0 + вращение колеса | robot_state_publisher по `/joint_states` | `/tf` |
| `base_link` | `rear_right_wheel` | `rear_right_wheel_joint`, continuous y | −0.4 −0.31 0 + вращение колеса | robot_state_publisher по `/joint_states` | `/tf` |

Камера, лидар и IMU стоят в одной точке, как в SDF курса. `odom → base_link` будет публиковать адаптер одометрии из ПР07 (contracts/topics.md), `map` пока нет — в этой работе их никто не публикует.

## Владельцы

Каждое преобразование публикует ровно один участник — `robot_state_publisher`:

- фиксированные звенья (камера, лидар, IMU) — один раз в `/tf_static` при старте, профиль reliable + transient local (см. `tf-qos.txt`);
- подвижные звенья (рулевые кулаки и колёса) — в `/tf`, только когда кто-то публикует `/joint_states`. В опыте их никто не публиковал, поэтому в `/tf` и в `view_frames` есть только три сенсора. Для RViz положения колёс на Mac публиковались вручную нулями через `ros2 topic pub /joint_states`.

Перед каждым новым запуском прежний launch останавливался, чтобы не было двух издателей `/tf_static`.

## Проверка на исправной модели

```
$ ros2 run tf2_ros tf2_echo base_link lidar_link
At time 0.0
- Translation: [0.280, 0.000, 0.380]
- Rotation: in Quaternion (xyzw) [0.000, 0.000, 0.000, 1.000]
$ ros2 run tf2_tools view_frames
camera_link: parent: 'base_link'
imu_link: parent: 'base_link'
lidar_link: parent: 'base_link'
$ ros2 topic echo /tf_static --once   (выборка полей)
frame_id: base_link  child_frame_id: camera_link  x: 0.28  z: 0.38
frame_id: base_link  child_frame_id: imu_link     x: 0.28  z: 0.38
frame_id: base_link  child_frame_id: lidar_link   x: 0.28  z: 0.38
```

Сначала `tf2_echo` пишет `frame does not exist` — буфер ещё пустой, через долю секунды преобразование приходит. Модель в RViz (Fixed Frame `base_link`): `rviz-model.png`.

## Дефект: lidar_link от camera_link

Коммит `3367f3e`: у `lidar_joint` родитель `camera_link`, offset тот же 0.28 0 0.38.

```
$ ros2 run tf2_ros tf2_echo base_link lidar_link
- Translation: [0.560, 0.000, 0.760]
$ ros2 run tf2_ros tf2_echo camera_link lidar_link
- Translation: [0.280, 0.000, 0.380]
$ ros2 run tf2_tools view_frames
camera_link: parent: 'base_link'
imu_link: parent: 'base_link'
lidar_link: parent: 'camera_link'
```

Offset задан относительно родителя, поэтому он прибавился к положению камеры: лидар оказался на 0.56 0 0.76 — на 0.28 м дальше вперёд и на 0.38 м выше настоящего места. Дерево при этом связное, `check_urdf` его принимает (`model-check.txt`), а ошибку ловят тесты ожидаемого parent и положения сенсора. Все данные лидара были бы привязаны к неверной точке.

## Исправление

Коммит `5af3d43` возвращает родителем `base_link`. Тот же тест:

```
$ ros2 run tf2_ros tf2_echo base_link lidar_link
- Translation: [0.280, 0.000, 0.380]
$ ros2 run tf2_ros tf2_echo camera_link lidar_link
- Translation: [0.000, 0.000, 0.000]
$ ros2 run tf2_tools view_frames
lidar_link: parent: 'base_link'
```

Графы `view_frames` до и после: `frames-before.gv`, `frames-after.gv`.
