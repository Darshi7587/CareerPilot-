from pathlib import Path
import importlib.util
import sys

path = Path('C:/Users/darsh/Downloads/Placement/careerpilot/backend/main.py')
text = path.read_text(encoding='utf-8')
print('PATH_EXISTS', path.exists())
print('HAS_HISTORY_LIMIT', 'history_limit' in text)
print('HAS_OLD_ATTR', 'conversation_history_limit' in text)
for line in text.splitlines():
    if 'history' in line and 'checkpoint_store' in line:
        print(line)

spec = importlib.util.spec_from_file_location('careerpilot.backend.main', path)
module = importlib.util.module_from_spec(spec)
sys.modules['careerpilot.backend.main'] = module
spec.loader.exec_module(module)
print('IMPORTED_MODULE', module.__file__)
print(module.chat.__code__.co_firstlineno)
import inspect
print(inspect.getsource(module.chat))
