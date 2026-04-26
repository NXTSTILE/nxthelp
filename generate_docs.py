import markdown
import os

# Read the markdown file
with open('NxtHelp_Developer_Architecture_Guide.md', 'r', encoding='utf-8') as f:
    md_content = f.read()

# Convert markdown to HTML with extensions
html_body = markdown.markdown(
    md_content,
    extensions=[
        'tables',
        'fenced_code',
        'toc',
        'nl2br',
    ]
)

# Build full HTML with print-optimized CSS
html_template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NxtHelp Developer Architecture Guide</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm 1.5cm;
        }}
        * {{
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #1e293b;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
            background: #fff;
        }}
        h1 {{
            font-size: 2.2rem;
            color: #5b21b6;
            border-bottom: 3px solid #7c3aed;
            padding-bottom: 0.5rem;
            margin-top: 0;
            page-break-after: avoid;
        }}
        h2 {{
            font-size: 1.6rem;
            color: #4c1d95;
            margin-top: 2rem;
            border-bottom: 1px solid #ddd6fe;
            padding-bottom: 0.3rem;
            page-break-after: avoid;
        }}
        h3 {{
            font-size: 1.25rem;
            color: #5b21b6;
            margin-top: 1.5rem;
            page-break-after: avoid;
        }}
        h4 {{
            font-size: 1.1rem;
            color: #334155;
            margin-top: 1.2rem;
            page-break-after: avoid;
        }}
        p {{
            margin: 0.75rem 0;
        }}
        a {{
            color: #7c3aed;
            text-decoration: none;
        }}
        code {{
            background: #f5f3ff;
            color: #5b21b6;
            padding: 0.15rem 0.35rem;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
        }}
        pre {{
            background: #0f172a;
            color: #e2e8f0;
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.85rem;
            line-height: 1.5;
            page-break-inside: avoid;
        }}
        pre code {{
            background: transparent;
            color: inherit;
            padding: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 0.95rem;
            page-break-inside: avoid;
        }}
        th, td {{
            border: 1px solid #e2e8f0;
            padding: 0.6rem 0.8rem;
            text-align: left;
        }}
        th {{
            background: #f5f3ff;
            color: #5b21b6;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background: #f8fafc;
        }}
        ul, ol {{
            margin: 0.75rem 0;
            padding-left: 1.5rem;
        }}
        li {{
            margin: 0.35rem 0;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e2e8f0;
            margin: 2rem 0;
        }}
        blockquote {{
            border-left: 4px solid #7c3aed;
            background: #f5f3ff;
            padding: 0.75rem 1rem;
            margin: 1rem 0;
            border-radius: 0 8px 8px 0;
        }}
        .toc ul {{
            list-style: none;
            padding-left: 0;
        }}
        .toc ul ul {{
            padding-left: 1.5rem;
        }}
        .toc a {{
            color: #475569;
        }}
        .toc a:hover {{
            color: #7c3aed;
        }}
        @media print {{
            body {{
                padding: 0;
                max-width: 100%;
            }}
            h1, h2, h3, h4 {{
                page-break-after: avoid;
            }}
            pre, table, blockquote {{
                page-break-inside: avoid;
            }}
            a {{
                text-decoration: none;
                color: #1e293b;
            }}
        }}
    </style>
</head>
<body>
{html_body}
</body>
</html>
'''

# Write HTML file
html_path = 'NxtHelp_Developer_Architecture_Guide.html'
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_template)

print(f'HTML documentation generated: {os.path.abspath(html_path)}')

# Try to generate PDF using Microsoft Edge headless mode
pdf_path = os.path.abspath('NxtHelp_Developer_Architecture_Guide.pdf')
html_abs_path = os.path.abspath(html_path)

# Common Edge paths on Windows
edge_paths = [
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
]

edge_exe = None
for path in edge_paths:
    if os.path.exists(path):
        edge_exe = path
        break

if edge_exe:
    import subprocess
    cmd = [
        edge_exe,
        '--headless',
        '--disable-gpu',
        '--run-all-compositor-stages-before-draw',
        f'--print-to-pdf={pdf_path}',
        f'file:///{html_abs_path.replace(chr(92), "/")}'
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if os.path.exists(pdf_path):
            print(f'PDF documentation generated: {pdf_path}')
        else:
            print('Edge did not generate PDF. Stderr:', result.stderr)
    except Exception as e:
        print(f'Failed to generate PDF via Edge: {e}')
else:
    print('Microsoft Edge not found. PDF generation skipped.')
    print('To create a PDF, open the HTML file in any browser and use Print -> Save as PDF.')
