#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.2.0", "PyYAML>=6.0"]
# ///
"""설치 없이 바로 실행하는 진입점. / Zero-install entry point.

uv가 있으면 설치 과정 없이 그대로 쓸 수 있다. 위의 주석이 필요한 패키지를 알려 준다.

    uv run /절대경로/saemaul/saemaul_mcp_server.py

pip로 의존성을 깔았다면 보통의 파이썬으로도 된다.

    python3 /절대경로/saemaul/saemaul_mcp_server.py

어느 쪽이든 에이전트 설정의 command/args 에 그대로 넣으면 된다.
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from saemaul_mcp.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
