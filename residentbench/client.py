"""Optional OpenRouter client. Credentials are loaded only during a live rerun."""
import json
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

class OpenRouter:
    system=''
    def __init__(self,model,key_path):
        self.model=model
        self._key=Path(key_path).read_text(encoding='utf-8').strip()
        if not self._key: raise ValueError('OpenRouter key file is empty')
    def generate_raw(self,prompt,tools=None,temperature=None,tool_choice='auto',extra=None,timeout=120,max_tokens=4096):
        body={'model':self.model,'messages':[{'role':'user','content':prompt}],'tools':tools,'tool_choice':tool_choice,'max_tokens':max_tokens}
        if temperature is not None: body['temperature']=temperature
        body.update(extra or {})
        request=Request('https://openrouter.ai/api/v1/chat/completions',data=json.dumps(body).encode('utf-8'),headers={'Authorization':'Bearer '+self._key,'Content-Type':'application/json','HTTP-Referer':'https://www.pseudoconscious.com/','X-OpenRouter-Title':'PseudoAgent'})
        try:
            with urlopen(request,timeout=timeout) as response: return json.loads(response.read().decode('utf-8'))
        except HTTPError as error: raise RuntimeError(f'OpenRouter HTTP {error.code}') from None
        except (URLError,TimeoutError): raise RuntimeError('OpenRouter network request failed') from None
