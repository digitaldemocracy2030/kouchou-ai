"""
kouchou-ai-analysis-core

広聴AIの分析パイプラインコアライブラリ。
コメントデータからクラスタリングと要約を行う。

This package provides two execution modes:
1. Legacy mode: Direct step function execution with status tracking
2. Workflow mode: Plugin-based workflow engine with configurable steps

Example (Legacy mode):
    from analysis_core import PipelineOrchestrator
    orchestrator = PipelineOrchestrator.from_config("config.json")
    result = orchestrator.run()

Example (Workflow mode):
    from analysis_core import PipelineOrchestrator
    orchestrator = PipelineOrchestrator.from_dict(config)
    result = orchestrator.run_workflow()
"""

__version__ = "0.1.0"

from analysis_core.config import PipelineConfig
from analysis_core.orchestrator import PipelineOrchestrator, PipelineResult, StepResult

__all__ = [
    "__version__",
    "PipelineOrchestrator",
    "PipelineConfig",
    "PipelineResult",
    "StepResult",
]
