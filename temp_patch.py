from pathlib import Path

path = Path(r"C:\Users\darsh\Downloads\Placement\careerpilot\frontend\streamlit_app.py")
lines = path.read_text(encoding='utf-8').splitlines()
start = None
end = None
for idx, line in enumerate(lines):
    if 'fig = go.Figure(go.Indicator(mode="gauge+number"' in line:
        start = idx
        break
if start is None:
    raise SystemExit('target start not found')
end = start + 10
replacement = [
    '        if ats is not None:',
    '            fig = go.Figure(',
    '                go.Indicator(',
    '                    mode="gauge+number",',
    '                    value=ats,',
    '                    domain={"x": [0, 1], "y": [0, 1]},',
    '                    title={"text": "ATS Score"},',
    '                    gauge={',
    '                        "axis": {"range": [0, 100]},',
    '                        "bar": {"color": "#38bdf8"},',
    '                        "steps": [',
    '                            {"range": [0, 50], "color": "rgba(251,113,133,0.3)"},',
    '                            {"range": [50, 75], "color": "rgba(251,191,36,0.3)"},',
    '                            {"range": [75, 100], "color": "rgba(52,211,153,0.3)"},',
    '                        ],',
    '                    },',
    '                )',
    '            )',
    '            fig.update_layout(height=260, margin=dict(t=40, b=0, l=20, r=20), paper_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0")',
    '            st.plotly_chart(fig, use_container_width=True)',
]
new_lines = lines[:start] + replacement + lines[end:]
path.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')
print('patched')
