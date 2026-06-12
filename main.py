"""FastAPI app for Vercel with AI Gateway."""

import os
import logging
from datetime import UTC, datetime

from fastapi import FastAPI, Header, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field

AI_GATEWAY_BASE_URL = "https://ai-gateway.vercel.sh/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"
DEFAULT_CRON_QUESTION = "Give me a one-sentence tip about FastAPI."

app = FastAPI(
    title="Python Vercel Test",
    description="Ask questions via Vercel AI Gateway",
    version="0.1.0",
)


def _get_openai_client() -> OpenAI:
    """Create an OpenAI client configured for Vercel AI Gateway.

    Returns:
        Configured OpenAI client.

    Raises:
        RuntimeError: If no API key or OIDC token is available.
    """
    api_key = os.getenv("AI_GATEWAY_API_KEY") or os.getenv(
        "VERCEL_OIDC_TOKEN",
    )
    if not api_key:
        raise RuntimeError(
            "Set AI_GATEWAY_API_KEY or deploy on Vercel for OIDC auth",
        )
    return OpenAI(
        api_key=api_key,
        base_url=AI_GATEWAY_BASE_URL,
    )


def _verify_cron_auth(authorization: str | None) -> None:
    """Verify that a cron request is authorized.

    Args:
        authorization: Value of the Authorization header.

    Raises:
        HTTPException: If CRON_SECRET is set and the header does not match.
    """
    cron_secret = os.getenv("CRON_SECRET")
    if not cron_secret:
        return
    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def _ask_ai(question: str, model: str | None = None) -> tuple[str, str]:
    """Send a question to the AI via Vercel AI Gateway.

    Args:
        question: The question to ask.
        model: Optional model override.

    Returns:
        Tuple of answer text and model used.

    Raises:
        HTTPException: On auth or upstream API errors.
    """
    resolved_model = model or os.getenv("AI_MODEL", DEFAULT_MODEL)
    try:
        client = _get_openai_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        response = client.chat.completions.create(
            model=resolved_model,
            messages=[{"role": "user", "content": question}],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI Gateway error: {exc}",
        ) from exc

    content = response.choices[0].message.content
    if not content:
        raise HTTPException(
            status_code=502,
            detail="AI returned an empty response",
        )

    return content, resolved_model


class QuestionRequest(BaseModel):
    """Request body for asking a question."""

    question: str = Field(..., min_length=1, description="Your question")
    model: str | None = Field(
        default=None,
        description="AI Gateway model id (e.g. openai/gpt-4o-mini)",
    )


class QuestionResponse(BaseModel):
    """Response from the AI."""

    answer: str
    model: str


class CronResponse(BaseModel):
    """Response from the scheduled cron job."""

    status: str
    ran_at: str
    message: str
    schedule: str | None = None


@app.get("/")
def root() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "message": "Send POST /ask with a question"}


@app.post("/ask", response_model=QuestionResponse)
def ask(body: QuestionRequest) -> QuestionResponse:
    """Send a question to the AI via Vercel AI Gateway.

    Args:
        body: Question and optional model override.

    Returns:
        The AI's answer.

    Raises:
        HTTPException: On auth or upstream API errors.
    """
    model = body.model or os.getenv("AI_MODEL", DEFAULT_MODEL)
    answer, used_model = _ask_ai(body.question, model)
    return QuestionResponse(answer=answer, model=used_model)


@app.get("/cron", response_model=CronResponse)
def cron_job(
    authorization: str | None = Header(default=None),
    x_vercel_cron_schedule: str | None = Header(default=None),
) -> CronResponse:
    """Run the scheduled cron task via Vercel AI Gateway.

    Vercel invokes this route on the schedule defined in vercel.json.
    Set CRON_SECRET in production so only Vercel can trigger it.

    Args:
        authorization: Bearer token from Vercel when CRON_SECRET is set.
        x_vercel_cron_schedule: Cron expression that triggered this run.

    Returns:
        Cron job result including the AI answer.

    Raises:
        HTTPException: If the request is unauthorized.
    """
    logging.info("Cron job started")
    _verify_cron_auth(authorization)
    logging.info("Cron job done")
    
    return CronResponse(
        status="ok",
        ran_at=datetime.now(tz=UTC).isoformat(),
        message="Hello, world!",
        schedule=x_vercel_cron_schedule,
    )

def main() -> None:
    """Run the FastAPI app locally with uvicorn."""
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
