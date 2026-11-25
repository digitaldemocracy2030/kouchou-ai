"""
kouchou-ai-analysis-core

広聴AIの分析パイプラインコアライブラリ。
コメントデータからクラスタリングと要約を行う。

Example:
    from analysis_core import PipelineOrchestrator
    orchestrator = PipelineOrchestrator.from_config("config.json")
    result = orchestrator.run_default()
"""

__version__ = "0.3.0"

from analysis_core.config import PipelineConfig
from analysis_core.orchestrator import PipelineOrchestrator, PipelineResult, StepResult

__all__ = [
    "__version__",
    "PipelineOrchestrator",
    "PipelineConfig",
    "PipelineResult",
    "StepResult",
]
