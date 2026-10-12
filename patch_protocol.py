import re

with open('.harness/a2a/protocol.py', 'r') as f:
    text = f.read()

text = re.sub(
    r'    def __init__\(self, config: A2AConfig \| HarnessConfig \| None = None\) -> None:\s+if isinstance\(config, HarnessConfig\):\s+self.config = config.a2a\s+else:\s+self.config = config or A2AConfig\(\)',
    '''    def __init__(self, config: A2AConfig | HarnessConfig | None = None, signature_key: str | bytes | None = None) -> None:
        if isinstance(config, HarnessConfig):
            self.config = config.a2a
        else:
            self.config = config or A2AConfig()
        self.signature_key = signature_key.encode('utf-8') if isinstance(signature_key, str) else signature_key

    def _generate_signature(self, task_id: str, status: str, agent_id: str, timestamp_utc: str) -> str:
        import hmac
        import hashlib
        if not self.signature_key:
            return ""
        msg = f"{task_id}:{status}:{agent_id}:{timestamp_utc}".encode('utf-8')
        return hmac.new(self.signature_key, msg, hashlib.sha256).hexdigest()''',
    text
)

with open('.harness/a2a/protocol.py', 'w') as f:
    f.write(text)
