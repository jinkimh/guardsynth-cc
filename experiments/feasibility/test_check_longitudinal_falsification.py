import unittest

from check_longitudinal_falsification import Scenario, check_grid, motion_step, simulate_scenario


class LongitudinalFalsificationTest(unittest.TestCase):
    def test_motion_stops_without_negative_speed(self) -> None:
        distance, speed = motion_step(1.0, -4.0, 1.0)
        self.assertAlmostEqual(distance, 0.125)
        self.assertEqual(speed, 0.0)

    def test_short_gap_reaches_collision(self) -> None:
        result = simulate_scenario(
            Scenario(5.0, 6.0, 0.0, 5.0, 0.0, 1.0, 0.2),
            horizon_s=5.0,
            dt_s=0.1,
        )
        self.assertTrue(result.collision)

    def test_large_gap_avoids_collision_in_same_model(self) -> None:
        result = simulate_scenario(
            Scenario(30.0, 6.0, 0.0, 5.0, 0.0, 1.0, 0.2),
            horizon_s=5.0,
            dt_s=0.1,
        )
        self.assertFalse(result.collision)

    def test_longer_response_delay_does_not_reduce_collision_count(self) -> None:
        results = check_grid(
            ego_speed_mps=6.0,
            gaps_m=[5.0, 10.0, 20.0],
            lead_speeds_mps=[0.0],
            ego_decels_mps2=[3.0, 5.0],
            lead_decels_mps2=[0.0],
            response_delays_s=[0.5, 2.0],
            brake_build_ups_s=[0.2, 0.5],
            horizon_s=5.0,
            dt_s=0.1,
            minimum_clearance_m=0.0,
        )
        self.assertLessEqual(
            results["0.5s"]["collision_scenarios"],
            results["2s"]["collision_scenarios"],
        )

    def test_documented_grid_regression(self) -> None:
        results = check_grid(
            ego_speed_mps=4.814302397104371,
            gaps_m=[5.0, 10.0, 15.0, 20.0, 25.0, 30.0],
            lead_speeds_mps=[0.0],
            ego_decels_mps2=[3.0, 5.0, 7.0],
            lead_decels_mps2=[0.0],
            response_delays_s=[0.5, 1.0, 2.0, 2.159711],
            brake_build_ups_s=[0.2, 0.5],
            horizon_s=5.0,
            dt_s=0.1,
            minimum_clearance_m=0.0,
        )
        self.assertEqual(
            [results[key]["collision_scenarios"] for key in ("0.5s", "1s", "2s", "2.15971s")],
            [3, 6, 12, 13],
        )
        self.assertEqual(
            [
                results[key]["minimum_tested_gap_without_witness_m"]
                for key in ("0.5s", "1s", "2s", "2.15971s")
            ],
            [10.0, 10.0, 15.0, 20.0],
        )


if __name__ == "__main__":
    unittest.main()
