import csv

from src.config import settings
from src.core.exceptions import ClusterCSVParseError, ClusterFileNotFound, ClusterNotFound
from src.schemas.cluster import ClusterResponse, ClusterUpdate
from src.utils.logger import setup_logger

slogger = setup_logger()


class ClusterRepository:
    """クラスタの中間ファイル（csvファイル）を読み書きするrepository"""

    def __init__(self, slug: str):
        self.slug = slug
        self.labels_path = settings.REPORT_DIR / slug / "hierarchical_merge_labels.csv"

    def read_from_csv(self) -> list[ClusterResponse]:
        """中間ファイル（CSVファイル）からクラスタのラベル・説明を読み込む"""

        clusters = []
        # ファイルが存在しない場合は、ClusterFileNotFound例外を発生させる
        if not self.labels_path.exists():
            raise ClusterFileNotFound(f"File not found: {self.labels_path}")

        try:
            with open(self.labels_path, encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        cluster = ClusterResponse(
                            level=int(row["level"]),
                            id=row["id"],
                            label=row["label"],
                            description=row["description"],
                            value=int(row["value"]),
                            parent=row["parent"],
                            # llm_grouping の出力には density / density_rank 列が無いため任意扱いにする
                            density=float(row["density"]) if row.get("density") else None,
                            density_rank=int(float(row["density_rank"])) if row.get("density_rank") else None,
                            density_rank_percentile=float(row["density_rank_percentile"])
                            if row.get("density_rank_percentile")
                            else None,
                        )
                        clusters.append(cluster)
                    except KeyError as e:
                        slogger.warning(f"KeyError: {e} in row: {row}")
                        continue

            return clusters
        except FileNotFoundError:
            slogger.warning(f"File not found: {self.labels_path}")
            raise ClusterFileNotFound(f"File not found: {self.labels_path}") from None
        except Exception as e:
            slogger.error(f"Error reading CSV file: {e}")
            raise ClusterCSVParseError(f"Error reading CSV file: {e}") from e

    def update_csv(self, updated_cluster: ClusterUpdate) -> bool:
        """中間ファイル（CSVファイル）を更新する

        元ファイルの列構成（density 列の無い llm_grouping の出力を含む）を保ったまま、
        対象IDの label / description だけを書き換える。
        対象IDが存在しない場合は ClusterNotFound を送出し、ファイルは変更しない。
        """
        try:
            if not self.labels_path.exists():
                raise ClusterFileNotFound(f"File not found: {self.labels_path}")

            with open(self.labels_path, encoding="utf-8", newline="") as csvfile:
                reader = csv.DictReader(csvfile)
                fieldnames = list(reader.fieldnames or [])
                rows = list(reader)

            # 読み込めた行が無い場合は、ヘッダーだけのファイルで上書きしないよう失敗扱いにする
            if not rows or not {"id", "label", "description"}.issubset(fieldnames):
                slogger.error(f"No cluster rows to update in: {self.labels_path}")
                return False

            # IDをキーとして、更新されたクラスタ情報を差し替える
            found = False
            for row in rows:
                if row["id"] == updated_cluster.id:
                    row["label"] = updated_cluster.label
                    row["description"] = updated_cluster.description
                    found = True
            if not found:
                raise ClusterNotFound(f"Cluster not found: {updated_cluster.id}")

            with open(self.labels_path, mode="w", encoding="utf-8", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
            return True
        except ClusterNotFound:
            raise
        except Exception as e:
            slogger.error(f"Error writing CSV file: {e}")
            return False
