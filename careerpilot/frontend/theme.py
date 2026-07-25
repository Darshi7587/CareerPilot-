"""Global CSS theme for CareerPilot AI."""

GLOBAL_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --bg-primary: #050810;
    --bg-secondary: #0b1220;
    --bg-card: rgba(15, 23, 42, 0.72);
    --border-subtle: rgba(148, 163, 184, 0.14);
    --border-accent: rgba(56, 189, 248, 0.35);
    --text-primary: #f8fafc;
    --text-secondary: rgba(203, 213, 225, 0.88);
    --text-muted: rgba(148, 163, 184, 0.72);
    --accent-cyan: #38bdf8;
    --accent-purple: #a855f7;
    --accent-emerald: #34d399;
    --accent-amber: #fbbf24;
    --gradient-primary: linear-gradient(135deg, #38bdf8 0%, #818cf8 45%, #a855f7 100%);
    --radius-lg: 22px;
    --radius-md: 14px;
    --radius-sm: 10px;
    --shadow-card: 0 12px 40px rgba(0, 0, 0, 0.35);
    --transition: all 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}

.stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background:
        radial-gradient(ellipse at 8% 0%, rgba(56, 189, 248, 0.10), transparent 55%),
        radial-gradient(ellipse at 92% 0%, rgba(168, 85, 247, 0.08), transparent 55%),
        radial-gradient(ellipse at 50% 100%, rgba(52, 211, 153, 0.05), transparent 55%),
        linear-gradient(180deg, var(--bg-primary) 0%, var(--bg-secondary) 100%) !important;
    color: var(--text-primary) !important;
}

html, body, [class*="st-"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

.block-container {
    padding-top: 1rem !important;
    padding-bottom: 2rem !important;
    max-width: 1440px !important;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #070c16 0%, #0a1222 100%) !important;
    border-right: 1px solid var(--border-subtle) !important;
}

section[data-testid="stSidebar"] .stButton > button {
    justify-content: flex-start !important;
    text-align: left !important;
    background: transparent !important;
    border: 1px solid transparent !important;
    padding: 0.55rem 0.85rem !important;
    font-weight: 500 !important;
}

section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(56, 189, 248, 0.08) !important;
    border-color: rgba(56, 189, 248, 0.2) !important;
}

section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: rgba(56, 189, 248, 0.14) !important;
    border-color: rgba(56, 189, 248, 0.35) !important;
    color: #e0f2fe !important;
}

div[data-testid="stChatMessage"] {
    border-radius: 16px !important;
    border: 1px solid var(--border-subtle) !important;
    backdrop-filter: blur(14px) !important;
    margin-bottom: 0.55rem !important;
}

.stButton > button {
    border-radius: var(--radius-sm) !important;
    transition: var(--transition) !important;
}

.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(56, 189, 248, 0.12) !important;
}

button[kind="primary"], .stButton > button[kind="primary"] {
    background: var(--gradient-primary) !important;
    color: white !important;
    border: none !important;
}

.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div,
.stNumberInput > div > div > input {
    background: rgba(15, 23, 42, 0.65) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-primary) !important;
}

div[data-testid="stFileUploader"] > div {
    background: rgba(15, 23, 42, 0.45) !important;
    border: 2px dashed rgba(56, 189, 248, 0.28) !important;
    border-radius: var(--radius-md) !important;
}

div[data-testid="stMetric"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    padding: 0.85rem !important;
    backdrop-filter: blur(12px) !important;
}

.hero-section {
    padding: 2.2rem 2.4rem;
    border-radius: var(--radius-lg);
    border: 1px solid var(--border-subtle);
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(2, 6, 23, 0.78));
    box-shadow: var(--shadow-card);
    margin-bottom: 1.4rem;
}

.hero-section h1 {
    background: var(--gradient-primary);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 2.5rem;
    font-weight: 800;
    margin: 0;
    line-height: 1.08;
}

.hero-section p { color: var(--text-secondary); line-height: 1.65; }

.stat-card {
    padding: 1.15rem 1.35rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--border-subtle);
    background: var(--bg-card);
    backdrop-filter: blur(12px);
    box-shadow: var(--shadow-card);
    transition: var(--transition);
    min-height: 108px;
}

.stat-card:hover {
    border-color: var(--border-accent);
    transform: translateY(-2px);
}

.stat-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: var(--text-muted);
    font-weight: 600;
}

.stat-value { font-size: 1.65rem; font-weight: 700; margin: 0.2rem 0; }
.stat-caption { font-size: 0.8rem; color: var(--text-muted); }

.feature-card {
    padding: 1.25rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--border-subtle);
    background: var(--bg-card);
    backdrop-filter: blur(12px);
    box-shadow: var(--shadow-card);
    transition: var(--transition);
    height: 100%;
}

.feature-card:hover {
    border-color: var(--border-accent);
    transform: translateY(-3px);
}

.feature-icon { font-size: 1.85rem; margin-bottom: 0.55rem; display: block; }
.feature-title { font-size: 1.02rem; font-weight: 600; margin-bottom: 0.3rem; }
.feature-desc { font-size: 0.86rem; color: var(--text-secondary); line-height: 1.55; }

.section-header { font-size: 1.45rem; font-weight: 700; margin-bottom: 0.25rem; }
.section-sub { font-size: 0.9rem; color: var(--text-muted); margin-bottom: 1rem; }

.badge {
    display: inline-block;
    padding: 0.18rem 0.55rem;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-right: 0.35rem;
}

.badge-agent { background: rgba(56, 189, 248, 0.16); color: #7dd3fc; }
.badge-planner { background: rgba(168, 85, 247, 0.16); color: #d8b4fe; }
.badge-route { background: rgba(52, 211, 153, 0.16); color: #6ee7b7; }
.badge-success { background: rgba(52, 211, 153, 0.15); color: #34d399; }
.badge-warning { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }

.empty-state { text-align: center; padding: 2.8rem 1.5rem; color: var(--text-muted); }
.empty-state .empty-icon { font-size: 3rem; opacity: 0.55; margin-bottom: 0.75rem; }

.status-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 6px;
}
.status-online { background: #34d399; box-shadow: 0 0 8px rgba(52, 211, 153, 0.55); }
.status-offline { background: #fb7185; box-shadow: 0 0 8px rgba(251, 113, 133, 0.55); }

.divider { height: 1px; background: var(--border-subtle); margin: 1rem 0; }

@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
.animate-in { animation: fadeInUp 0.45s ease-out; }

.nav-brand {
    text-align: center;
    padding: 0.4rem 0 0.9rem;
}
.nav-brand h2 {
    margin: 0.35rem 0 0;
    font-size: 1.22rem;
    font-weight: 700;
    background: var(--gradient-primary);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
"""
