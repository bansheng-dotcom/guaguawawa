class BaseAdapter:
    def validate(self, input_data: dict) -> dict:
        raise NotImplementedError
        
    def execute(self, input_data: dict, context: dict) -> dict:
        raise NotImplementedError
        
    def receipt(self, output_data: dict) -> dict:
        raise NotImplementedError
