import os
import unittest
from unittest.mock import patch


class SendEmailToolTests(unittest.TestCase):
    def test_smtp_settings_rejects_a_missing_host_before_login(self):
        from AgentBI.src.tools.send_email_tool import smtp_settings

        with patch.dict(
            os.environ,
            {"EMAIL_HOST": "", "EMAIL_FROM": "sender@example.com", "EMAIL_PASSWORD": "password"},
            clear=False,
        ):
            with self.assertRaisesRegex(RuntimeError, "EMAIL_HOST"):
                smtp_settings()

    def test_local_env_loader_overrides_empty_inherited_values(self):
        from AgentBI.src.tools import send_email_tool

        with patch.object(send_email_tool, "load_dotenv") as load_dotenv:
            send_email_tool.load_smtp_environment()

        load_dotenv.assert_called_once_with(send_email_tool.ENV_PATH, override=True)


if __name__ == "__main__":
    unittest.main()
