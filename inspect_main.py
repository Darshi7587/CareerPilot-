from pathlib import Path
p = Path('C:/Users/darsh/Downloads/Placement/careerpilot/backend/main.py')
text = p.read_text(encoding='utf-8')
start = text.index('def chat')
end = text.index('def list_documents')
print(text[start:end])
