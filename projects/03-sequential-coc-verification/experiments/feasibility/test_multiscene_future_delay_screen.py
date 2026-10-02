#!/usr/bin/env python3
"""Geometry tests for the multiscene future-delay screen."""

from __future__ import annotations

import unittest

import numpy as np

from run_multiscene_future_delay_screen import polygon_signed_distance, rectangle


class RectangleDistanceTest(unittest.TestCase):
    def test_separated_axis_aligned_rectangles(self) -> None:
        first = rectangle(np.array([0.0, 0.0]), 0.0, 4.0, 2.0)
        second = rectangle(np.array([4.0, 0.0]), 0.0, 2.0, 2.0)
        self.assertAlmostEqual(polygon_signed_distance(first, second), 1.0)

    def test_touching_rectangles(self) -> None:
        first = rectangle(np.array([0.0, 0.0]), 0.0, 4.0, 2.0)
        second = rectangle(np.array([3.0, 0.0]), 0.0, 2.0, 2.0)
        self.assertAlmostEqual(polygon_signed_distance(first, second), 0.0)

    def test_overlapping_rectangles_are_negative(self) -> None:
        first = rectangle(np.array([0.0, 0.0]), 0.0, 4.0, 2.0)
        second = rectangle(np.array([2.5, 0.0]), 0.0, 2.0, 2.0)
        self.assertLess(polygon_signed_distance(first, second), 0.0)

    def test_rotated_separation_is_symmetric(self) -> None:
        first = rectangle(np.array([0.0, 0.0]), 0.3, 4.0, 2.0)
        second = rectangle(np.array([5.0, 2.0]), -0.4, 2.0, 1.0)
        self.assertAlmostEqual(
            polygon_signed_distance(first, second),
            polygon_signed_distance(second, first),
        )


if __name__ == "__main__":
    unittest.main()
