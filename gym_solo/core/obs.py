from abc import ABC, abstractmethod

from pybullet_utils import bullet_client
from typing import List, Tuple

import pybullet as p
import numpy as np
import math

import gym
from gym import spaces

from gym_solo import solo_types


class Observation(ABC):
  """An observation for a body in the pybullet simulation.

  Attributes:
    _client: The PyBullet client for the instance. Will be set via a
      property setter.
  """
  _client: bullet_client.BulletClient = None

  @abstractmethod
  def __init__(self, body_id: int):
    """Create a new Observation.
    
    Note that for every child of this class, each one *needs* to specify
    which pybullet body id they would like to track the observation for.

    Args:
      body_id (int): PyBullet body id to get the observation for.
    """
    pass
  
  @property
  @abstractmethod
  def observation_space(self) -> spaces.Space:
    """Get the observation space of the Observation.

    Returns:
      spaces.Space: The observation space.
    """
    pass

  @property
  @abstractmethod
  def labels(self) -> List[str]:
    """A list of labels corresponding to the observation.
    
    i.e. if the observation was [1, 2, 3], and the labels were ['a', 'b', 'c'],
    then a = 1, b = 2, c = 3.

    Returns:
      List[str]: Labels, where the index is the same as its respective 
      observation.
    """
    pass

  @abstractmethod
  def compute(self) -> solo_types.obs:
    """Compute the observation for the current state.

    Returns:
      solo_types.obs: Specified observation for the current state.
    """
    pass

  @property
  def client(self) -> bullet_client.BulletClient:
    """Get the Observation's physics client.

    Raises:
      ValueError: If the PyBullet client hasn't been set yet.

    Returns:
      bullet_client.BulletClient: The active client for the observation.
    """
    if not self._client:
      raise ValueError('PyBullet client needs to be set')
    return self._client

  @client.setter
  def client(self, client: bullet_client.BulletClient):
    """Set the Observation's physics client.

    Args:
      client (bullet_client.BulletClient): The client to use for the 
        observation.
    """
    self._client = client


class ObservationFactory:
  def __init__(self, client: bullet_client.BulletClient):
    """Create a new Observation Factory.

    Args:
      client (bullet_client.BulletClient): Pybullet client to perform 
        calculations.
    """
    self._client = client
    self._observations = []
    self._obs_space = None

  def register_observation(self, obs: Observation):
    """Add an observation to be computed.

    Args:
      obs (Observation): Observation to be tracked.
    """
    obs.client = self._client

    lbl_len = len(obs.labels)
    obs_space_len = len(obs.observation_space.low)
    obs_len = obs.compute().size

    if lbl_len != obs_space_len:
      raise ValueError('Labels have length {} != obs space len {}'.format(
        lbl_len, obs_space_len))
    if lbl_len != obs_len:
      raise ValueError('Labels have length {} != obs len {}'.format(
        lbl_len, obs_len))
    
    self._observations.append(obs)

  def get_obs(self) -> Tuple[solo_types.obs, List[str]]:
    """Get all of the observations for the current state.

    Returns:
      Tuple[solo_types.obs, List[str]]: The observations and associated labels.
        len(observations) == len(labels) and labels[i] corresponds to the
        i-th observation.
    """
    if not self._observations:
      raise ValueError('Need to register at least one observation instance')

    all_obs = [] 
    all_labels = []
    
    for obs in self._observations:
      all_obs.append(obs.compute())
      all_labels.append(obs.labels)

    observations = np.concatenate(all_obs)
    labels = [l for lbl in all_labels for l in lbl]

    return observations, labels

  def get_observation_space(self, generate=False) -> spaces.Box:
    """Get the combined observation space of all of the registered observations.

    Args:
      generate (bool, optional): Whether or not to regenerate the observation
        space or just used the cached ersion. Note that some Observations
        might dynamically generate their observation space, so this could be a
        potentially expensive operation. Defaults to False.

    Raises:
      ValueError: If no observations are registered.

    Returns:
      spaces.Box: The observation space of the registered Observations.
    """
    if not self._observations:
      raise ValueError('Can\'t generate an empty observation space')
    if self._obs_space and not generate:
      return self._obs_space

    lower, upper = [], []
    for obs in self._observations:
      lower.extend(obs.observation_space.low)
      upper.extend(obs.observation_space.high)

    self._obs_space = spaces.Box(low=np.array(lower), high=np.array(upper))
    return self._obs_space


