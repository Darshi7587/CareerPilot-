"""CareerPilot AI — production SaaS dashboard (Streamlit)."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is in sys.path for Streamlit
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import re
import uuid
from datetime import datetime
from typing import Any

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    go = None

import streamlit as st

from careerpilot.frontend.api_client import (
    DEFAULT_BACKEND,
    api_delete,
    api_get,
    api_login,
    api_reindex,
    api_signup,
    api_upload,
    check_health,
    send_chat,
    stream_chat,
)
from careerpilot.frontend.theme import GLOBAL_CSS

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

PAGES: dict[str, dict[str, str]] = {
    "Dashboard": {"icon": "🏠", "key": "dashboard", "focus": "all"},
    "Resume Analyzer": {"icon": "📄", "key": "resume", "focus": "resume"},
    "Company Research": {"icon": "🏢", "key": "company", "focus": "company"},
    "RAG Knowledge Base": {"icon": "📚", "key": "rag", "focus": "rag"},
    "Coding Assistant": {"icon": "💻", "key": "coding", "focus": "coding"},
    "Mock Interview": {"icon": "🎤", "key": "interview", "focus": "interview"},
    "Roadmap Generator": {"icon": "🗺️", "key": "roadmap", "focus": "roadmap"},
    "Progress Analytics": {"icon": "📈", "key": "analytics", "focus": "all"},
    "Settings": {"icon": "⚙️", "key": "settings", "focus": "all"},
}

QUICK_ACTIONS = {
    "Resume review": ("Resume Analyzer", "Analyze my resume for ATS score, missing skills, and improvements."),
    "Research Google": ("Company Research", "Research Google: hiring process, OA pattern, interview rounds, salary, and recent experiences."),
    "Mock HR interview": ("Mock Interview", "Start an HR mock interview. Ask one question at a time and score my answers."),
    "Debug Python code": ("Coding Assistant", "Review this Python code for bugs, time/space complexity, and optimization."),
    "4-week DSA plan": ("Roadmap Generator", "Create a 4-week DSA roadmap for placements with 2 hours per day."),
}

st.set_page_config(page_title="CareerPilot AI", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")
st.markdown(f"<style>{GLOBAL_CSS}</style>", unsafe_allow_html=True)


def init_state() -> None:
    defaults: dict[str, Any] = {
        "backend_url": DEFAULT_BACKEND,
        "session_id": f"cp-{uuid.uuid4().hex[:8]}",
        "logged_in": False,
        "user_info": None,
        "messages": [],
        "interview_messages": [],
        "page": "Dashboard",
        "last_route": "idle",
        "last_analysis": {},
        "resume_analysis": "",
        "company_result": "",
        "coding_result": "",
        "roadmap_result": "",
        "use_streaming": True,
        "theme": "dark",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


init_state()


def render_auth_page() -> None:
    """Render the Signup and Login landing view."""

    st.markdown(
        """
        <div style="max-width: 520px; margin: 3rem auto 2rem auto; text-align: center;">
            <span style="font-size: 3.8rem;">🚀</span>
            <h1 style="color: #f8fafc; font-size: 2.2rem; font-weight: 700; margin-top: 0.5rem;">Welcome to CareerPilot AI</h1>
            <p style="color: #94a3b8; font-size: 1rem;">Sign in or register an account to save your resume ATS analysis, RAG documents, and placement progress.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_signup = st.tabs(["🔑 Sign In", "📝 Create Account"])

        with tab_login:
            st.markdown("#### Sign In")
            login_user = st.text_input("Username or Email", key="login_username")
            login_pass = st.text_input("Password", type="password", key="login_password")
            if st.button("Sign In to CareerPilot", type="primary", use_container_width=True):
                if not login_user or not login_pass:
                    st.error("Please enter both username/email and password.")
                else:
                    res = api_login(login_user, login_pass)
                    if res:
                        st.session_state.logged_in = True
                        st.session_state.user_info = res
                        st.session_state.session_id = res["session_id"]
                        st.session_state.messages = []
                        st.session_state.interview_messages = []
                        st.toast(f"Welcome back, {res['full_name']}!", icon="👋")
                        st.rerun()

        with tab_signup:
            st.markdown("#### Register Account")
            reg_name = st.text_input("Full Name", key="reg_fullname")
            reg_user = st.text_input("Username", key="reg_username")
            reg_email = st.text_input("Email Address", key="reg_email")
            reg_pass = st.text_input("Password", type="password", key="reg_password")
            if st.button("Create Account", type="primary", use_container_width=True):
                if not reg_user or not reg_email or not reg_pass:
                    st.error("Please fill in all required fields.")
                else:
                    res = api_signup(username=reg_user, email=reg_email, password=reg_pass, full_name=reg_name)
                    if res:
                        st.session_state.logged_in = True
                        st.session_state.user_info = res
                        st.session_state.session_id = res["session_id"]
                        st.session_state.messages = []
                        st.session_state.interview_messages = []
                        st.success("Account registered successfully!")
                        st.toast(f"Welcome to CareerPilot, {res['full_name']}!", icon="🚀")
                        st.rerun()


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------


