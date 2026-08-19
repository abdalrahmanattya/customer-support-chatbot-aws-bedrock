"""Unit tests for CloudFormation templates."""

from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
INFRA_DIR = ROOT_DIR / "infrastructure"


def test_tool_stack_template():
    """Verify tool-stack.yaml contains required resources and outputs."""
    template_path = INFRA_DIR / "tool-stack.yaml"
    assert template_path.exists()

    content = template_path.read_text(encoding="utf-8")
    assert "AWSTemplateFormatVersion" in content
    assert "BugReportsTable" in content
    assert "AWS::DynamoDB::Table" in content
    assert "CreateBugReportFunction" in content
    assert "AWS::Lambda::Function" in content
    assert "LambdaExecutionRole" in content
    assert "BedrockInvokePermission" in content


def test_eval_stack_template():
    """Verify eval-stack.yaml contains required resources and outputs."""
    template_path = INFRA_DIR / "eval-stack.yaml"
    assert template_path.exists()

    content = template_path.read_text(encoding="utf-8")
    assert "AWSTemplateFormatVersion" in content
    assert "EvalDatasetBucket" in content
    assert "AWS::S3::Bucket" in content
    assert "BedrockEvalRole" in content
    assert "AWS::IAM::Role" in content
