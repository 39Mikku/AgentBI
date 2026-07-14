import unittest


class ChatRouteTests(unittest.TestCase):
    def test_chat_and_configuration_routers_expose_phase_one_endpoints(self):
        from AgentBI.src.api.chat import router as chat_router
        from AgentBI.src.api.conversations import router as conversation_router
        from AgentBI.src.api.providers import router as provider_router

        chat_paths = {route.path for route in chat_router.routes}
        conversation_paths = {route.path for route in conversation_router.routes}
        provider_paths = {route.path for route in provider_router.routes}

        self.assertIn("/chat/stream", chat_paths)
        self.assertIn("/conversations", conversation_paths)
        self.assertIn("/providers", provider_paths)


if __name__ == "__main__":
    unittest.main()
