import os
import codecs

def convert_to_utf8(file_path):
    # Try reading with common encodings
    for encoding in ['gbk', 'utf-8-sig', 'utf-16']:
        try:
            with codecs.open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            # If successful, write back as utf-8
            with codecs.open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Converted: {file_path} to UTF-8 (from {encoding})")
            return
        except (UnicodeDecodeError, LookupError):
            continue
    print(f"Failed to convert: {file_path}")

for root, dirs, files in os.walk("D:\\蛙蛙呱呱\\蛙蛙呱呱agents团"):
    for file in files:
        if file.endswith((".py", ".md")):
            file_path = os.path.join(root, file)
            convert_to_utf8(file_path)
