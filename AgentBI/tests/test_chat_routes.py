import unittest


class ChatRouteTests(unittest.TestCase):
    def test_chat_and_configuration_routers_expose_phase_one_endpoints(self):
        from AgentBI.src.api.chat import router as chat_router
        from AgentBI.src.api.conversations import router as conversation_router
        from AgentBI.src.api.providers import router as provider_router
        from AgentBI.src.api.user_profile import router as user_profile_router
        from AgentBI.src.api.assistants import router as assistant_router
        from AgentBI.src.api.model_routes import router as model_route_router
        from AgentBI.src.api.music import router as music_router
        from AgentBI.src.api.capability_settings import router as capability_settings_router
        from AgentBI.src.api.live import router as live_router
        from AgentBI.src.api.image_generation import router as image_generation_router

        chat_paths = {route.path for route in chat_router.routes}
        conversation_paths = {route.path for route in conversation_router.routes}
        provider_paths = {route.path for route in provider_router.routes}
        user_profile_paths = {route.path for route in user_profile_router.routes}
        assistant_paths = {route.path for route in assistant_router.routes}
        model_route_paths = {route.path for route in model_route_router.routes}
        music_paths = {route.path for route in music_router.routes}
        capability_settings_paths = {route.path for route in capability_settings_router.routes}
        live_paths = {route.path for route in live_router.routes}
        image_generation_paths = {route.path for route in image_generation_router.routes}

        self.assertIn("/chat/stream", chat_paths)
        self.assertIn("/conversations", conversation_paths)
        self.assertIn("/conversations/{conversation_id}/branches", conversation_paths)
        self.assertIn("/conversations/{conversation_id}/active-message/{message_id}", conversation_paths)
        self.assertIn("/conversations/{conversation_id}/messages/{message_id}/edit", conversation_paths)
        self.assertIn("/conversations/{conversation_id}/messages/{message_id}/retry", conversation_paths)
        self.assertIn("/chat/preferences", conversation_paths)
        self.assertIn("/providers", provider_paths)
        self.assertIn("/user-profile", user_profile_paths)
        self.assertIn("/user-profile/avatar", user_profile_paths)
        self.assertIn("/assistants/{assistant_id}/memory", assistant_paths)
        self.assertIn("/assistants/{assistant_id}/memory/refresh", assistant_paths)
        self.assertIn("/model-routes/{role}", model_route_paths)
        self.assertIn("/music/status", music_paths)
        self.assertIn("/music/tracks/{track_id}/stream", music_paths)
        self.assertIn("/capabilities/settings", capability_settings_paths)
        self.assertIn("/capabilities/{capability_id}/settings", capability_settings_paths)
        self.assertIn("/live/preferences", live_paths)
        self.assertIn("/live/roles", live_paths)
        self.assertIn("/live/roles/{role_id}/memory", live_paths)
        self.assertIn("/live/conversations", live_paths)
        self.assertIn("/live/conversations/{conversation_id}/messages", live_paths)
        self.assertIn("/live/ws", live_paths)
        self.assertIn("/image-generation/generate", image_generation_paths)
        self.assertIn("/image-generation/codex/status", image_generation_paths)
        self.assertIn("/image-generation/codex/connect", image_generation_paths)

        from AgentBI.main import app

        self.assertTrue(any(getattr(route, "path", None) == "/generated-images" for route in app.routes))


if __name__ == "__main__":
    unittest.main()
