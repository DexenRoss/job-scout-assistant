from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from core.config import get_settings
from core.logger import get_logger, setup_logging
from storage.repositories import JobRepository
from tailoring.export_outputs import DEFAULT_OUTPUT_DIR, export_tailoring_outputs
from tailoring.generate_summary import generate_fit_summary_markdown
from tailoring.parse_master_resume import DEFAULT_MASTER_RESUME_PATH, load_master_resume
from tailoring.tailor_resume import tailor_resume_for_job


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Generate a tailored resume for a stored job posting.",
    )
    parser.add_argument(
        "--resume",
        default=str(DEFAULT_MASTER_RESUME_PATH),
        help="Path to the structured master resume JSON file.",
    )
    parser.add_argument(
        "--job-id",
        type=int,
        default=None,
        help="Optional SQLite job ID. If omitted, the top scored recent job is used.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where tailored resume outputs will be written.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    settings = get_settings()
    setup_logging(settings.log_level)
    logger = get_logger(__name__)

    try:
        master_resume = load_master_resume(args.resume)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    repository = JobRepository(settings.database_path)
    job = (
        repository.get_job_by_id(args.job_id)
        if args.job_id is not None
        else repository.get_top_job_for_tailoring()
    )
    if job is None:
        selector = f"id={args.job_id}" if args.job_id is not None else "top scored recent job"
        raise SystemExit(
            f"No stored job posting found for selector: {selector}. Run `python -m app` first."
        )

    tailored_resume = tailor_resume_for_job(master_resume, job)
    summary_markdown = generate_fit_summary_markdown(job, tailored_resume)
    metadata = dict(tailored_resume.metadata)
    metadata["resume_source_path"] = str(Path(args.resume))

    exported = export_tailoring_outputs(
        job=job,
        tailored_resume_markdown=tailored_resume.resume_markdown,
        summary_markdown=summary_markdown,
        metadata=metadata,
        output_dir=args.output_dir,
    )

    logger.info(
        "Generated tailored resume outputs for job_id=%s company=%s title=%s",
        job.id,
        job.company,
        job.title,
    )
    print(f"Tailoring generated for job_id={job.id} | {job.company} | {job.title}")
    print(f"Resume markdown: {exported.resume_path}")
    print(f"Summary markdown: {exported.summary_path}")
    print(f"Metadata JSON: {exported.metadata_path}")


if __name__ == "__main__":
    main()
