import os
import unittest
from unittest.mock import patch


class SendEmailToolTests(unittest.TestCase):
    def test_email_message_contains_plain_and_html_alternatives(self):
        from AgentBI.src.tools.send_email_tool import build_email_message

        message = build_email_message(
            "reader@example.com",
            "AgentBI 登录验证码",
            "验证码 123456",
            html_content="<strong>123456</strong>",
            sender="agentbi@example.com",
        )

        self.assertEqual(message["To"], "reader@example.com")
        self.assertEqual(message["From"], "agentbi@example.com")
        self.assertEqual(message.get_body(preferencelist=("plain",)).get_content().strip(), "验证码 123456")
        self.assertIn("<strong>123456</strong>", message.get_body(preferencelist=("html",)).get_content())

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

        with patch.dict(os.environ, {"EMAIL_HOST": "", "NCM_ENABLED": "false"}), patch.object(
            send_email_tool, "dotenv_values", return_value={"EMAIL_HOST": "smtp.example.com", "NCM_ENABLED": "true"}
        ):
            send_email_tool.load_smtp_environment()
            self.assertEqual(os.environ['EMAIL_HOST'], 'smtp.example.com')
            self.assertEqual(os.environ['NCM_ENABLED'], 'false')


if __name__ == "__main__":
    unittest.main()
