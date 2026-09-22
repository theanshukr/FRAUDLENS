import os

cases_dir = r'C:\Users\kanav\OneDrive\Desktop\fraudlens\FRAUDLENS\cases'
count = 0
for f in os.listdir(cases_dir):
    if f.endswith('.json'):
        path = os.path.join(cases_dir, f)
        with open(path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        if ': NaN' in content:
            content = content.replace(': NaN', ': null')
            with open(path, 'w', encoding='utf-8') as file:
                file.write(content)
            count += 1

print(f'Fixed {count} files')
