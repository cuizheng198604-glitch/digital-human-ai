import os
import shutil
from pathlib import Path

# 创建部署包
base = Path(r'C:\Users\Administrator\Projects\digital_human_ai')
output = Path(r'C:\Users\Administrator\Desktop\digital_human_deploy.zip')

# 要复制的文件和目录
items = [
    'web/app.py',
    'web/*.html',
    'modeling/personality_encoder.py',
    'modeling/social_media_collector.py',
    'engine/llm_engine.py',
    'engine/persona_filter.py',
    'engine/memory_retriever.py',
    'questionnaire/questionnaire_engine.py',
    'config/settings.py',
    'main.py',
    'requirements.txt',
    'README.md',
]

print("创建部署包...")

# 创建临时目录
import zipfile
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
    for pattern in items:
        if '*' in pattern:
            # 处理通配符
            dir_part = os.path.dirname(pattern)
            file_part = os.path.basename(pattern)
            full_dir = base / dir_part
            if full_dir.exists():
                for f in full_dir.glob(file_part):
                    arcname = str(f.relative_to(base))
                    zf.write(f, arcname)
                    print(f"  + {arcname}")
        else:
            # 处理具体文件
            f = base / pattern
            if f.exists():
                if f.is_file():
                    arcname = pattern
                    zf.write(f, arcname)
                    print(f"  + {arcname}")
            else:
                # 可能是 __init__.py
                init_file = base / pattern.replace('/', '/__init__.py').replace('\\', '/')
                if init_file.exists():
                    arcname = pattern.replace('.py', '/__init__.py')
                    zf.write(init_file, arcname)
                    print(f"  + {arcname}")

print(f"\n部署包已创建: {output}")
print(f"大小: {output.stat().st_size / 1024:.1f} KB")
