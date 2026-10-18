"""새마을 MCP — 새마을운동 자료를 표준 MCP로 제공한다.

Saemaul MCP — Saemaul Undong (South Korea, 1970s) sources over the Model Context Protocol.
"""

__version__ = "0.2.0"

__all__ = ["__version__", "main", "build_server", "Corpus"]


def __getattr__(name: str):
    # mcp 패키지가 없어도 Corpus/CLI는 쓸 수 있게 늦게 가져온다.
    if name == "main":
        from .cli import main

        return main
    if name == "build_server":
        from .server import build_server

        return build_server
    if name == "Corpus":
        from .corpus import Corpus

        return Corpus
    raise AttributeError(name)
