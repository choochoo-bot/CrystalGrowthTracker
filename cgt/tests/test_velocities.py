# -*- coding: utf-8 -*-
"""
Created on 06 Oct 2021

Licensed under the Apache License, Version 2.0 (the "License"); you may not use
this file except in compliance with the License. You may obtain a copy of the
License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

@copyright 2021
@author: j.h.pickering@leeds.ac.uk
"""
# set up linting conditions
# pylint: disable = too-many-public-methods
# pylint: disable = c-extension-no-member

import unittest

from cgt.util.markers import MarkerTypes
from cgt.model.velocitiescalculator import (ScreenDisplacement,
                                            VelocitiesCalculator)
import cgt.tests.makeresults as mkres

class TestDisplacements(unittest.TestCase):
    """
    test the ScreenDisplacement class
    """

    def setUp(self):
        """
        initalize objects
        """
        ## the start frame
        self._start = 100

        ## the end frame
        self._end = 200

        ## the frames per second
        self._fps = 10.0

        ## the displacement length in pixels
        self._length = 100

        ## the test object (created with end & start reversed to check for switch)
        self._displacement = ScreenDisplacement(self._end,
                                                self._start,
                                                self._fps,
                                                self._length)

        self._speed = 10.0

    def tearDown(self):
        """
        clean up
        """
        del self._displacement

    def test_velocity(self):
        """
        ensure ScreenDisplacement works
        """
        message = "start frame not correct"
        self.assertEqual(self._start, self._displacement.get_start(), message)
        message = "end frame not correct"
        self.assertEqual(self._end, self._displacement.get_end(), message)
        message = "length not correct"
        self.assertEqual(self._length, self._displacement.get_length(), message)

        # test speed to 5 decimal places
        speed = self._displacement.get_speed()
        message = f"speed wrong: {speed} should be 10.0"
        self.assertAlmostEqual(self._speed, speed, 5, message)

class TestVelocities(unittest.TestCase):
    """
    test the velocities calculator class
    """

    def setUp(self):
        """
        initalize objects
        """
        self._points = mkres.make_test_points()
        self._lines = mkres.make_test_lines()
        self._test_values = mkres.get_test_values()

        self._calculator = VelocitiesCalculator([self._lines],
                                                [self._points],
                                                self._test_values.fps,
                                                self._test_values.scale)

        self._calculator.process_latest_data()

    def tearDown(self):
        """
        clean up
        """
        del self._calculator

    def test_calculator(self):
        """
        ensure calculator works
        """
        speeds = self._calculator.get_average_speeds()

        for speed in speeds:
            if speed.m_type is MarkerTypes.POINT:
                message = "point speed is wrong"
                self.assertAlmostEqual(self._test_values.point_speed,
                                       speed.speed,
                                       places=4,
                                       msg=message)

            elif speed.m_type is MarkerTypes.LINE:
                message = "line speed is wrong"
                self.assertAlmostEqual(self._test_values.line_speed,
                                       speed.speed,
                                       places=4,
                                       msg=message)

if __name__ == "__main__":
    unittest.main()
