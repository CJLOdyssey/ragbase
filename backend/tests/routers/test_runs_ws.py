"""Run WebSocket endpoint tests — auth + ownership gates (/ws/runs/{id}).

``/ws/*`` 被 AuthMiddleware 豁免，handler 必须自行认证并校验归属；
这些测试锁定该安全边界，防止回归成「未认证即可流式读取任意 run」。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import starlette.websockets as ws_errors


def test_ws_unauthenticated_rejected(client, monkeypatch):
    """无有效 token → error 状态 + 1008 关闭，不进入流式逻辑。"""
    monkeypatch.setattr("routers.runs._ws_user_id", lambda websocket: "")
    with client.websocket_connect("/ws/runs/run-1") as websocket:
        assert websocket.receive_json() == {
            "type": "status", "status": "error", "error": "未登录",
        }
        with pytest.raises(ws_errors.WebSocketDisconnect):
            websocket.receive_json()


def test_ws_non_owner_rejected(client, monkeypatch):
    """已认证但 run 非本人 → 拒绝（BOLA 防护）。"""
    monkeypatch.setattr("routers.runs._ws_user_id", lambda websocket: "u-other")
    with patch("routers.runs.get_run_for_user", new_callable=AsyncMock) as mock_for_user:
        mock_for_user.return_value = None
        with client.websocket_connect("/ws/runs/run-1") as websocket:
            assert websocket.receive_json() == {
                "type": "status", "status": "error", "error": "无权访问该运行",
            }
            with pytest.raises(ws_errors.WebSocketDisconnect):
                websocket.receive_json()


def test_ws_owner_gets_stream_for_completed_run(client, monkeypatch):
    """本人已结束的 run → 正常连接，流式回放消息与结果。"""
    monkeypatch.setattr("routers.runs._ws_user_id", lambda websocket: "admin-login")
    run = MagicMock(
        status="converged",
        approved=True,
        pm_document="PM 文档",
        code="print(1)",
        review="OK",
    )
    msg = MagicMock(
        role="assistant",
        agent_name="pm",
        content="回复内容",
        round_number=1,
        sources='[{"asset_id": "a1"}]',
    )
    with (
        patch("routers.runs.get_run_for_user", new_callable=AsyncMock) as mock_for_user,
        patch("routers.runs.get_messages", new_callable=AsyncMock) as mock_msgs,
        patch("routers.runs.stop_buffer", new_callable=AsyncMock),
    ):
        mock_for_user.return_value = run
        mock_msgs.return_value = [msg]
        with client.websocket_connect("/ws/runs/run-1") as websocket:
            assert websocket.receive_json()["status"] == "connected"
            message = websocket.receive_json()
            assert message["type"] == "message"
            assert message["content"] == "回复内容"
            assert message["sources"] == [{"asset_id": "a1"}]
            result = websocket.receive_json()
            assert result["type"] == "result"
            assert result["pm_document"] == "PM 文档"
