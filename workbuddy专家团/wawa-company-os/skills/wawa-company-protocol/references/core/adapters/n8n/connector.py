# core/adapters/n8n/connector.py
import os
import json
import requests
from typing import Dict, Any, Optional

class N8nAdapter:
    """n8n 自动化扩展接入层。

    External execution is blocked unless an explicit webhook URL is configured.
    """
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("N8N_WEBHOOK_URL")
        
    def trigger_workflow(self, workflow_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.webhook_url:
            return {"ok": False, "error": "N8N_WEBHOOK_URL not configured."}
            
        url = f"{self.webhook_url}/{workflow_id}"
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return {"ok": True, "data": response.json()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def execute_sql(self, connection_id: str, query: str) -> Dict[str, Any]:
        payload = {
            "action": "execute_query",
            "connection_id": connection_id,
            "query": query
        }
        return self.trigger_workflow("sql-proxy-webhook", payload)
