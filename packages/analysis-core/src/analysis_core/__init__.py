"""
kouchou-ai-analysis-core

広聴AIの分析パイプラインコアライブラリ。
コメントデータからクラスタリングと要約を行う。
"""

__version__ = "0.1.0"

from analysis_core.orchestrator import PipelineOrchestrator
from analysis_core.config import PipelineConfig

__all__ = [
    "__version__",
    "PipelineOrchestrator",
    "PipelineConfig",
]
