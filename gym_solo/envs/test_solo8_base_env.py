from gym_solo.envs import Solo8BaseEnv
import unittest

from parameterized import parameterized
from unittest import mock

import importlib
import pybullet as p
import pybullet_utils.bullet_client as bc

from gym_solo.core import configs


class SimpleSoloEnv(Solo8BaseEnv):
  def __init__(self, *args, **kwargs):
    self.reset_call = None
    self.load_bodies_call = None

    super().__init__(*args, **kwargs)

  def reset(self, init_call: bool):
    self.reset_call = init_call
  
  def load_bodies(self):
    self.load_bodies_call = True


class TestSolo8BaseEnv(unittest.TestCase):
  def setUp(self):
    with mock.patch('pybullet_utils.bullet_client.BulletClient') as self.mock_client:
      self.env = SimpleSoloEnv(configs.Solo8BaseConfig(), False)

  def tearDown(self):
    self.env._close()

  def test_abstract_init(self):
    with self.assertRaises(TypeError):
      env = Solo8BaseEnv()

  def test_init(self):
    config = configs.Solo8BaseConfig()
    gui = False

    with mock.patch('pybullet_utils.bullet_client.BulletClient') as mock_client:
      env = SimpleSoloEnv(config, gui)

    with self.subTest('config'):
      self.assertEqual(env.config, config)
    
    # with self.subTest('client'):
    #   mock_client.setAdditionalSearchPath.assert_called_once()

  @parameterized.expand([
    ('nogui', False, p.DIRECT),
    ('gui', True, p.GUI),
  ])
  @mock.patch('pybullet_utils.bullet_client.BulletClient')
  def test_GUI(self, name, use_gui, expected_ui, mock_client):
    env = SimpleSoloEnv(configs.Solo8BaseConfig(), use_gui)

    mock_client.assert_called_with(connection_mode=expected_ui)
    self.assertTrue(env.load_bodies_call)
    self.assertTrue(env.reset_call)

  def test_seed(self):
    seed = 69
    self.env._seed(seed)

    import numpy as np
    import random
    
    numpy_control = float(np.random.rand(1))
    random_control = random.random()

    with self.subTest('random seed'):
      importlib.reload(np)
      importlib.reload(random)

      self.assertNotEqual(numpy_control, float(np.random.rand(1)))
      self.assertNotEqual(random_control, random.random())

    with self.subTest('same seed'):
      importlib.reload(np)
      importlib.reload(random)

      self.env._seed(seed)

      self.assertEqual(numpy_control, float(np.random.rand(1)))
      self.assertEqual(random_control, random.random())


if __name__ == '__main__':
  unittest.main() 