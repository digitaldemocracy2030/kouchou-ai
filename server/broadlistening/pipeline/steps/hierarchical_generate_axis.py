"""Generate axis labels for UMAP-reduced data."""

import json
import logging
from pathlib import Path
from typing import Any, TypedDict

import pandas as pd
from pydantic import BaseModel, Field

from services.llm import request_to_chat_openai

logger = logging.getLogger(__name__)


class Argument(TypedDict):
    arg_id: str
    argument: str
    comment_id: str
    x: float
    y: float
    p: float
    cluster_ids: list[str]


class AxisLabelResponse(BaseModel):
    axis_name: str = Field(..., description="どのような特性の軸か")
    min_label: str = Field(..., description="小さな値にはどのような傾向があるか")
    max_label: str = Field(..., description="大きな値にはどのような傾向があるか")


def generate_axis_labels(
    arguments: list[Argument], 
    is_x_axis: bool = True, 
    model: str = "gpt-4o-mini", 
    provider: str = "openai",
    local_llm_address: str | None = None
) -> dict[str, str]:
    """
    Generate axis labels for UMAP-reduced data.

    Args:
        arguments: List of arguments with x and y coordinates
        is_x_axis: Whether to generate labels for the X axis (True) or Y axis (False)
        model: LLM model to use
        provider: LLM provider (openai, azure, local)
        local_llm_address: Address for local LLM if provider is "local"

    Returns:
        Dictionary with axis_name, min_label, and max_label
    """
    default_response = {"axis_name": "軸" + ("X" if is_x_axis else "Y"), "min_label": "最小", "max_label": "最大"}

    if not arguments or len(arguments) < 10:
        logger.warning(f"Not enough arguments to generate {'X' if is_x_axis else 'Y'} axis labels")
        return default_response

    try:
        axis1 = "x" if is_x_axis else "y"
        axis2 = "y" if is_x_axis else "x"

        axis_min = min(item[axis1] for item in arguments)
        axis_max = max(item[axis1] for item in arguments)
        axis_range = axis_max - axis_min

        if axis_range == 0:
            logger.warning(f"Zero range for {'X' if is_x_axis else 'Y'} axis")
            return default_response

        axis_step = axis_range / 10
        labels = []

        axis2_ave = sum(item[axis2] for item in arguments) / len(arguments)

        for i in range(11):
            range_min = axis_min + i * axis_step
            range_max = axis_min + (i + 1) * axis_step if i < 10 else axis_max + 0.0001

            items = [item for item in arguments if range_min <= item[axis1] < range_max]

            if items:
                items = sorted(items, key=lambda item: abs(item[axis2] - axis2_ave))
                labels.append(items[0]["argument"])

        if not labels:
            logger.warning(f"No labels generated for {'X' if is_x_axis else 'Y'} axis")
            return default_response

        system_prompt = """
あなたは、トップコンサルタントである。 1から10番のある特性に応じたソートが行われた文章が与えられます。
あなたはどのような軸でソートされたデータなのかの全体像を考えなさい。
そして、値が小さい方はどのような傾向があるのか、また、値が大きい方はどのような傾向があるのかを考えなさい。

以下のような形式で出力せよ。
{
    "axis_name": "どのような特性の軸か",
    "min_label": "小さな値にはどのような傾向があるか",
    "max_label": "大きな値にはどのような傾向があるか"
}
"""

        user_prompt = ""
        for i, label in enumerate(labels):
            user_prompt += f"#{i} : {label}\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        raw_response = request_to_chat_openai(
            messages=messages,
            model=model,
            provider=provider,
            local_llm_address=local_llm_address,
            json_schema=AxisLabelResponse,
        )

        response = json.loads(raw_response)
        return response
    except Exception as e:
        logger.error(f"Error generating {'X' if is_x_axis else 'Y'} axis labels: {str(e)}")
        return default_response


def hierarchical_generate_axis(config: dict[str, Any]) -> None:
    """
    Generate axis labels for UMAP-reduced data and save to a JSON file.

    Args:
        config: Configuration dictionary
    """
    try:
        arguments_path = f"outputs/{config['output_dir']}/args.csv"
        if not Path(arguments_path).exists():
            logger.error(f"Arguments file not found: {arguments_path}")
            return

        arguments_df = pd.read_csv(arguments_path)

        arguments = []
        for _, row in arguments_df.iterrows():
            argument = {
                "arg_id": row["arg-id"],
                "argument": row["argument"],
                "x": row["x"],
                "y": row["y"],
                "p": 0,  # Default value
                "cluster_ids": [],  # Will be populated later
                "comment_id": row.get("comment-id", ""),
            }
            arguments.append(argument)

        model = config.get("hierarchical_generate_axis", {}).get("model", "gpt-4o-mini")
        provider = config.get("provider", "openai")
        local_llm_address = config.get("local_llm_address")
        
        x_axis = generate_axis_labels(
            arguments, 
            is_x_axis=True,
            model=model,
            provider=provider,
            local_llm_address=local_llm_address
        )
        y_axis = generate_axis_labels(
            arguments, 
            is_x_axis=False,
            model=model,
            provider=provider,
            local_llm_address=local_llm_address
        )

        output_path = f"outputs/{config['output_dir']}/axis_labels.json"
        with open(output_path, mode="w") as f:
            json.dump({"x_axis": x_axis, "y_axis": y_axis}, f, indent=2, ensure_ascii=False)

        logger.info(f"Axis labels generated and saved to {output_path}")
    except Exception as e:
        logger.error(f"Error in hierarchical_generate_axis: {str(e)}")
