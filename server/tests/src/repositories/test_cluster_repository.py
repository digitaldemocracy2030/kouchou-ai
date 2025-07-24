from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.core.exceptions import ClusterCSVParseError, ClusterFileNotFound
from src.repositories.cluster_repository import ClusterRepository
from src.schemas.cluster import ClusterResponse, ClusterUpdate


class TestClusterRepository:
    """ClusterRepositoryのテスト"""

    @pytest.fixture
    def test_slug(self):
        """テスト用のスラグ"""
        return "test-slug"

    @pytest.fixture
    def cluster_repository(self, test_slug):
        """ClusterRepositoryのインスタンス"""
        return ClusterRepository(test_slug)

    @pytest.fixture
    def mock_csv_data(self):
        """モック用のCSVデータ"""
        return [
            {
                "level": "1",
                "id": "cluster-1",
                "label": "テストラベル1",
                "description": "テスト説明1",
                "value": "10",
                "parent": "",
                "density": "0.8",
                "density_rank": "1",
                "density_rank_percentile": "0.9",
            },
            {
                "level": "2",
                "id": "cluster-2",
                "label": "テストラベル2",
                "description": "テスト説明2",
                "value": "5",
                "parent": "cluster-1",
                "density": "0.6",
                "density_rank": "2",
                "density_rank_percentile": "0.7",
            },
            {
                "level": "2",
                "id": "cluster-3",
                "label": "テストラベル3",
                "description": "テスト説明3",
                "value": "4",
                "parent": "cluster-1",
                "density": "",
                "density_rank": "",
                "density_rank_percentile": "",
            },
        ]

    @pytest.fixture
    def expected_clusters(self):
        """期待されるClusterResponseのリスト"""
        return [
            ClusterResponse(
                level=1,
                id="cluster-1",
                label="テストラベル1",
                description="テスト説明1",
                value=10,
                parent="",
                density=0.8,
                density_rank=1,
                density_rank_percentile=0.9,
            ),
            ClusterResponse(
                level=2,
                id="cluster-2",
                label="テストラベル2",
                description="テスト説明2",
                value=5,
                parent="cluster-1",
                density=0.6,
                density_rank=2,
                density_rank_percentile=0.7,
            ),
            ClusterResponse(
                level=2,
                id="cluster-3",
                label="テストラベル3",
                description="テスト説明3",
                value=4,
                parent="cluster-1",
                density=None,
                density_rank=None,
                density_rank_percentile=None,
            ),
        ]

    def test_init(self, test_slug, cluster_repository):
        """初期化時にスラグが正しく設定されることを確認"""
        assert cluster_repository.slug == test_slug
        assert str(cluster_repository.labels_path).endswith(f"{test_slug}/hierarchical_merge_labels.csv")

    def test_read_from_csv_file_not_exists(self, cluster_repository):
        """CSVファイルが存在しない場合、ClusterFileNotFoundエラーが発生することを確認"""
        # ファイルが存在しないようにパッチを適用
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(ClusterFileNotFound) as excinfo:
                cluster_repository.read_from_csv()

        # 検証
        assert "File not found" in str(excinfo.value)

    def test_read_from_csv_success(self, cluster_repository, mock_csv_data, expected_clusters):
        """CSVファイルが正常に読み込まれることを確認"""
        # ファイルが存在するようにパッチを適用
        with patch.object(Path, "exists", return_value=True):
            # CSVファイルの読み込みをモック
            with patch("builtins.open", mock_open()):
                with patch("csv.DictReader", return_value=mock_csv_data):
                    result = cluster_repository.read_from_csv()

        # 検証
        assert len(result) == len(expected_clusters)
        for i, cluster in enumerate(result):
            assert cluster.model_dump() == expected_clusters[i].model_dump()

    def test_read_from_csv_key_error(self, cluster_repository):
        """CSVファイルの読み込み中にKeyErrorが発生した場合、エラーをスキップして続行することを確認"""
        # 必須フィールドが欠けているデータ
        invalid_data = [
            {"level": "1", "id": "cluster-1"},  # labelフィールドが欠けている
            {
                "level": "2",
                "id": "cluster-2",
                "label": "テストラベル2",
                "description": "テスト説明2",
                "value": "10",
                "parent": "cluster-1",
                "density": "0.6",
                "density_rank": "2",
                "density_rank_percentile": "0.7",
            },
        ]

        # ファイルが存在するようにパッチを適用
        with patch.object(Path, "exists", return_value=True):
            # CSVファイルの読み込みをモック
            with patch("builtins.open", mock_open()):
                with patch("csv.DictReader", return_value=invalid_data):
                    result = cluster_repository.read_from_csv()

        # 検証
        assert len(result) == 1  # エラーのあるデータはスキップされる
        assert result[0].id == "cluster-2"

    def test_read_from_csv_file_not_found_error(self, cluster_repository):
        """CSVファイルが見つからない場合、ClusterFileNotFoundエラーが発生することを確認"""
        # ファイルが存在するようにパッチを適用
        with patch.object(Path, "exists", return_value=True):
            # ファイルが見つからないエラーを発生させる
            with patch("builtins.open", side_effect=FileNotFoundError()):
                with pytest.raises(ClusterFileNotFound) as excinfo:
                    cluster_repository.read_from_csv()

        # 検証
        assert "File not found" in str(excinfo.value)

    def test_read_from_csv_general_exception(self, cluster_repository):
        """CSVファイルの読み込み中に一般的な例外が発生した場合、ClusterCSVParseErrorが発生することを確認"""
        # ファイルが存在するようにパッチを適用
        with patch.object(Path, "exists", return_value=True):
            # 一般的な例外を発生させる
            with patch("builtins.open", side_effect=Exception("一般的なエラー")):
                with pytest.raises(ClusterCSVParseError) as excinfo:
                    cluster_repository.read_from_csv()

        # 検証
        assert "一般的なエラー" in str(excinfo.value)

    def test_update_csv_success(self, cluster_repository, mock_csv_data, expected_clusters):
        """CSVファイルの更新が成功することを確認"""
        # 更新するクラスタ
        updated_cluster = ClusterUpdate(
            id="cluster-2",
            label="更新されたラベル",
            description="更新された説明",
        )

        # read_from_csvの結果をモック
        with patch.object(ClusterRepository, "read_from_csv", return_value=expected_clusters):
            # ファイルの書き込みをモック
            mock_csv_writer = MagicMock()
            with patch("builtins.open", mock_open()):
                with patch("csv.DictWriter", return_value=mock_csv_writer):
                    result = cluster_repository.update_csv(updated_cluster)

        # 検証
        assert result is True
        # writeheaderが呼ばれたことを確認
        mock_csv_writer.writeheader.assert_called_once()
        # writerowが3回呼ばれたことを確認（3つのクラスタがある）
        assert mock_csv_writer.writerow.call_count == 3
        # 2番目のクラスタが更新されていることを確認
        updated_data = mock_csv_writer.writerow.call_args_list[1][0][0]
        assert updated_data["label"] == "更新されたラベル"
        assert updated_data["description"] == "更新された説明"

    def test_update_csv_exception(self, cluster_repository, expected_clusters):
        """CSVファイルの更新中に例外が発生した場合、Falseが返されることを確認"""
        # 更新するクラスタ
        updated_cluster = ClusterUpdate(
            id="cluster-2",
            label="更新されたラベル",
            description="更新された説明",
        )

        # read_from_csvの結果をモック
        with patch.object(ClusterRepository, "read_from_csv", return_value=expected_clusters):
            # ファイルの書き込み中に例外を発生させる
            with patch("builtins.open", side_effect=Exception("書き込みエラー")):
                result = cluster_repository.update_csv(updated_cluster)

        # 検証
        assert result is False
