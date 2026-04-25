import os
import re

# Configuration
REPLACEMENTS = {
    # Name rebrand
    'NxtHelp': 'UniConnect',
    # Icon rebrand (only brand instances — all 4 occurrences are brand-related)
    'fa-hands-helping': 'fa-share-nodes',
    # Core color mappings (blue → violet)
    '#1d4ed8': '#7c3aed',
    '#1e40af': '#6d28d9',
    '#2563eb': '#8b5cf6',
    '#93c5fd': '#c4b5fd',
    '#eff6ff': '#f5f3ff',
    '#dbeafe': '#ede9fe',
    '#fafcff': '#faf5ff',
    # RGBA mappings (blue rgb → violet rgb)
    '29, 78, 216': '124, 58, 237',
    '29,78,216': '124,58,237',
}

CSS_VAR_REPLACEMENTS = {
    '--blue:': '--primary:',
    '--blue-dark:': '--primary-dark:',
    '--blue-light:': '--primary-light:',
    'var(--blue)': 'var(--primary)',
    'var(--blue-dark)': 'var(--primary-dark)',
    'var(--blue-light)': 'var(--primary-light)',
}

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Generic replacements
    for old, new in REPLACEMENTS.items():
        content = content.replace(old, new)

    # CSS variable replacements (CSS files only)
    if filepath.endswith('.css'):
        for old, new in CSS_VAR_REPLACEMENTS.items():
            content = content.replace(old, new)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated: {filepath}')
    else:
        print(f'No changes: {filepath}')

def main():
    dirs = ['templates', 'accounts', 'work', 'chat', 'static']
    for root_dir in dirs:
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith(('.html', '.css')):
                    filepath = os.path.join(root, file)
                    process_file(filepath)

if __name__ == '__main__':
    main()
