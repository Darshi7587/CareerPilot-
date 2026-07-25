from pathlib import Path
from typing import Any

from careerpilot.backend.agents.common import AgentState, run_specialist
from careerpilot.backend.llm import LLMConfigurationError, generate_response
from careerpilot.backend.rag.loader import load_pdf
from careerpilot.backend.rag.service import get_rag_service

_RESUME_PROMPT = """You are CareerPilot's expert resume analyst and ATS (Applicant Tracking System) specialist.

When the user shares their resume text or asks about resume improvements, provide a thorough, structured analysis.

## Your Analysis Must Include:

### 1. ATS Compatibility Score (0-100)
- Evaluate keyword optimization, formatting compatibility, and section structure
- Explain what affects the score

### 2. Strengths
- Identify what the resume does well
- Note effective use of action verbs, quantified achievements, relevant skills

### 3. Weaknesses & Gaps
- Point out missing sections (summary, skills, projects, certifications)
- Identify vague descriptions lacking metrics
- Note any red flags (employment gaps, inconsistencies)

### 4. Missing Skills
- Based on the target role/industry, identify important skills not mentioned
- Suggest technical and soft skills to add

### 5. Formatting Issues
- Check for ATS-unfriendly elements (tables, images, headers/footers, fancy fonts)
- Recommend structural improvements

### 6. Actionable Improvements
- Provide 5-7 specific, implementable suggestions
- Include example rewrites for weak bullet points

### 7. Potential Interview Questions
- Generate 5 questions an interviewer would likely ask based on this resume
- Include both technical and behavioral questions

### 8. Skill Graph Summary
- List top skills found with proficiency estimates (Beginner/Intermediate/Advanced)
- Note skill clusters (Languages, Frameworks, Tools, Soft Skills)

Be specific and reference actual content from the resume. Do not invent facts not present in the resume.
Format your response in clean markdown with headers and bullet points."""


def _generate_resume_response(system_prompt: str, user_query: str, history: list[dict[str, Any]]) -> str:
    """Helper hook for generating resume specialist responses."""
    try:
        return generate_response(system_prompt=system_prompt, user_query=user_query, history=history)
    except LLMConfigurationError as exc:
        return f"The selected LLM provider is not configured: {exc}"
    except Exception:
        return "I could not complete that request because the AI provider is temporarily unavailable. Please try again."


def handle_resume(state: AgentState) -> AgentState:
    """Provide comprehensive resume and ATS feedback grounded in uploaded PDFs when available."""

    query = state.get("user_query", "")
    session_id = state.get("session_id", "default-session")
    history = state.get("history", [])

    service = get_rag_service()
    records = service.registry.list(session_id)
    if not records and hasattr(service.registry, "list_all"):
        records = service.registry.list_all()

    resume_blocks: list[str] = []
    for record in records:
        storage_path = getattr(record, "storage_path", "")
        filename = getattr(record, "filename", "uploaded_resume.pdf")
        path = Path(storage_path) if storage_path else None
        if path and path.is_file():
            try:
                if path.suffix.lower() == ".pdf":
                    pages = load_pdf(path)
                    text = "\n".join(str(p.get("page_content", "")).strip() for p in pages if p.get("page_content"))
                    if text.strip():
                        resume_blocks.append(f"=== UPLOADED RESUME FILE: {filename} ===\n{text}")
                elif path.suffix.lower() in (".txt", ".md"):
                    text = path.read_text(encoding="utf-8").strip()
                    if text:
                        resume_blocks.append(f"=== UPLOADED RESUME FILE: {filename} ===\n{text}")
            except Exception:
                pass

    if not resume_blocks and records:
        try:
            matches = service.retrieve(session_id, query or "resume skills experience projects education")
            if matches:
                context = "\n\n".join(
                    f"[{item['metadata']['filename']} p.{item['metadata']['page']}]\n{item['content']}"
                    for item in matches
                )
                resume_blocks.append(context)
        except Exception:
            pass

    prompt = _RESUME_PROMPT
    if resume_blocks:
        full_resume_text = "\n\n".join(resume_blocks)
        prompt = (
            f"{_RESUME_PROMPT}\n\n"
            f"## FULL UPLOADED RESUME CONTENT TO ANALYZE IN DETAIL:\n"
            f"{full_resume_text}\n\n"
            f"INSTRUCTION: Perform a thorough, complete, and specific ATS analysis on the above uploaded resume text. "
            f"Reference the candidate's exact name, contact info, skills, projects, and education directly from the text."
        )

    response = _generate_resume_response(prompt, query, history)
    metadata = dict(state.get("metadata") or {})
    metadata["resume_documents"] = len(resume_blocks)
    return {"response": response, "metadata": metadata}
