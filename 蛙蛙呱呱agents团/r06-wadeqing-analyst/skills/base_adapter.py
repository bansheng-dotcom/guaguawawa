import abc
from typing import Any, Dict

class BaseAdapter(abc.ABC):
    """
    智能体技能适配器基类 (Adapter Layer)。
    将以前的“纯 JSON 规则门禁”改造为真实的业务动作执行器。
    """
    
    def __init__(self, rule_config: Dict[str, Any] = None):
        """
        初始化适配器。
        :param rule_config: 传入外置的业务规则字典（不再在代码里硬编码阈值）
        """
        self.rule_config = rule_config or {}
        
    @abc.abstractmethod
    def validate(self, input_data: Any) -> bool:
        """
        第一阶段：校验输入数据是否符合该技能的契约预期 (Schema Validation)。
        如缺少关键列，直接抛出异常或返回 False。
        """
        pass
        
    @abc.abstractmethod
    def execute(self, input_data: Any, **kwargs) -> Any:
        """
        第二阶段：执行真实的业务动作 (Real Execution)。
        调用如 Pandas, SQLAlchemy,外部 API 等处理数据。
        """
        pass
        
    @abc.abstractmethod
    def get_receipt(self, execute_result: Any) -> Dict[str, Any]:
        """
        第三阶段：签发回执 (Receipt Generation)。
        将真实的执行结果打包成符合 `contracts.py` 门禁要求的标准 JSON 回执，
        供下游环节继续流转。
        """
        pass
        
    def run_pipeline(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        """标准流水线"""
        if not self.validate(input_data):
            return {"ok": False, "error": "Validation failed"}
        result = self.execute(input_data, **kwargs)
        return self.get_receipt(result)
