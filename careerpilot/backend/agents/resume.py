from __future__ import annotations

from careerpilot.backend.agents.common import AgentState, run_specialist
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


def handle_resume(state: AgentState) -> AgentState:
    """Provide comprehensive resume and ATS feedback grounded in uploaded PDFs when available."""

    query = state.get("user_query", "")
    session_id = state.get("session_id", "default-session")
    enriched_state: AgentState = dict(state)

    service = get_rag_service()
    indexed = [record for record in service.registry.list(session_id) if record.status == "indexed"]
    if indexed:
        try:
            matches = service.retrieve(session_id, query or "resume skills experience projects education")
            if matches:
                context = "\n\n".join(
                    f"[{item['metadata']['filename']} p.{item['metadata']['page']}]\n{item['content']}"
                    for item in matches
                )
                enriched_state["user_query"] = f"{query}\n\nUploaded resume content:\n{context}"
        except Exception:
            pass

    result = run_specialist(enriched_state, _RESUME_PROMPT)
    metadata = dict(result.get("metadata") or {})
    metadata["resume_documents"] = len(indexed)
    result["metadata"] = metadata
    return result
