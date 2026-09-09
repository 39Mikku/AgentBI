"""Run from the repository root: python scripts/check-startup.py."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

with tempfile.TemporaryDirectory() as directory:
    os.environ['CHAT_SQLITE_PATH'] = str(Path(directory) / 'workspace.sqlite3')
    os.environ['NCM_ENABLED'] = 'false'

    from fastapi.testclient import TestClient
    from AgentBI.main import app
    from AgentBI.src.api.chat import build_runtime_context
    from types import SimpleNamespace

    context = build_runtime_context(SimpleNamespace(timezone='Asia/Shanghai', locale='zh-CN', user_name='本地用户'))
    assert context['timezone'] == 'Asia/Shanghai'

    with TestClient(app) as client:
        assert client.get('/').status_code == 200
        response = client.get('/workspace')
        assert response.status_code == 200
        user_id = response.json()['profile']['user_id']
        assert user_id == 'local-user'
        assert client.get('/workspace').json()['profile']['user_id'] == user_id
        assert client.get('/providers').json() == []
        assert client.get('/conversations', params={'user_id': user_id}).json() == []
        assert client.post('/login', json={}).status_code == 404
    print('Empty workspace startup passed')
