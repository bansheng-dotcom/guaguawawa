from .._template.base_adapter import BaseAdapter

class N8nAdapter(BaseAdapter):
    def validate(self, input_data: dict) -> dict:
        if "workflow_id" not in input_data:
            return {"valid": False, "errors": ["Missing workflow_id"]}
        return {"valid": True, "errors": []}
        
    def execute(self, input_data: dict, context: dict) -> dict:
        # TODO: 使用 requests 或 httpx 真实调用 n8n webhook API
        # 这里严禁“假执行”，不可达则返回 blocked
        return {"status": "blocked", "raw_response": {"error": "N8N host not configured"}}
        
    def receipt(self, output_data: dict) -> dict:
        return {"receipt_id": "receipt-n8n-blocked", "details": output_data}
