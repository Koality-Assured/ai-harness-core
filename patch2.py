import sys
with open('.harness/a2a/protocol.py', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if line.startswith('    def __init__(self, config: A2AConfig | HarnessConfig | None = None) -> None:'):
        new_lines.append('    def __init__(self, config: A2AConfig | HarnessConfig | None = None, signature_key: str | bytes | None = None) -> None:\n')
        new_lines.append('        if isinstance(config, HarnessConfig):\n')
        new_lines.append('            self.config = config.a2a\n')
        new_lines.append('        else:\n')
        new_lines.append('            self.config = config or A2AConfig()\n')
        new_lines.append('        self.signature_key = signature_key.encode(\"utf-8\") if isinstance(signature_key, str) else signature_key\n')
        new_lines.append('\n')
        new_lines.append('    def _generate_signature(self, task_id: str, status: str, agent_id: str, timestamp_utc: str) -> str:\n')
        new_lines.append('        import hmac\n')
        new_lines.append('        import hashlib\n')
        new_lines.append('        if not self.signature_key:\n')
        new_lines.append('            return \"\"\n')
        new_lines.append('        msg = f\"{task_id}:{status}:{agent_id}:{timestamp_utc}\".encode(\"utf-8\")\n')
        new_lines.append('        return hmac.new(self.signature_key, msg, hashlib.sha256).hexdigest()\n')
        skip = True
    elif skip and line.startswith('        if isinstance(config, HarnessConfig):'):
        pass
    elif skip and line.startswith('            self.config = config.a2a'):
        pass
    elif skip and line.startswith('        else:'):
        pass
    elif skip and line.startswith('            self.config = config or A2AConfig()'):
        skip = False
    else:
        new_lines.append(line)

with open('.harness/a2a/protocol.py', 'w') as f:
    f.writelines(new_lines)
