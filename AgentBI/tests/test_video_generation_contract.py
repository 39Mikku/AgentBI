import unittest


class VideoGenerationContractTests(unittest.TestCase):
    def test_duration_maps_to_agnes_valid_frame_presets(self):
        from AgentBI.src.schemas.video_generation_schema import frames_for_duration

        self.assertEqual(
            {seconds: frames_for_duration(seconds) for seconds in (3, 5, 10, 18)},
            {3: 81, 5: 121, 10: 241, 18: 441},
        )
        with self.assertRaises(ValueError):
            frames_for_duration(4)

    def test_aspect_ratios_map_to_720p_dimensions(self):
        from AgentBI.src.schemas.video_generation_schema import dimensions_for_aspect_ratio

        self.assertEqual(dimensions_for_aspect_ratio("16:9"), (1280, 720))
        self.assertEqual(dimensions_for_aspect_ratio("9:16"), (720, 1280))
        self.assertEqual(dimensions_for_aspect_ratio("1:1"), (768, 768))
        self.assertEqual(dimensions_for_aspect_ratio("4:3"), (1024, 768))
        self.assertEqual(dimensions_for_aspect_ratio("3:4"), (768, 1024))

    def test_capability_config_has_only_default_ratio_and_duration(self):
        from AgentBI.src.schemas.capability_settings_schema import resolve_capability_config

        self.assertEqual(
            resolve_capability_config("tool.video_generation"),
            {"default_aspect_ratio": "16:9", "default_duration_seconds": 5},
        )
        self.assertEqual(
            resolve_capability_config(
                "tool.video_generation",
                {"default_aspect_ratio": "9:16", "default_duration_seconds": 10},
            ),
            {"default_aspect_ratio": "9:16", "default_duration_seconds": 10},
        )
        with self.assertRaises(ValueError):
            resolve_capability_config(
                "tool.video_generation",
                {"default_aspect_ratio": "16:9", "default_duration_seconds": 7},
            )


if __name__ == "__main__":
    unittest.main()