class TorsoIMU(Observation):
  """Get the orientation and velocities of the Solo 8 torso.

  Attributes:
    labels (List[str]): The labels associated with the outputted observation
    robot (int): PyBullet BodyId for the robot.
  """
  # TODO: Add angular acceleration to support production IMUs
  labels: List[str] = ['θx', 'θy', 'θz', 'vx', 'vy', 'vz', 'wx', 'wy', 'wz']

  def __init__(self, body_id: int, degrees: bool = False):
    """Create a new TorsoIMU observation

    Args:
      body_id (int): The PyBullet body id for the robot.
      degrees (bool, optional): Whether or not to return angles in degrees. 
        Defaults to False.
    """
    self.robot = body_id
    self._degrees = degrees

  @property
  def observation_space(self) -> spaces.Box:
    """Get the observation space for the IMU mounted on the Torso. 

    The IMU in this case return the orientation of the torso (x, y, z angles),
    the linear velocity (vx, vy, vz), and the angular velocity (wx, wy, wz). 
    Note that the range for the angle measurements is [-180, 180] degrees. This
    value can be toggled between degrees and radians at instantiation.

    Returns:
      spaces.Box: The observation space corresponding to (θx, θy, θz, vx, vy, 
        vz, wx, wy, wz)
    """
    angle_min = -180. if self._degrees else -np.pi
    angle_max = 180. if self._degrees else np.pi

    lower = [angle_min, angle_min, angle_min,  # Orientation
             -np.inf, -np.inf, -np.inf,        # Linear Velocity
             -np.inf, -np.inf, -np.inf]        # Angular Velocity

    upper = [angle_max, angle_max, angle_max,  # Same as above
             np.inf, np.inf, np.inf,          
             np.inf, np.inf, np.inf]         

    return spaces.Box(low=np.array(lower), high=np.array(upper))

  def compute(self) -> solo_types.obs:
    """Compute the torso IMU values for a state.

    Returns:
      solo_types.obs: The observation for the current state (accessed via
        pybullet)
    """
    _, orien_quat = self.client.getBasePositionAndOrientation(self.robot)

    # Orien is in (x, y, z)
    orien = np.array(self.client.getEulerFromQuaternion(orien_quat))

    v_lin, v_ang = self.client.getBaseVelocity(self.robot)
    v_lin = np.array(v_lin) 
    v_ang = np.array(v_ang)

    if self._degrees:
      orien = np.degrees(orien)
      v_ang = np.degrees(v_ang)

    return np.concatenate([orien, v_lin, v_ang])



class MotorEncoder(Observation):
  """Get the position of the all the joints
  """

  def __init__(self, body_id: int, degrees: bool = False):
    """Create a new MotorEncoder observation

    Args:
      body_id (int): The PyBullet body id for the robot.
      degrees (bool, optional): Whether or not to return angles in degrees. 
        Defaults to False.
    """
    self.robot = body_id
    self._degrees = degrees

  @property
  def _num_joints(self):
    return self.client.getNumJoints(self.robot)
  
  @property
  def observation_space(self) -> spaces.Space:
    """Gets the observation space for the joints

    Returns:
      spaces.Space: The observation space corresponding to the labels
    """
    lower, upper = [], []

    for joint in range(self._num_joints):
      joint_info = self.client.getJointInfo(self.robot, joint)
      lower.append(joint_info[8])
      upper.append(joint_info[9])

    lower = np.array(lower)
    upper = np.array(upper)

    if self._degrees:
      lower = np.degrees(lower)
      upper = np.degrees(upper)

    return spaces.Box(low=lower, high=upper)

  @property
  def labels(self) -> List[str]:
    """A list of labels corresponding to the observation.

    Returns:
      List[str]: Labels, where the index is the same as its respective 
      observation.
    """
    return [self.client.getJointInfo(self.robot, joint)[1].decode('UTF-8') 
            for joint in range(self._num_joints)]

  def compute(self) -> solo_types.obs:
    """Computes the motor position values all the joints of the robot 
    for the current state.

    Returns:
      solo_types.obs: The observation extracted from pybullet
    """
    joint_values = np.array([self.client.getJointState(self.robot, i)[0] 
                             for i in range(self._num_joints)])

    if self._degrees:
      joint_values = np.degrees(joint_values)
      
    return joint_values