def render_stat(label: str, value: str, caption: str = "", color: str = "") -> None:
    style = f"color:{color};" if color else ""
    st.markdown(
        f"""<div class="stat-card animate-in">
        <div class="stat-label">{label}</div>
        <div class="stat-value" style="{style}">{value}</div>
        <div class="stat-caption">{caption}</div></div>""",
        unsafe_allow_html=True,
    )


def section(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="section-sub">{subtitle}</div>', unsafe_allow_html=True)


def feature_card(icon: str, title: str, desc: str) -> None:
    st.markdown(
        f"""<div class="feature-card animate-in">
        <span class="feature-icon">{icon}</span>
        <div class="feature-title">{title}</div>
        <div class="feature-desc">{desc}</div></div>""",
        unsafe_allow_html=True,
    )


def empty_state(icon: str, title: str, message: str) -> None:
    st.markdown(
        f"""<div class="empty-state animate-in">
        <div class="empty-icon">{icon}</div><h3>{title}</h3><p>{message}</p></div>""",
        unsafe_allow_html=True,
    )


def render_message_badges(msg: dict[str, Any]) -> None:
    route = msg.get("route", "")
    planner = msg.get("planner_source", "")
    elapsed = msg.get("execution_time_ms")
    badges = []
    if route and route != "error":
        badges.append(f'<span class="badge badge-route">{route}</span>')
    if planner:
        badges.append(f'<span class="badge badge-planner">{planner}</span>')
    if elapsed:
        badges.append(f'<span class="badge badge-agent">{elapsed}ms</span>')
    if badges:
        st.markdown(" ".join(badges), unsafe_allow_html=True)


def append_chat(message: str, focus: str, *, target: str = "messages") -> dict[str, Any] | None:
    cleaned = message.strip()
    if not cleaned:
        return None
    bucket: list[dict[str, Any]] = st.session_state[target]
    bucket.append({"role": "user", "content": cleaned, "ts": datetime.now().strftime("%I:%M %p")})

    if st.session_state.use_streaming:
        full = ""
        meta: dict[str, Any] = {}
        try:
            for chunk in stream_chat(cleaned, focus):
                full += chunk
            meta = getattr(st.session_state, "_stream_meta", {}) or {}
            result = {
                "route": meta.get("route", "fallback"),
                "response": full or getattr(st.session_state, "_stream_full", ""),
                "planner_source": meta.get("planner_source", ""),
                "execution_time_ms": meta.get("execution_time_ms", 0),
                "sources": meta.get("sources", []),
            }
        except Exception:
            result = send_chat(cleaned, focus)
    else:
        result = send_chat(cleaned, focus)

    if not result:
        bucket.append(
            {
                "role": "assistant",
                "content": "Could not reach the backend. Ensure FastAPI is running on port 8000.",
                "route": "error",
                "ts": datetime.now().strftime("%I:%M %p"),
            }
        )
        return None

    bucket.append(
        {
            "role": "assistant",
            "content": result.get("response", ""),
            "route": result.get("route", result.get("agent", "fallback")),
            "planner_source": result.get("planner_source", ""),
            "execution_time_ms": result.get("execution_time_ms", 0),
            "sources": result.get("sources", []),
            "ts": datetime.now().strftime("%I:%M %p"),
        }
    )
    route_name = result.get("route", result.get("agent", "fallback"))
    response_text = result.get("response", "")
    if route_name == "resume" or focus == "resume":
        st.session_state.resume_analysis = response_text
    elif route_name == "company" or focus == "company":
        st.session_state.company_result = response_text
    elif route_name == "coding" or focus == "coding":
        st.session_state.coding_result = response_text
    elif route_name == "roadmap" or focus == "roadmap":
        st.session_state.roadmap_result = response_text

    st.session_state.last_route = route_name
    st.toast(f"Routed → {route_name}", icon="🧭")
    return result


def extract_ats_score(text: str) -> int | None:
    patterns = [
        r"ats[^0-9]{0,30}(\d{1,3})\s*(?:/100|%)?",
        r"score[^0-9]{0,20}(\d{1,3})\s*/\s*100",
        r"(\d{1,3})\s*/\s*100",
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            val = int(match.group(1))
            if 0 <= val <= 100:
                return val
    return None


def fetch_analytics() -> dict[str, Any]:
    data = api_get("/analytics", {"session_id": st.session_state.session_id}, silent=True)
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def page_dashboard() -> None:
    st.markdown(
        """<div class="hero-section animate-in">
        <h1>Welcome to CareerPilot AI</h1>
        <p>Your autonomous multi-agent placement coach — resume analysis, company intel,
        mock interviews, coding mentorship, roadmaps, and document-grounded answers.</p></div>""",
        unsafe_allow_html=True,
    )

    analytics = fetch_analytics()
    health = check_health(st.session_state.backend_url)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_stat("Backend", "ONLINE" if health else "OFFLINE", "API health", "#34d399" if health else "#fb7185")
    with c2:
        render_stat("Streak", f"{analytics.get('learning_streak_days', 0)}d", "Learning streak", "#fbbf24")
    with c3:
        render_stat("Interview", f"{analytics.get('interview_score_avg', 0) or '—'}", "Avg score /10", "#a855f7")
    with c4:
        render_stat("Coding", str(analytics.get('problems_solved', 0)), "Sessions solved", "#38bdf8")
    with c5:
        score = analytics.get("resume_score_latest", 0)
        render_stat("Resume ATS", f"{score or '—'}", "Latest score", "#34d399")

    st.markdown("---")
    section("⚡ Quick Actions", "Jump into a workflow with one click")
    cols = st.columns(len(QUICK_ACTIONS))
    for col, (label, (page, prompt)) in zip(cols, QUICK_ACTIONS.items()):
        with col:
            if st.button(label, key=f"qa-{label}", use_container_width=True):
                st.session_state.page = page
                append_chat(prompt, PAGES[page]["focus"])
                st.rerun()

    st.markdown("---")
    section("🎯 Platform Capabilities")
    features = [
        ("📄", "Resume Analyzer", "ATS scoring, skill gaps, interview questions, skill graph."),
        ("🏢", "Company Research", "Live web search for hiring process, OA, rounds, salary."),
        ("📚", "RAG Knowledge Base", "Upload PDFs and ask citation-backed questions."),
        ("💻", "Coding Assistant", "Bug detection, complexity analysis, optimized solutions."),
        ("🎤", "Mock Interview", "HR & technical interviews with scoring and feedback."),
        ("🗺️", "Roadmap Generator", "Weekly plans, daily tasks, projects, revision schedule."),
    ]
    for i in range(0, len(features), 3):
        cols = st.columns(3)
        for col, item in zip(cols, features[i : i + 3]):
            with col:
                feature_card(*item)

    st.markdown("---")
    section("📜 Recent Activity")
    recent = analytics.get("recent_activity") or []
    if recent:
        for item in recent[:6]:
            st.markdown(
                f"**{item.get('route', 'agent').title()}** — {item.get('query', '')[:100]}… "
                f"<span class='badge badge-planner'>{item.get('planner_source', '')}</span>",
                unsafe_allow_html=True,
            )
    else:
        empty_state("📭", "No activity yet", "Use quick actions above to start your preparation journey.")


def page_resume() -> None:
    section("📄 Resume Analyzer", "Upload, analyze, and improve your resume with ATS intelligence")
    tab_upload, tab_results = st.tabs(["Upload & Analyze", "Analysis Results"])

    with tab_upload:
        uploaded = st.file_uploader(
            "Drag & drop your resume PDF",
            type=["pdf"],
            accept_multiple_files=True,
            help="Max 10 MB per file",
        )
        if uploaded:
            progress = st.progress(0, text="Ready to upload…")
            if st.button("📤 Upload Resume", type="primary", use_container_width=True):
                files = [(f.name, f.read()) for f in uploaded]
                progress.progress(35, text="Uploading…")
                result = api_upload("/documents", files, st.session_state.session_id)
                progress.progress(100, text="Done" if result else "Failed")
                if result:
                    st.toast(f"Indexed {len(result)} file(s)", icon="📄")
                    st.rerun()

        docs = api_get("/documents", {"session_id": st.session_state.session_id}) or []
        resume_docs = [d for d in docs if d.get("filename", "").lower().endswith(".pdf")]
        if resume_docs:
            st.markdown("**Your resumes**")
            for doc in resume_docs:
                c1, c2 = st.columns([5, 1])
                with c1:
                    badge = "badge-success" if doc["status"] == "indexed" else "badge-warning"
                    st.markdown(
                        f"📄 **{doc['filename']}** <span class='badge {badge}'>{doc['status']}</span> · {doc['chunk_count']} chunks",
                        unsafe_allow_html=True,
                    )
                with c2:
                    if st.button("🗑️", key=f"rd-{doc['document_id']}"):
                        api_delete(f"/documents/{doc['document_id']}", {"session_id": st.session_state.session_id})
                        st.rerun()

        st.markdown("---")
        target_role = st.text_input("Target role (optional)", placeholder="Software Engineer, Data Analyst…")
        analyze_prompt = "Analyze my uploaded resume for ATS score, strengths, weaknesses, missing skills, formatting issues, and interview questions."
        if target_role:
            analyze_prompt += f" Target role: {target_role}."
        if st.button("🔍 Run ATS Analysis", type="primary", use_container_width=True):
            with st.spinner("Analyzing resume with AI…"):
                result = append_chat(analyze_prompt, "resume")
            if result:
                st.session_state.resume_analysis = result.get("response", "")
                st.rerun()

    with tab_results:
        text = st.session_state.resume_analysis
        if not text:
            empty_state("📄", "No analysis yet", "Upload a resume and run ATS analysis.")
            return

        ats = extract_ats_score(text)
        c1, c2, c3 = st.columns(3)
        with c1:
            render_stat("ATS Score", f"{ats or '—'}/100", "Compatibility", "#34d399" if ats and ats >= 70 else "#fbbf24")
        with c2:
            render_stat("Documents", str(len(api_get("/documents", {"session_id": st.session_state.session_id}) or [])), "Indexed PDFs")
        with c3:
            st.download_button("⬇ Download Report", text, file_name="resume-analysis.md", use_container_width=True)

        st.markdown(text)

        if ats is not None and HAS_PLOTLY:
            fig = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=ats,
                    domain={"x": [0, 1], "y": [0, 1]},
                    title={"text": "ATS Score"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": "#38bdf8"},
                        "steps": [
                            {"range": [0, 50], "color": "rgba(251,113,133,0.3)"},
                            {"range": [50, 75], "color": "rgba(251,191,36,0.3)"},
                            {"range": [75, 100], "color": "rgba(52,211,153,0.3)"},
                        ],
                    },
                )
            )
            fig.update_layout(height=260, margin=dict(t=40, b=0, l=20, r=20), paper_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0")
            st.plotly_chart(fig, use_container_width=True)

def page_company() -> None:
    section("🏢 Company Research", "Live web search for hiring intelligence — stored in your knowledge base")
    company = st.text_input("Company name", placeholder="Google, Microsoft, Amazon…")
    presets = ["Google", "Microsoft", "Amazon", "Adobe", "NVIDIA", "Flipkart", "TCS", "Infosys"]
    pc = st.columns(len(presets))
    for col, name in zip(pc, presets):
        with col:
            if st.button(name, key=f"co-{name}", use_container_width=True):
                company = name

    if st.button("🔍 Research Company", type="primary", disabled=not company, use_container_width=True):
        query = (
            f"Research {company}: company overview, hiring process, OA pattern, interview rounds, "
            f"salary range, preparation tips, recent interview experiences, and hiring trends."
        )
        with st.spinner(f"Researching {company}…"):
            result = append_chat(query, "company")
        if result:
            st.session_state.company_result = result.get("response", "")
            st.rerun()

    if st.session_state.company_result:
        st.markdown("---")
        st.markdown(st.session_state.company_result)
        st.caption("Research is indexed into ChromaDB for future RAG queries in this session.")


def page_rag() -> None:
    section("📚 RAG Knowledge Base", "Upload PDFs, notes, and interview experiences — ask with citations")
    tab_docs, tab_ask = st.tabs(["Documents", "Ask Questions"])

    with tab_docs:
        uploaded = st.file_uploader("Upload PDFs (resume, notes, books, experiences)", type=["pdf"], accept_multiple_files=True, key="rag_up")
        if uploaded and st.button("📤 Upload & Index", type="primary", key="rag_idx", use_container_width=True):
            with st.spinner("Indexing…"):
                api_upload("/documents", [(f.name, f.read()) for f in uploaded], st.session_state.session_id)
            st.rerun()

        status = api_get("/rag/status", {"session_id": st.session_state.session_id}) or {}
        c1, c2, c3 = st.columns(3)
        with c1:
            render_stat("Documents", str(status.get("document_count", 0)), "Total")
        with c2:
            render_stat("Indexed", str(status.get("indexed_document_count", 0)), "Ready")
        with c3:
            render_stat("Chunks", str(status.get("chunk_count", 0)), "Searchable")

        docs = api_get("/documents", {"session_id": st.session_state.session_id}) or []
        for doc in docs:
            c1, c2, c3 = st.columns([5, 1, 1])
            with c1:
                badge = "badge-success" if doc["status"] == "indexed" else "badge-warning"
                st.markdown(f"📄 **{doc['filename']}** <span class='badge {badge}'>{doc['status']}</span>", unsafe_allow_html=True)
            with c2:
                if st.button("🔄", key=f"ri-{doc['document_id']}", help="Re-index"):
                    api_reindex(doc["document_id"], st.session_state.session_id)
                    st.rerun()
            with c3:
                if st.button("🗑️", key=f"rdel-{doc['document_id']}"):
                    api_delete(f"/documents/{doc['document_id']}", {"session_id": st.session_state.session_id})
                    st.rerun()

    with tab_ask:
        question = st.text_input("Ask about your documents", placeholder="What skills are mentioned in my resume?")
        if st.button("🔍 Search & Answer", type="primary", disabled=not question, use_container_width=True):
            with st.spinner("Retrieving…"):
                result = append_chat(question, "rag")
            if result:
                st.markdown(result.get("response", ""))
                sources = result.get("sources") or []
                if sources:
                    st.markdown("**Sources:** " + ", ".join(sources))


def page_coding() -> None:
    section("💻 Coding Assistant", "Analyze code for bugs, complexity, optimization, and edge cases")
    c1, c2 = st.columns([1, 3])
    with c1:
        lang = st.selectbox("Language", ["Python", "Java", "C++", "JavaScript", "C", "SQL", "Go"])
        task = st.selectbox(
            "Analysis",
            ["Full Analysis", "Debug", "Complexity", "Optimize", "Similar Questions"],
        )
    with c2:
        code = st.text_area("Code editor", height=380, placeholder="def solution(nums):\n    ...")

    if st.button("🚀 Analyze Code", type="primary", use_container_width=True):
        if not code.strip():
            st.warning("Paste code first.")
        else:
            task_map = {
                "Full Analysis": "Perform full code review with bugs, time/space complexity, optimization, and edge cases",
                "Debug": "Debug and fix all bugs",
                "Complexity": "Analyze time and space complexity in detail",
                "Optimize": "Provide an optimized solution with comparison",
                "Similar Questions": "Analyze this code and generate 3 similar interview questions",
            }
            prompt = f"{task_map[task]} ({lang}):\n\n```{lang.lower()}\n{code}\n```"
            with st.spinner("Analyzing…"):
                result = append_chat(prompt, "coding")
            if result:
                st.session_state.coding_result = result.get("response", "")
                st.rerun()

    if st.session_state.coding_result:
        st.markdown("---")
        st.markdown(st.session_state.coding_result)


def page_interview() -> None:
    section("🎤 Mock Interview", "HR and technical interviews with scoring and feedback")
    c1, c2 = st.columns(2)
    with c1:
        mode = st.selectbox("Type", ["HR / Behavioral", "Technical"])
    with c2:
        topics = {
            "HR / Behavioral": ["General HR", "Leadership", "Conflict", "Career Goals"],
            "Technical": ["DSA", "Java", "Python", "DBMS", "OS", "CN", "SQL"],
        }
        topic = st.selectbox("Topic", topics[mode])

    if st.button("🎬 Start Interview", type="primary", use_container_width=True):
        kind = "HR" if "HR" in mode else "Technical"
        prompt = (
            f"Start a {kind} mock interview on {topic}. Ask ONE question at a time. "
            f"After each answer, score 1-10, give feedback, model answer, then next question."
        )
        st.session_state.interview_messages = []
        append_chat(prompt, "interview", target="interview_messages")
        st.rerun()

    for msg in st.session_state.interview_messages:
        avatar = "👤" if msg["role"] == "user" else "🎤"
        with st.chat_message(msg["role"], avatar=avatar):
            render_message_badges(msg)
            st.markdown(msg.get("content", ""))

    if st.session_state.interview_messages:
        answer = st.chat_input("Your answer…")
        if answer:
            append_chat(answer, "interview", target="interview_messages")
            st.rerun()
    else:
        empty_state("🎤", "No interview started", "Choose type and topic, then click Start Interview.")


def page_roadmap() -> None:
    section("🗺️ Roadmap Generator", "Personalized weekly plans with daily tasks and projects")
    c1, c2 = st.columns(2)
    with c1:
        level = st.selectbox("Skill level", ["Beginner", "Intermediate", "Advanced"])
        language = st.selectbox("Language", ["Python", "Java", "C++", "JavaScript"])
    with c2:
        weeks = st.slider("Weeks", 1, 24, 8)
        hours = st.slider("Hours/day", 1, 8, 3)
    target = st.text_input("Target company (optional)")

    if st.button("🗺️ Generate Roadmap", type="primary", use_container_width=True):
        prompt = (
            f"Create a {weeks}-week placement roadmap for a {level.lower()} developer using {language}, "
            f"{hours} hours/day. Include weekly breakdown, daily tasks, DSA topics, CS fundamentals, "
            f"projects, mock interviews, revision schedule, and rest days."
        )
        if target:
            prompt += f" Target company: {target}."
        with st.spinner("Generating…"):
            result = append_chat(prompt, "roadmap")
        if result:
            st.session_state.roadmap_result = result.get("response", "")
            st.rerun()

    if st.session_state.roadmap_result:
        st.markdown("---")
        st.markdown(st.session_state.roadmap_result)


def page_analytics() -> None:
    section("📈 Progress Analytics", "Track preparation metrics across agents")
    data = fetch_analytics()
    if not data:
        empty_state("📊", "No data", "Start using CareerPilot to populate analytics.")
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_stat("Interactions", str(data.get("total_interactions", 0)), "Total")
    with c2:
        render_stat("Streak", f"{data.get('learning_streak_days', 0)} days", "Learning")
    with c3:
        render_stat("Interview Avg", str(data.get("interview_score_avg", 0)), "/10")
    with c4:
        render_stat("Coding", str(data.get("coding_sessions", 0)), "Sessions")

    route_counts = data.get("route_counts") or {}
    if route_counts:
        st.markdown("**Agent Usage**")
        if HAS_PLOTLY:
            fig = go.Figure(go.Bar(x=list(route_counts.keys()), y=list(route_counts.values()), marker_color="#38bdf8"))
            fig.update_layout(title="Agent Usage", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", height=320)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.bar_chart(route_counts)

    radar = data.get("skill_radar") or {}
    if any(radar.values()):
        if HAS_PLOTLY:
            fig = go.Figure(go.Scatterpolar(
                r=list(radar.values()) + [list(radar.values())[0]],
                theta=list(radar.keys()) + [list(radar.keys())[0]],
                fill="toself", line_color="#a855f7", fillcolor="rgba(168,85,247,0.25)",
            ))
            fig.update_layout(title="Skill Radar", polar=dict(radialaxis=dict(visible=True)), paper_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", height=380)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown("**Skill Radar**")
            for skill, val in radar.items():
                st.write(f"- **{skill}**: {val}")

    scores = data.get("interview_scores") or []
    if scores:
        if HAS_PLOTLY:
            fig = go.Figure(go.Scatter(y=scores, mode="lines+markers", line=dict(color="#34d399")))
            fig.update_layout(title="Interview Scores", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", height=280)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown("**Interview Scores**")
            st.line_chart(scores)


def page_settings() -> None:
    section("⚙️ Settings", "Connection, providers, and subsystem status")
    with st.container(border=True):
        st.markdown("**Connection**")
        st.text_input("Backend URL", key="backend_url")
        st.text_input("Session ID", key="session_id")
        st.toggle("Streaming responses", key="use_streaming")

    status = api_get("/status", {"session_id": st.session_state.session_id}) or {}
    health = check_health(st.session_state.backend_url)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_stat("API", "OK" if health else "DOWN", "Backend")
    with c2:
        render_stat("LLM", status.get("llm_provider", "—").upper(), "Provider")
    with c3:
        render_stat("Memory", status.get("memory_status", "—"), f"{status.get('checkpoint_count', 0)} checkpoints")
    with c4:
        render_stat("RAG", status.get("rag_status", "—").upper(), "Vector index")

    st.info("LLM provider is configured via `.env` (`DEFAULT_LLM_PROVIDER`, `GEMINI_API_KEY` or `GROQ_API_KEY`). Restart backend after changes.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Clear chat history", use_container_width=True):
            st.session_state.messages = []
            st.session_state.interview_messages = []
            st.toast("Cleared", icon="🗑️")
            st.rerun()
    with c2:
        if st.button("New session", use_container_width=True):
            st.session_state.session_id = f"cp-{uuid.uuid4().hex[:8]}"
            st.session_state.messages = []
            st.session_state.interview_messages = []
            st.toast("New session", icon="🔄")
            st.rerun()


def page_chat() -> None:
    section("💬 AI Chat", "Planner routes your message to the best specialist agent")
    focus = st.selectbox("Route focus", ["all", "resume", "company", "coding", "interview", "roadmap", "rag"], format_func=str.title)

    for idx, msg in enumerate(st.session_state.messages):
        avatar = "👤" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            render_message_badges(msg)
            st.markdown(msg.get("content", ""))
            if msg["role"] == "assistant" and msg.get("sources"):
                st.caption("Sources: " + ", ".join(msg["sources"]))
            cols = st.columns([1, 1, 4])
            with cols[0]:
                st.button("📋 Copy", key=f"copy-{idx}", on_click=lambda c=msg.get("content", ""): st.session_state.update({"_clip": c}))
            with cols[1]:
                if st.button("🔁 Retry", key=f"retry-{idx}"):
                    prior = st.session_state.messages[idx - 1]["content"] if idx > 0 else ""
                    if prior:
                        append_chat(prior, focus)
                        st.rerun()

    if prompt := st.chat_input("Ask CareerPilot anything…"):
        append_chat(prompt, focus)
        st.rerun()


# ---------------------------------------------------------------------------
# Sidebar & router
# ---------------------------------------------------------------------------

if not st.session_state.get("logged_in"):
    render_auth_page()
    st.stop()

with st.sidebar:
    st.markdown('<div class="nav-brand"><span style="font-size:2.2rem">🚀</span><h2>CareerPilot AI</h2></div>', unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    user = st.session_state.get("user_info") or {}
    user_name = user.get("full_name") or user.get("username") or "Candidate"
    user_email = user.get("email") or ""
    st.markdown(
        f"""
        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.1); padding: 0.8rem; border-radius: 12px; margin-bottom: 1rem;">
            <div style="font-weight: 600; color: #f8fafc; font-size: 0.95rem;">👤 {user_name}</div>
            <div style="font-size: 0.8rem; color: #94a3b8;">{user_email}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.session_state.session_id = f"cp-{uuid.uuid4().hex[:8]}"
        st.session_state.messages = []
        st.session_state.interview_messages = []
        st.rerun()

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    health = check_health(st.session_state.backend_url)
    dot = "status-online" if health else "status-offline"
    label = "Backend Online" if health else "Backend Offline"
    st.markdown(f'<span class="status-dot {dot}"></span> **{label}**', unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    for name, meta in PAGES.items():
        if st.button(f"{meta['icon']}  {name}", key=f"nav-{meta['key']}", use_container_width=True,
                     type="primary" if st.session_state.page == name else "secondary"):
            st.session_state.page = name
            st.rerun()

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    if st.button("💬 Open Chat", use_container_width=True):
        st.session_state.page = "Chat"
        st.rerun()
    st.caption(f"User Session `{st.session_state.session_id}`")

PAGE_HANDLERS = {
    "Dashboard": page_dashboard,
    "Resume Analyzer": page_resume,
    "Company Research": page_company,
    "RAG Knowledge Base": page_rag,
    "Coding Assistant": page_coding,
    "Mock Interview": page_interview,
    "Roadmap Generator": page_roadmap,
    "Progress Analytics": page_analytics,
    "Settings": page_settings,
    "Chat": page_chat,
}

current = st.session_state.get("page", "Dashboard")
handler = PAGE_HANDLERS.get(current, page_dashboard)
handler()
