"""
Field Mapper Service
====================
Reusable field mapping heuristics shared between the server Playwright agent
and the browser extension. Maps detected DOM form fields to candidate profile values.
"""

from typing import List, Optional

from app.core.logging import get_logger
from app.models.schemas import (
    DetectedDOMField,
    FieldMappingDecision,
    FormFieldMetadata,
    ResumeProfile,
)

logger = get_logger("field_mapper")


def map_fields_heuristic(
    fields: List[FormFieldMetadata],
    profile: ResumeProfile,
    correlation_id: str = "sys",
) -> List[FieldMappingDecision]:
    """
    Decides which profile value fills each DOM field based on labels, names, IDs, and placeholders.
    Shared heuristic engine for both Playwright automation and browser extension copilot.
    """
    log = get_logger("field_mapper", correlation_id=correlation_id)
    decisions: List[FieldMappingDecision] = []

    # Split candidate name into first and last if available
    parts = (profile.full_name or "Applicant").split()
    first_name = parts[0] if parts else ""
    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    for f in fields:
        combined_context = (
            f"{f.label_text} {f.name} {f.element_id} {f.placeholder} {f.autocomplete} {f.aria_label}".lower()
        )

        # 1. First Name
        if any(term in combined_context for term in ["first_name", "firstname", "first name", "given-name"]):
            decisions.append(
                FieldMappingDecision(
                    field_name="First Name",
                    field_type=f.input_type,
                    selector=f.selector,
                    value_filled=first_name,
                    confidence=0.98,
                    source_field="profile.full_name",
                    rationale="Target field labeled for applicant given name",
                )
            )
        # 2. Last Name
        elif any(term in combined_context for term in ["last_name", "lastname", "last name", "family-name", "surname"]):
            decisions.append(
                FieldMappingDecision(
                    field_name="Last Name",
                    field_type=f.input_type,
                    selector=f.selector,
                    value_filled=last_name,
                    confidence=0.98,
                    source_field="profile.full_name",
                    rationale="Target field labeled for applicant surname",
                )
            )
        # 3. Full Name
        elif any(term in combined_context for term in ["full name", "fullname", "name", "your name"]) and f.input_type != "email":
            decisions.append(
                FieldMappingDecision(
                    field_name="Full Name",
                    field_type=f.input_type,
                    selector=f.selector,
                    value_filled=profile.full_name or "Applicant",
                    confidence=0.95,
                    source_field="profile.full_name",
                    rationale="Target field labeled for applicant legal full name",
                )
            )
        # 4. Email
        elif f.input_type == "email" or any(term in combined_context for term in ["email", "e-mail"]):
            decisions.append(
                FieldMappingDecision(
                    field_name="Email Address",
                    field_type=f.input_type,
                    selector=f.selector,
                    value_filled=profile.email or "candidate@example.com",
                    confidence=0.99,
                    source_field="profile.email",
                    rationale="Standard email pattern and attribute match",
                )
            )
        # 5. Phone
        elif f.input_type == "tel" or any(term in combined_context for term in ["phone", "mobile", "telephone", "contact number"]):
            decisions.append(
                FieldMappingDecision(
                    field_name="Phone Number",
                    field_type=f.input_type,
                    selector=f.selector,
                    value_filled=profile.phone or "+1 (555) 010-9999",
                    confidence=0.95,
                    source_field="profile.phone",
                    rationale="Telephone type or label matched parsed candidate phone",
                )
            )
        # 6. LinkedIn URL
        elif any(term in combined_context for term in ["linkedin", "profile link", "social profile"]):
            linkedin_val = profile.linkedin or "https://linkedin.com/in/applicant-profile"
            decisions.append(
                FieldMappingDecision(
                    field_name="LinkedIn Profile",
                    field_type=f.input_type,
                    selector=f.selector,
                    value_filled=linkedin_val,
                    confidence=0.88,
                    source_field="profile.linkedin",
                    rationale="Candidate professional profile link",
                )
            )
        # 7. Experience
        elif any(term in combined_context for term in ["experience", "years of exp", "total experience"]):
            decisions.append(
                FieldMappingDecision(
                    field_name="Years of Experience",
                    field_type=f.input_type,
                    selector=f.selector,
                    value_filled=str(profile.years_experience or 3.0),
                    confidence=0.90,
                    source_field="profile.years_experience",
                    rationale="Extracted years of experience estimation",
                )
            )
        # 8. City / Location
        elif any(term in combined_context for term in ["city", "location", "address", "residence"]):
            decisions.append(
                FieldMappingDecision(
                    field_name="Location",
                    field_type=f.input_type,
                    selector=f.selector,
                    value_filled=profile.location or "Remote",
                    confidence=0.91,
                    source_field="profile.location",
                    rationale="Candidate location or city preference",
                )
            )
        # 9. Cover Letter / Notes
        elif f.tag == "textarea" or any(term in combined_context for term in ["cover letter", "message", "note", "comments", "pitch"]):
            skills_str = ", ".join(profile.skills[:4]) if profile.skills else "software engineering"
            cover_text = (
                f"Hi, I am enthusiastic about applying for this opportunity. "
                f"With my background in {skills_str}, I look forward to contributing effectively to your team."
            )
            decisions.append(
                FieldMappingDecision(
                    field_name="Cover Letter",
                    field_type="textarea",
                    selector=f.selector,
                    value_filled=cover_text,
                    confidence=0.85,
                    source_field="profile.skills",
                    rationale="Generated tailored pitch from matched skills",
                )
            )

    log.info("mapping_complete", decisions_count=len(decisions))
    return decisions


def map_detected_dom_fields(
    detected_fields: List[DetectedDOMField],
    profile: ResumeProfile,
    job_description: Optional[str] = None,
    correlation_id: str = "sys",
) -> List[FieldMappingDecision]:
    """Convert browser extension detected fields into standard FormFieldMetadata and map."""
    converted: List[FormFieldMetadata] = []
    for df in detected_fields:
        tag = "textarea" if df.field_type == "textarea" else "input"
        converted.append(
            FormFieldMetadata(
                tag=tag,
                element_id=df.name if df.name.startswith("#") else "",
                name=df.name,
                input_type=df.field_type or "text",
                placeholder=df.placeholder or "",
                label_text=df.label or df.name,
                aria_label=df.label or "",
                autocomplete="",
                selector=df.selector,
                required=df.required,
            )
        )
    return map_fields_heuristic(converted, profile, correlation_id=correlation_id)
