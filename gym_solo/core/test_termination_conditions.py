import unittest
from gym_solo.core import termination

class TestTimeBasedTermination(unittest.TestCase):
    def test_attributes(self):
      max_step_delta = 3
      term = termination.TimeBasedTermination(max_step_delta)
      self.assertEqual(max_step_delta, term.max_step_delta)
      self.assertEqual(0, term.step_delta)

    def test_reset(self):
      max_step_delta = 3
      term = termination.TimeBasedTermination(max_step_delta)

      for i in range(max_step_delta):
        self.assertFalse(term.is_terminated())

      term.reset()
      self.assertEqual(0,term.step_delta)

    def test_is_terminated(self):
      max_step_delta = 3
      term = termination.TimeBasedTermination(max_step_delta)
      
      for i in range(max_step_delta):
        self.assertEqual(False, term.is_terminated())
        self.assertEqual(i+1, term.step_delta)

      self.assertEqual(True, term.is_terminated())
      self.assertEqual(max_step_delta + 1, term.step_delta)


class TestPerpetualTermination(unittest.TestCase):
  def test_is_terminated(self):
    term = termination.PerpetualTermination()

    # Arbitrary count, just need to ensure that always returns False
    for i in range(1000): 
      self.assertFalse(term.is_terminated())