import unittest

from src.database.models import UserConfig
from src.utils.config_status import get_config_status, is_tgbot_api_token


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

    def test_token_format_validator(self):
        self.assertTrue(is_tgbot_api_token("y2a_tgbot_v1_" + "a" * 32))
        self.assertFalse(is_tgbot_api_token("wrong_" + "a" * 32))
        self.assertFalse(is_tgbot_api_token("y2a_tgbot_v1_short"))
        self.assertFalse(is_tgbot_api_token("y2a_tgbot_v1_" + "!" * 32))

    def test_config_status_guides_next_step(self):
        missing = get_config_status(None)
        self.assertFalse(missing.is_ready)
        self.assertEqual(missing.next_action, "set_api")

        api_only = get_config_status(UserConfig(y2a_api_url="https://y2a.example.com/tasks/add_via_extension"))
        self.assertFalse(api_only.is_ready)
        self.assertEqual(api_only.next_action, "set_api_token")

        invalid_token = get_config_status(UserConfig(
            y2a_api_url="https://y2a.example.com/tasks/add_via_extension",
            y2a_api_token="not-a-valid-token",
        ))
        self.assertFalse(invalid_token.is_ready)
        self.assertTrue(invalid_token.has_api_token)
        self.assertFalse(invalid_token.has_valid_api_token)

        ready = get_config_status(UserConfig(
            y2a_api_url="https://y2a.example.com/tasks/add_via_extension",
            y2a_api_token="y2a_tgbot_v1_" + "a" * 32,
        ))
        self.assertTrue(ready.is_ready)
        self.assertEqual(ready.next_action, "test")


if __name__ == "__main__":
    unittest.main()
