
import os

file_path = 'c:\\Dev\\Vectra\\scripts\\start_ollama.sh'

with open(file_path, 'rb') as f:
    content = f.read()

# Replace CRLF with LF
content = content.replace(b'\r\n', b'\n')

with open(file_path, 'wb') as f:
    f.write(content)

print(f"Converted {file_path} to LF line endings.")
