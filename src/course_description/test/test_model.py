import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest
import xacro

XACRO = os.path.join(os.path.dirname(__file__), '..', 'urdf', 'vehicle.urdf.xacro')
SENSORS = ['camera_link', 'lidar_link', 'imu_link']


def load():
    return ET.fromstring(xacro.process_file(XACRO).toxml())


def parents(robot):
    return {j.find('child').get('link'): j.find('parent').get('link')
            for j in robot.findall('joint')}


def offset(robot, child):
    for j in robot.findall('joint'):
        if j.find('child').get('link') == child:
            return [float(v) for v in j.find('origin').get('xyz').split()]
    raise KeyError(child)


def position_in_base(robot, link):
    # углы у фиксированных звеньев нулевые, поэтому смещения просто складываются
    par = parents(robot)
    pos = [0.0, 0.0, 0.0]
    while link != 'base_link':
        pos = [a + b for a, b in zip(pos, offset(robot, link))]
        link = par[link]
    return pos


def test_single_root_is_base_link():
    robot = load()
    links = {link.get('name') for link in robot.findall('link')}
    assert links - set(parents(robot)) == {'base_link'}


def test_tree_connected_and_acyclic():
    robot = load()
    par = parents(robot)
    links = [link.get('name') for link in robot.findall('link')]
    for link in links:
        seen = set()
        while link != 'base_link':
            assert link not in seen, f'цикл через {link}'
            seen.add(link)
            assert link in par, f'{link} не связан с base_link'
            link = par[link]


def test_sensors_present():
    links = {link.get('name') for link in load().findall('link')}
    assert set(SENSORS) <= links


def test_lidar_parent_is_base_link():
    assert parents(load())['lidar_link'] == 'base_link'


def test_sensor_positions_in_base_link():
    robot = load()
    for sensor in SENSORS:
        assert position_in_base(robot, sensor) == pytest.approx([0.28, 0.0, 0.38])


def test_wheels_match_parameters():
    robot = load()
    assert position_in_base(robot, 'front_left_wheel') == pytest.approx([0.4, 0.31, 0.0])
    assert position_in_base(robot, 'rear_right_wheel') == pytest.approx([-0.4, -0.31, 0.0])
    radius = {float(c.get('radius')) for c in robot.iter('cylinder')
              if c.get('length') == '0.07'}
    assert radius == {0.12}


def test_visual_and_collision_separate():
    robot = load()
    for link in robot.findall('link'):
        if link.find('visual') is not None:
            assert link.find('collision') is not None, link.get('name')


def test_inertia_physically_valid():
    for link in load().findall('link'):
        inertial = link.find('inertial')
        assert inertial is not None, link.get('name')
        assert float(inertial.find('mass').get('value')) > 0
        i = inertial.find('inertia')
        ixx, iyy, izz = (float(i.get(k)) for k in ('ixx', 'iyy', 'izz'))
        assert min(ixx, iyy, izz) > 0, link.get('name')
        # неравенство треугольника для главных моментов
        assert ixx + iyy >= izz and iyy + izz >= ixx and ixx + izz >= iyy, link.get('name')


@pytest.mark.skipif(shutil.which('check_urdf') is None, reason='нет check_urdf')
def test_check_urdf(tmp_path):
    urdf = tmp_path / 'vehicle.urdf'
    urdf.write_text(xacro.process_file(XACRO).toxml())
    result = subprocess.run(['check_urdf', str(urdf)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'root Link: base_link' in result.stdout
