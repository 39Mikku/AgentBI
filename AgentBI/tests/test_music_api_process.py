import asyncio
import unittest


class _FakeProcess:
    def __init__(self, returncode=None):
        self.returncode = returncode
        self.terminated = False
        self.killed = False

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def kill(self):
        self.killed = True
        self.returncode = -9

    async def wait(self):
        return self.returncode


class _FakeSyncProcess:
    def __init__(self, returncode=None):
        self.returncode = returncode
        self.terminated = False
        self.killed = False
        self.stdout = _FakeSyncStream()
        self.stderr = _FakeSyncStream()

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self):
        return self.returncode


class _FakeSyncStream:
    def __init__(self):
        self.closed = False

    def readline(self):
        return b""

    def close(self):
        self.closed = True


class MusicApiProcessManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_sync_exit_is_polled_before_health_wait(self):
        from AgentBI.src.services.music_api_process import MusicApiProcessManager

        process = _FakeSyncProcess()
        process.poll = lambda: 1
        probes = []

        async def probe(_):
            probes.append(True)
            return False

        manager = MusicApiProcessManager(sync_process_factory=lambda *_, **__: process, health_probe=probe)
        self.assertFalse(await manager.start())
        self.assertEqual(probes, [])
        self.assertFalse(process.terminated)

    async def test_sync_process_factory_does_not_require_asyncio_subprocess_support(self):
        from AgentBI.src.services.music_api_process import MusicApiProcessManager

        starts = []
        process = _FakeSyncProcess()

        def sync_process_factory(*args, **kwargs):
            starts.append((args, kwargs))
            return process

        manager = MusicApiProcessManager(
            enabled=True,
            startup_timeout=0.2,
            poll_interval=0,
            sync_process_factory=sync_process_factory,
            health_probe=lambda _: asyncio.sleep(0, result=True),
            command=("node", "app.cjs"),
        )

        await manager.start()
        await manager.stop()

        self.assertEqual(len(starts), 1)
        self.assertEqual(starts[0][0], (("node", "app.cjs"),))
        self.assertTrue(process.terminated)
        self.assertTrue(process.stdout.closed)
        self.assertTrue(process.stderr.closed)

    async def test_disabled_manager_never_starts_a_process(self):
        from AgentBI.src.services.music_api_process import MusicApiProcessManager

        starts = []

        async def process_factory(*args, **kwargs):
            starts.append((args, kwargs))
            return _FakeProcess()

        manager = MusicApiProcessManager(
            enabled=False,
            process_factory=process_factory,
            health_probe=lambda _: asyncio.sleep(0, result=True),
        )

        await manager.start()

        self.assertFalse(manager.available)
        self.assertEqual(starts, [])

    async def test_start_polls_health_and_marks_service_available(self):
        from AgentBI.src.services.music_api_process import MusicApiProcessManager

        process = _FakeProcess()
        probes = iter([False, True])

        async def health_probe(_):
            return next(probes)

        async def process_factory(*args, **kwargs):
            return process

        manager = MusicApiProcessManager(
            enabled=True,
            startup_timeout=0.2,
            poll_interval=0,
            process_factory=process_factory,
            health_probe=health_probe,
            command=("node", "app.cjs"),
        )

        await manager.start()

        self.assertTrue(manager.available)
        self.assertEqual(manager.base_url, "http://127.0.0.1:3300")

    async def test_ensure_running_restarts_a_dead_process_once(self):
        from AgentBI.src.services.music_api_process import MusicApiProcessManager

        processes = [_FakeProcess(), _FakeProcess()]
        starts = 0

        async def process_factory(*args, **kwargs):
            nonlocal starts
            process = processes[starts]
            starts += 1
            return process

        async def health_probe(_):
            return True

        manager = MusicApiProcessManager(
            enabled=True,
            startup_timeout=0.2,
            poll_interval=0,
            process_factory=process_factory,
            health_probe=health_probe,
            command=("node", "app.cjs"),
        )
        await manager.start()
        processes[0].returncode = 1

        self.assertTrue(await manager.ensure_running())
        self.assertEqual(starts, 2)

        processes[1].returncode = 1
        self.assertFalse(await manager.ensure_running())
        self.assertEqual(starts, 2)

    async def test_stop_terminates_the_child_process(self):
        from AgentBI.src.services.music_api_process import MusicApiProcessManager

        process = _FakeProcess()

        async def process_factory(*args, **kwargs):
            return process

        manager = MusicApiProcessManager(
            enabled=True,
            startup_timeout=0.2,
            poll_interval=0,
            process_factory=process_factory,
            health_probe=lambda _: asyncio.sleep(0, result=True),
            command=("node", "app.cjs"),
        )
        await manager.start()

        await manager.stop()

        self.assertTrue(process.terminated)
        self.assertFalse(manager.available)


if __name__ == "__main__":
    unittest.main()
