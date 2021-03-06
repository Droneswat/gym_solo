""" A demo for the Solo v2 Vanilla with realtime control.

This environment is designed to act like a real robot would. There is no concept
of a "timestep"; rather the step command should be interprated as sending
position values to the robot's PID controllers.
"""
import gym
import numpy as np

import gym_solo
from gym_solo.envs import solo8v2vanilla
from gym_solo.core import obs


if __name__ == '__main__':
  env = gym.make('solo8vanilla-realtime-v0')
  env.obs_factory.register_observation(obs.TorsoIMU(env.robot))

  try:
    print("""\n
          =============================================
              Solo 8 v2 Vanilla Realtime Simulation
              
          Simulation Active.
          
          Exit with ^C.
          =============================================
          """)

    env.reset()
    while True:
      pos = float(input('Which position do you want to set all the joints to?: '))
      action = np.full(env.action_space.shape, pos)
      env.step(action)

  except KeyboardInterrupt:
    pass