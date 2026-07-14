import unittest


class ChatErrorTests(unittest.TestCase):
    def test_model_error_message_is_safe_and_visible_to_the_user(self):
        from AgentBI.src.services.chat_service import format_model_error

        message = format_model_error(PermissionError('Your request was blocked.'))

        self.assertEqual(message, '模型调用被提供商拒绝：Your request was blocked.')


if __name__ == '__main__':
    unittest.main()
