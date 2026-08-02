"""Optional summarisation against any OpenAI-compatible endpoint."""

import json
import urllib.request


def summarise(
    text, endpoint, model, prompt, api_key=None, max_chars=20000, timeout=1800
):
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            # A very long recording would overflow the context and lose its
            # tail silently; cut the summary input, never the stored transcript.
            {"role": "user", "content": text[:max_chars]},
        ],
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        f"{endpoint.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode(),
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read())
    return payload["choices"][0]["message"]["content"].strip()
