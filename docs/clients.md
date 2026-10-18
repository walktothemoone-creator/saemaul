# 클라이언트별 설정 / Client setup

모든 설정은 같은 두 가지를 적는 일입니다. **무엇을 실행할지(command)**와 **무엇을 넘길지(args)**.

```
command: python3
args:    ["/내려받은/경로/saemaul/saemaul_mcp_server.py"]
```

경로는 반드시 절대경로로 씁니다. `pwd`로 지금 위치를 확인한 뒤 뒤에 `/saemaul_mcp_server.py`를 붙이면 됩니다.

---

## Claude Desktop

| OS | 설정 파일 |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

[examples/mcp.json](../examples/mcp.json)의 `saemaul` 항목을 `mcpServers` 안에 넣고 앱을 다시 시작합니다.
Windows에서는 경로 구분자를 `\\`로 두 번 쓰거나 `/`로 씁니다.

```json
{
  "mcpServers": {
    "saemaul": {
      "command": "python3",
      "args": ["/Users/me/saemaul/saemaul_mcp_server.py"]
    }
  }
}
```

## Claude Code

```bash
claude mcp add saemaul -- python3 /내려받은/경로/saemaul/saemaul_mcp_server.py
```

## Cursor

전역으로 쓰려면 `~/.cursor/mcp.json`, 이 저장소를 연 워크스페이스에서만 쓰려면 그 폴더의
`.cursor/mcp.json`에 같은 내용을 넣습니다. 형식은 Claude Desktop과 같습니다.

## VS Code (GitHub Copilot MCP)

[examples/vscode.mcp.json](../examples/vscode.mcp.json)을 저장소의 `.vscode/mcp.json`으로 복사합니다.
키 이름이 `mcpServers`가 아니라 **`servers`**이고 `"type": "stdio"`가 필요합니다.

## Codex CLI

`~/.codex/config.toml`에 추가합니다. 내용은 [examples/codex.config.toml](../examples/codex.config.toml)에 있습니다.

```toml
[mcp_servers.saemaul]
command = "python3"
args = ["/내려받은/경로/saemaul/saemaul_mcp_server.py"]
```

## Zed

설정의 `context_servers`에 넣습니다. [examples/zed.settings.json](../examples/zed.settings.json) 참고.

## Cline · Continue · Windsurf · 그 밖의 에이전트

MCP stdio를 지원하면 모두 같은 `mcpServers` 형식을 씁니다. [examples/mcp.json](../examples/mcp.json)을 쓰십시오.

## ChatGPT 등 URL 커넥터

로컬 명령 대신 MCP 엔드포인트 URL을 받는 클라이언트입니다. [examples/http.md](../examples/http.md)에
띄우는 법과 외부 공개 시 주의할 점을 적어 두었습니다.

---

## 문제가 생기면

### 에이전트가 서버를 못 띄웁니다

먼저 터미널에서 같은 명령을 그대로 실행해 보십시오.

```bash
python3 /내려받은/경로/saemaul/saemaul_mcp_server.py --check
```

- `No module named mcp` → 의존성이 없습니다. `pip install -r requirements.txt` 하거나 `uv run`으로 바꿉니다.
- `데이터 폴더를 찾을 수 없습니다` → 경로가 틀렸거나 `data/`를 함께 받지 않았습니다.
- 터미널에선 되는데 앱에서만 안 됩니다 → GUI 앱은 셸 PATH를 물려받지 않습니다. `which python3` 결과를
  `command`에 통째로 넣으십시오. 예: `/opt/homebrew/bin/python3`. 가상환경을 썼다면 그 안의
  `.venv/bin/python` 경로를 넣습니다.

### uv를 쓰고 싶습니다

```json
{
  "mcpServers": {
    "saemaul": {
      "command": "/opt/homebrew/bin/uv",
      "args": ["run", "/내려받은/경로/saemaul/saemaul_mcp_server.py"]
    }
  }
}
```

`uv`도 절대경로로 적습니다(`which uv`). 의존성을 따로 깔 필요가 없어집니다.
[examples/mcp.uv.json](../examples/mcp.uv.json) 참고.

### 자료를 고쳤는데 반영이 안 됩니다

서버는 시작할 때 한 번만 읽습니다. 에이전트에서 서버를 다시 연결하거나 앱을 다시 시작하십시오.

### 자료를 다른 곳에 두고 싶습니다

환경 변수로 지정합니다.

| 변수 | 뜻 |
|---|---|
| `SAEMAUL_DATA` | `data` 폴더 경로 |
| `SAEMAUL_REGISTRY` | `sources.yaml` 하나만 다른 곳에서 읽을 때 |

```json
{
  "mcpServers": {
    "saemaul": {
      "command": "python3",
      "args": ["/경로/saemaul/saemaul_mcp_server.py"],
      "env": { "SAEMAUL_DATA": "/다른/경로/data" }
    }
  }
}
```

### 도구가 보이는지 직접 확인하고 싶습니다

```bash
python3 tests/smoke_test.py
```

에이전트가 하는 것과 똑같이 서버를 띄워 도구·리소스·프롬프트를 전부 불러 봅니다.
