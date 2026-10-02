#!/usr/bin/env python3
"""Unit tests for geometry and temporal mutation in the PAR-011 experiment."""

from __future__ import annotations

import unittest

import numpy as np

from run_par_011_counterfactual_fragility import (
    VehicleGeometry,
    interpolate_track,
    signed_clearance_to_ego,
)


class CounterfactualFragilityTest(unittest.TestCase):
    def test_signed_clearance_to_front_of_vehicle(self) -> None:
        plan = np.array([[0.0, 0.0]])
        yaw = np.array([0.0])
        pedestrian = np.array([[4.0, 0.0]])
        radius = np.array([0.5])
        geometry = VehicleGeometry(length=4.0, width=2.0, rear_axle_to_center=1.0)
        clearance = signed_clearance_to_ego(
            plan, yaw, pedestrian, radius, geometry, margin_m=0.0
        )
        self.assertAlmostEqual(float(clearance[0]), 0.5)

    def test_margin_can_convert_clearance_to_overlap_candidate(self) -> None:
        plan = np.array([[0.0, 0.0]])
        yaw = np.array([0.0])
        pedestrian = np.array([[3.6, 0.0]])
        radius = np.array([0.2])
        geometry = VehicleGeometry(length=4.0, width=2.0, rear_axle_to_center=1.0)
        clearance = signed_clearance_to_ego(
            plan, yaw, pedestrian, radius, geometry, margin_m=0.5
        )
        self.assertLess(float(clearance[0]), 0.0)

    def test_track_interpolation(self) -> None:
        times_us = np.array([8_506_674, 9_506_674, 10_506_674])
        points = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]])
        radius = np.full(3, 0.3)
        delayed, delayed_radius = interpolate_track(
            times_us, points, radius, np.array([0.0, 0.5, 1.0])
        )
        np.testing.assert_allclose(delayed[:, 0], [0.0, 0.5, 1.0])
        np.testing.assert_allclose(delayed_radius, 0.3)


if __name__ == "__main__":
    unittest.main()
