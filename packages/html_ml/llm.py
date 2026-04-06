from __future__ import annotations

import json
from typing import Any

import httpx

from html_ml.config import settings


class OpenRouterClient:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        resolved_api_key = api_key or settings.openrouter_api_key
        if not resolved_api_key:
            raise RuntimeError('OPENROUTER_API_KEY is not configured')
        self.base_url = settings.openrouter_base_url.rstrip('/')
        self.model = model or settings.openrouter_model
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=60.0,
            headers={
                'Authorization': f'Bearer {resolved_api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://github.com/Kapustin-Team/html-ml',
                'X-Title': 'html-ml',
            },
        )

    def chat_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> dict[str, Any]:
        payload = {
            'model': self.model,
            'temperature': temperature,
            'response_format': {'type': 'json_object'},
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
        }
        response = self.client.post('/chat/completions', json=payload)
        response.raise_for_status()
        data = response.json()
        content = data['choices'][0]['message']['content']
        if isinstance(content, list):
            text = ''.join(part.get('text', '') for part in content if isinstance(part, dict))
        else:
            text = str(content)
        return json.loads(text)
