"""Configuration models and settings for the Customer Support Agent."""

import os
from pathlib import Path

from pydantic import BaseModel, Field


def _load_env_file() -> None:
    """Load environment variables from project-level .env if present."""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k:
                    os.environ[k] = v


_load_env_file()


class AgentConfig(BaseModel):
    """Configuration parameters for Bedrock AgentCore Assistant."""

    model_id: str = Field(
        default_factory=lambda: os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0"),
        description="Bedrock Foundation Model identifier (e.g. amazon.nova-pro-v1:0, anthropic.claude-3-5-sonnet-20241022-v2:0)"
    )
    region_name: str = Field(
        default_factory=lambda: os.environ.get("AWS_REGION", "us-east-1"),
        description="AWS Region for Bedrock runtime"
    )
    temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Sampling temperature for deterministic grounding"
    )
    top_p: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Top-p nucleus sampling"
    )
    max_tokens: int = Field(
        default=1024,
        gt=0,
        le=4096,
        description="Maximum generated token limit per response"
    )
    max_turns: int = Field(
        default=30,
        description="Maximum turns retained in active conversation memory"
    )
    lambda_tool_arn: str | None = Field(
        default_factory=lambda: os.environ.get("CREATE_BUG_REPORT_LAMBDA_ARN"),
        description="Optional ARN for remote Lambda execution"
    )
    guardrail_id: str | None = Field(
        default_factory=lambda: os.environ.get("BEDROCK_GUARDRAIL_ID"),
        description="Optional Bedrock Guardrail Identifier"
    )
    guardrail_version: str = Field(
        default_factory=lambda: os.environ.get("BEDROCK_GUARDRAIL_VERSION", "DRAFT"),
        description="Bedrock Guardrail Version"
    )
    knowledge_base_id: str | None = Field(
        default_factory=lambda: os.environ.get("BEDROCK_KNOWLEDGE_BASE_ID"),
        description="Optional Bedrock Knowledge Base Identifier for RAG"
    )
    rag_top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of knowledge chunks to retrieve per turn"
    )
    mock_mode: bool = Field(
        default_factory=lambda: os.environ.get("AWS_MOCK_MODE", "").lower() in ("true", "1", "yes"),
        description="Whether to run in local offline mock mode without connecting to AWS"
    )
