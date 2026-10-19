# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path
import socket
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

FILES = Path(__file__).resolve().parents[1] / 'recipes-connectivity/openh432-adbd/files'
spec = importlib.util.spec_from_file_location('approval', FILES / 'adb-approval.py')
approval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(approval)


class ApprovalTests(unittest.TestCase):
    def test_exact_affirmative_only(self):
        self.assertTrue(approval.decision(b'yes\n'))
        self.assertTrue(approval.decision(b'YES\n'))
        for answer in (b'', b'\n', b'y', b'no', b'yes please', b'yes\nno\n', b'\x1byes'):
            self.assertFalse(approval.decision(answer))

    def test_untrusted_comments_are_not_rendered(self):
        digest = 'SHA256:' + 'A' * 43
        with patch.object(approval.subprocess, 'run', return_value=SimpleNamespace(stdout=(digest+'\n').encode())) as run:
            self.assertEqual(approval.fingerprint(b'PKopaque-key \x1b[2Jhost\0'), digest)
            self.assertEqual(run.call_args.kwargs['input'], b'opaque-key \x1b[2Jhost')

    def test_bad_framing_is_rejected_before_subprocess(self):
        for packet in (b'PK', b'NOabc', b'PKx\ny', b'PKx\ry', b'PKx\0y', b'PK' + b'x'*4097):
            with patch.object(approval.subprocess, 'run') as run:
                with self.assertRaises(ValueError):
                    approval.fingerprint(packet)
                run.assert_not_called()

    def test_fingerprint_output_is_strict(self):
        with patch.object(approval.subprocess, 'run', return_value=SimpleNamespace(stdout=b'\x1b[2Jhost')):
            with self.assertRaises(ValueError):
                approval.fingerprint(b'PKkey')

    def test_allow_and_deny_protocol_is_exact(self):
        for accepted, response in ((True, b'OK'), (False, b'NO')):
            peer = Mock()
            peer.recvmsg.side_effect = [(b'PKkey', [], 0, None), (b'', [], 0, None)]
            with patch.object(approval, 'fingerprint', return_value='fingerprint'), patch.object(approval, 'prompt', return_value=accepted):
                approval.serve(peer)
            peer.sendall.assert_called_once_with(response)

    def test_prompt_failure_denies(self):
        peer = Mock()
        peer.recvmsg.side_effect = [(b'PKkey', [], 0, None), (b'', [], 0, None)]
        with patch.object(approval, 'fingerprint', side_effect=ValueError):
            approval.serve(peer)
        peer.sendall.assert_called_once_with(b'NO')

    def test_truncated_or_unknown_packets_fail_closed(self):
        for packet, flags in ((b'PKkey', socket.MSG_TRUNC), (b'W1', 0)):
            peer = Mock()
            peer.recvmsg.return_value = (packet, [], flags, None)
            with self.assertRaises(ValueError):
                approval.serve(peer)
            peer.sendall.assert_not_called()

    def test_notifications_do_not_open_prompts(self):
        peer = Mock()
        peer.recvmsg.side_effect = [(b'CKkey', [], 0, None), (b'DCkey', [], 0, None), (b'', [], 0, None)]
        with patch.object(approval, 'prompt') as prompt:
            approval.serve(peer)
        prompt.assert_not_called()
        peer.sendall.assert_not_called()

    def test_service_reserves_private_vt_and_stops_with_daemon(self):
        unit = (FILES / 'FMAdbApproval.service').read_text()
        for expected in ('BindsTo=FMAdb.service', 'Conflicts=getty@tty8.service',
                         'CapabilityBoundingSet=CAP_SYS_TTY_CONFIG', 'RestrictAddressFamilies=AF_UNIX'):
            self.assertIn(expected, unit)
        self.assertNotIn('[Install]', unit)


if __name__ == '__main__':
    unittest.main()
