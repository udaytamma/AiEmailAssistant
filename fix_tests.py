"""Quick fix script to remove freezegun dependencies"""
import re

files_to_fix = [
    'tests/conftest.py',
    'tests/unit/test_cache_manager.py',
    'tests/integration/test_email_flow.py'
]

for file_path in files_to_fix:
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Remove freezegun imports
    content = re.sub(r'from freezegun import freeze_time\n', '', content)
    content = re.sub(r'import freezegun\n', '', content)
    
    # Comment out freezegun fixture
    content = re.sub(r'@pytest.fixture\ndef frozen_time\(\):.*?yield frozen_datetime\n', 
                     '# Freezegun fixture removed - not compatible with Python 3.14\n', 
                     content, flags=re.DOTALL)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Fixed {file_path}")
