import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from AgentBI.src.api.workspace import router
from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = str(Path(self.directory.name) / "workspace.sqlite3")
        self.repository = SqliteChatRepository(self.path)
        app = FastAPI()
        app.state.chat_repository = self.repository
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.repository.close()
        self.directory.cleanup()

    def test_empty_workspace_is_stable_and_profile_can_be_renamed(self):
        first = self.client.get('/workspace').json()
        self.assertEqual(first['profile']['user_id'], 'local-user')
        self.assertIsNone(first['profile']['email'])
        self.repository.update_user('local-user', {'username': '我的工作台'})
        self.assertEqual(self.client.get('/workspace').json()['profile']['username'], '我的工作台')
        self.assertEqual(len(self.client.get('/workspace').json()['profiles']), 1)

    def test_single_legacy_identity_preserves_threads_and_settings(self):
        user = self.repository.create_user('old@example.com')
        assistant = self.repository.ensure_default_assistant(user['user_id'])
        thread = self.repository.create_conversation({'user_id': user['user_id'], 'title': '旧会话', 'assistant_id': assistant['_id']})
        result = self.client.get('/workspace').json()
        self.assertEqual(result['profile']['user_id'], user['user_id'])
        self.assertEqual(self.repository.get_conversation(thread['_id'], user['user_id'])['title'], '旧会话')
        self.assertEqual(self.repository.ensure_default_assistant(user['user_id'])['_id'], assistant['_id'])

    def test_multiple_legacy_identities_require_selection_and_survive_reopen(self):
        self.repository.create_user('one@example.com')
        self.repository.create_user('two@example.com')
        self.assertIsNone(self.client.get('/workspace').json()['profile'])
        response = self.client.put('/workspace', json={'user_id': 'two@example.com'})
        self.assertEqual(response.status_code, 200)
        self.repository.close()
        self.repository = SqliteChatRepository(self.path)
        selected, profiles = self.repository.bootstrap_workspace()
        self.assertEqual(selected['user_id'], 'two@example.com')
        self.assertEqual(len(profiles), 2)

    def test_invalid_selection_does_not_create_or_replace_identity(self):
        self.client.get('/workspace')
        self.assertEqual(self.client.put('/workspace', json={'user_id': 'missing'}).status_code, 404)
        self.assertEqual(self.client.get('/workspace').json()['profile']['user_id'], 'local-user')
