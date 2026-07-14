import unittest


class ChatRouteTests(unittest.TestCase):
    def test_chat_and_configuration_routers_expose_phase_one_endpoints(self):
        from AgentBI.src.api.chat import router as chat_router
        from AgentBI.src.api.conversations import router as conversation_router
        from AgentBI.src.api.providers import router as provider_router
        from AgentBI.src.api.user_profile import router as user_profile_router

        chat_paths = {route.path for route in chat_router.routes}
        conversation_paths = {route.path for route in conversation_router.routes}
        provider_paths = {route.path for route in provider_router.routes}
        user_profile_paths = {route.path for route in user_profile_router.routes}

        self.assertIn("/chat/stream", chat_paths)
        self.assertIn("/conversations", conversation_paths)
        self.assertIn("/chat/preferences", conversation_paths)
        self.assertIn("/providers", provider_paths)
        self.assertIn("/user-profile", user_profile_paths)
        self.assertIn("/user-profile/avatar", user_profile_paths)


if __name__ == "__main__":
    unittest.main()
