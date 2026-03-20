# Data Model

## Reused standard HRMS records

- `Job Requisition`: manager demand intake and approval anchor
- `Job Opening`: publishable role and salary range
- `Job Applicant`: candidate master record during recruiting
- `Interview`: round scheduling and follow-up
- `Job Offer`: offer approval and onboarding handoff
- `Employee`: active employee record after hire

## AIHR custom additions

### Custom fields on Job Requisition

- hiring priority
- work mode
- work city
- work schedule
- salary band
- must-have and nice-to-have skills
- generated agency brief

### Custom fields on Job Applicant

- resume plain text cache
- AIHR status
- machine match score
- candidate city
- years of experience
- next action and follow-up timestamps

### Custom fields on Interview

- interview mode
- follow-up owner
- feedback due time
- interviewer pack

### Custom fields on Job Offer

- onboarding owner
- payroll handoff state
- compensation notes

### New DocType: AI Screening

Purpose:

- store the machine-generated candidate brief
- preserve the score explanation
- keep strengths, risks, and suggested interview questions auditable

Core fields:

- `job_applicant`
- `job_opening`
- `status`
- `overall_score`
- `matched_skills`
- `missing_skills`
- `ai_summary`
- `strengths`
- `risks`
- `suggested_questions`
- `parsed_resume_json`
- `screening_payload_json`

## Lifecycle thread

`Job Requisition -> Job Opening -> Job Applicant -> AI Screening -> Interview -> Job Offer -> Employee`

That thread is the minimum viable lifecycle for the current company pain point.

