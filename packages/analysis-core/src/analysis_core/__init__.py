"""
kouchou-ai-analysis-core

広聴AIの分析パイプラインコアライブラリ。
コメントデータからクラスタリングと要約を行う。

This package provides two execution modes:
1. Default mode: Workflow-backed execution used by the CLI and current API path
2. Legacy mode: Direct step function execution with status tracking

Example (Default mode):
    from analysis_core import PipelineOrchestrator
    orchestrator = PipelineOrchestrator.from_config("config.json")
    result = orchestrator.run_default()

Example (Legacy mode):
    from analysis_core import PipelineOrchestrator
    orchestrator = PipelineOrchestrator.from_config("config.json")
    result = orchestrator.run()
"""

__version__ = "0.1.2"

from analysis_core.config import PipelineConfig
from analysis_core.orchestrator import PipelineOrchestrator, PipelineResult, StepResult

__all__ = [
    "__version__",
    "PipelineOrchestrator",
    "PipelineConfig",
    "PipelineResult",
    "StepResult",
]
