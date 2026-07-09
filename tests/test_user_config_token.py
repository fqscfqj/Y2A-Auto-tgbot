import unittest

from src.database.models import UserConfig


class UserConfigTokenTests(unittest.TestCase):
    def test_user_config_uses_api_token_field(self):
        config = UserConfig.from_dict({
            "id": 1,
            "user_id": 2,
            "y2a_api_url": "https://y2a.example.com/tasks/add_via_extension",
            "y2a_api_token": "y2a_tgbot_v1_example_token_value_1234567890",
            "upload_target": "acfun",
            "created_at": None,
            "updated_at": None,
        })

        self.assertEqual(config.y2a_api_token, "y2a_tgbot_v1_example_token_value_1234567890")
        self.assertEqual(config.to_dict()["y2a_api_token"], "y2a_tgbot_v1_example_token_value_1234567890")
        self.assertNotIn("y2a_password", config.to_dict())


if __name__ == "__main__":
    unittest.main()
