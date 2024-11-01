from typing import Dict, Any, Optional, Generator

from .mongodb_cache import llm_api_cache
from .baidu_api import stream_chat_with_wenxin, wenxin_model_config
from .doubao_api import stream_chat_with_doubao, doubao_model_config
from .chat_messages import ChatMessages
from .openai_api import stream_chat_with_gpt, gpt_model_config

class ModelConfig(dict):
    def __init__(self, model: str, **options):
        super().__init__(**options)
        self['model'] = model
        self.validate()

    def validate(self):
        if self['model'] in wenxin_model_config:
            for key in ['ak', 'sk']:
                if key not in self:
                    raise ValueError(f"Missing required key: {key}")
        elif self['model'] in doubao_model_config:
            for key in ['api_key', 'endpoint_id']:
                if key not in self:
                    raise ValueError(f"Missing required key: {key}")
        elif self['model'] in gpt_model_config or True:
            # 其他模型名默认采用openai接口调用
            for key in ['api_key']:
                if key not in self:
                    raise ValueError(f"Missing required key: {key}")
        
        if 'max_tokens' not in self:
            raise ValueError('Missing required key: max_tokens')


    def get_api_keys(self) -> Dict[str, str]:
        return {k: v for k, v in self.items() if k not in ['model']}

@llm_api_cache(db_name='llm_api', collection_name='stream_chat')
def stream_chat(model_config: ModelConfig, messages: list, response_json=False) -> Generator:
    if isinstance(model_config, dict):
        model_config = ModelConfig(**model_config)
    
    model_config.validate()
    
    if model_config['model'] in wenxin_model_config:
        result = yield from stream_chat_with_wenxin(
            messages,
            model=model_config['model'],
            ak=model_config['ak'],
            sk=model_config['sk'],
            max_tokens=model_config['max_tokens'],
            response_json=response_json
        )
    elif model_config['model'] in doubao_model_config:  # doubao models
        result = yield from stream_chat_with_doubao(
            messages,
            model=model_config['model'],
            endpoint_id=model_config['endpoint_id'],
            api_key=model_config['api_key'],
            max_tokens=model_config['max_tokens'],
            response_json=response_json
        )
    elif model_config['model'] in gpt_model_config or True:  # openai models或其他兼容openai接口的模型
        result = yield from stream_chat_with_gpt(
            messages,
            model=model_config['model'],
            api_key=model_config['api_key'],
            base_url=model_config.get('base_url'),
            max_tokens=model_config['max_tokens'],
            response_json=response_json
        )

    return result

def test_stream_chat(model_config: ModelConfig):
    messages = [{"role": "user", "content": "1+1=?直接输出答案即可："}]
    for response in stream_chat(model_config, messages, use_cache=False):
        yield response.response
    
    return response

# 导出必要的函数和配置
__all__ = ['ChatMessages', 'stream_chat', 'wenxin_model_config', 'doubao_model_config', 'gpt_model_config', 'ModelConfig']
