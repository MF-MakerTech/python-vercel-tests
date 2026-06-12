"""FastAPI app for Vercel with AI Gateway."""

import os

from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field

AI_GATEWAY_BASE_URL = "https://ai-gateway.vercel.sh/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"

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
    try:
        client = _get_openai_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": body.question}],
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

    return QuestionResponse(answer=content, model=model)
