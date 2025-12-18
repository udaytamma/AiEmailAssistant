#!/usr/bin/env python3
"""
Generate HTML documentation from markdown - can be printed to PDF from browser
"""

import markdown

# Read markdown file
with open('EMAIL_ASSISTANT_DOCUMENTATION.md', 'r') as f:
    md_content = f.read()

# Convert markdown to HTML with extensions
html_body = markdown.markdown(
    md_content,
    extensions=['tables', 'fenced_code', 'toc', 'codehilite']
)

# Create full HTML document with professional styling
html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Assistant - Technical Documentation</title>
    <style>
        @media print {{
            body {{
                margin: 0;
                padding: 20px;
            }}
            h1 {{
                page-break-before: always;
            }}
            h1:first-of-type {{
                page-break-before: avoid;
            }}
            pre, table {{
                page-break-inside: avoid;
            }}
            .no-print {{
                display: none;
            }}
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
            background-color: #f8f9fa;
        }}

        .container {{
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        h1 {{
            color: #2c3e50;
            border-bottom: 4px solid #3498db;
            padding-bottom: 12px;
            margin: 40px 0 20px 0;
            font-size: 2.5em;
        }}

        h1:first-child {{
            margin-top: 0;
            font-size: 3em;
        }}

        h2 {{
            color: #34495e;
            border-bottom: 2px solid #95a5a6;
            padding-bottom: 8px;
            margin: 30px 0 15px 0;
            font-size: 1.8em;
        }}

        h3 {{
            color: #3498db;
            margin: 25px 0 12px 0;
            font-size: 1.4em;
        }}

        h4 {{
            color: #555;
            margin: 20px 0 10px 0;
            font-size: 1.2em;
        }}

        p {{
            margin: 12px 0;
        }}

        code {{
            background-color: #f4f4f4;
            padding: 3px 7px;
            border-radius: 4px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.9em;
            color: #e74c3c;
        }}

        pre {{
            background-color: #282c34;
            color: #abb2bf;
            border-radius: 6px;
            padding: 20px;
            overflow-x: auto;
            margin: 20px 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}

        pre code {{
            background-color: transparent;
            padding: 0;
            color: #abb2bf;
            font-size: 0.85em;
        }}

        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 25px 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}

        th {{
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}

        td {{
            border: 1px solid #ddd;
            padding: 12px;
        }}

        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}

        tr:hover {{
            background-color: #f1f1f1;
        }}

        ul, ol {{
            margin: 15px 0;
            padding-left: 40px;
        }}

        li {{
            margin: 8px 0;
        }}

        blockquote {{
            border-left: 5px solid #3498db;
            padding-left: 20px;
            margin: 20px 0;
            color: #555;
            font-style: italic;
            background-color: #f8f9fa;
            padding: 15px 20px;
            border-radius: 4px;
        }}

        hr {{
            border: none;
            border-top: 3px solid #ecf0f1;
            margin: 40px 0;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: bold;
            margin-left: 8px;
        }}

        .badge-complete {{
            background-color: #2ecc71;
            color: white;
        }}

        .badge-pending {{
            background-color: #e74c3c;
            color: white;
        }}

        .btn-download {{
            display: inline-block;
            background-color: #3498db;
            color: white;
            padding: 12px 24px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: 600;
            margin: 20px 0;
            transition: background-color 0.3s;
        }}

        .btn-download:hover {{
            background-color: #2980b9;
        }}

        .print-hint {{
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}

        .toc {{
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}

        .toc a {{
            color: #3498db;
            text-decoration: none;
        }}

        .toc a:hover {{
            text-decoration: underline;
        }}

        a {{
            color: #3498db;
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="print-hint no-print">
            <strong>💡 Tip:</strong> To save this as a PDF, use your browser's Print function (Cmd/Ctrl + P) and select "Save as PDF" as the destination.
        </div>

        {html_body}

        <hr>
        <p style="text-align: center; color: #777; margin-top: 40px;">
            <em>Email Assistant Documentation v1.0 | Generated on December 17, 2025</em>
        </p>
    </div>
</body>
</html>
"""

# Write HTML file
output_file = 'Email_Assistant_Documentation.html'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_doc)

print(f"✅ HTML documentation generated successfully!")
print(f"📄 File: /Users/omega/Projects/emailAssistant/{output_file}")
print(f"\n📋 To create a PDF:")
print(f"   1. Open {output_file} in your browser")
print(f"   2. Press Cmd+P (Mac) or Ctrl+P (Windows)")
print(f"   3. Select 'Save as PDF' as the destination")
print(f"   4. Click 'Save'")
