#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aihr.services.resume_parser import extract_text_from_file, parse_resume_text
from aihr.services.screening import screen_candidate


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview AIHR heuristic resume screening.")
    parser.add_argument("--requirements-file", required=True, help="Path to a text file with job requirements.")
    parser.add_argument("--resume-file", required=True, help="Path to a resume text or PDF file.")
    parser.add_argument("--preferred-skills", default="", help="Comma-separated preferred skills.")
    parser.add_argument("--preferred-city", default="", help="Preferred city for this role.")
    args = parser.parse_args()

    requirements = Path(args.requirements_file).read_text(encoding="utf-8", errors="ignore")
    resume_text = extract_text_from_file(args.resume_file)
    parsed_resume = parse_resume_text(resume_text)
    result = screen_candidate(
        parsed_resume=parsed_resume,
        job_requirements=requirements,
        preferred_skills=args.preferred_skills,
        preferred_city=args.preferred_city,
    )
    print(json.dumps({"parsed_resume": parsed_resume, "screening": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
