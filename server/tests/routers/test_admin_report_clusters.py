from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.exceptions import ClusterCSVParseError, ClusterFileNotFound
from src.routers.admin_report import router, verify_admin_api_key
from src.schemas.cluster import ClusterResponse


@pytest.fixture
def app():
    """テスト用のFastAPIアプリケーションを作成するフィクスチャ"""
    app = FastAPI()
    app.include_router(router)

    # 認証をバイパスするためのオーバーライド
    async def override_verify_admin_api_key():
        return "test-api-key"

    app.dependency_overrides[verify_admin_api_key] = override_verify_admin_api_key
    return app


@pytest.fixture
def client(app):
    """テスト用のクライアントを作成するフィクスチャ"""
    return TestClient(app)


class TestGetClusters:
    """get_clustersエンドポイントのテスト"""

    def test_get_clusters_success(self, client):
        """正常系：クラスタ情報が正常に取得できるケース"""
        # テスト用のクラスタデータ
        test_clusters = [
            ClusterResponse(
                level=1,
                id="cluster-1",
                label="テストクラスタ1",
                description="テスト説明1",
                value=10,
                parent=None,
                density=0.8,
                density_rank=1,
                density_rank_percentile=0.9,
            ),
            ClusterResponse(
                level=2,
                id="cluster-2",
                label="テストクラスタ2",
                description="テスト説明2",
                value=5,
                parent="cluster-1",
                density=0.6,
                density_rank=2,
                density_rank_percentile=0.7,
            ),
        ]

        # ClusterRepositoryのread_from_csvメソッドをモック化
        with patch("src.routers.admin_report.ClusterRepository") as mock_repo:
            # モックオブジェクトの設定
            mock_instance = mock_repo.return_value
            mock_instance.read_from_csv.return_value = test_clusters

            # エンドポイントにリクエストを送信
            response = client.get(
                "/admin/reports/test-slug/cluster-labels",
                headers={"x-api-key": "test-api-key"},
            )

            # レスポンスを検証
            assert response.status_code == 200
            response_data = response.json()
            assert "clusters" in response_data
            assert len(response_data["clusters"]) == 2
            assert response_data["clusters"][0]["id"] == "cluster-1"
            assert response_data["clusters"][1]["id"] == "cluster-2"

            # モックが正しく呼び出されたことを確認
            mock_repo.assert_called_once_with("test-slug")
            mock_instance.read_from_csv.assert_called_once()

    def test_get_clusters_file_not_found(self, client):
        """異常系：ファイルが存在しないケース"""
        # ClusterRepositoryのread_from_csvメソッドをモック化してClusterFileNotFoundを発生させる
        with patch("src.routers.admin_report.ClusterRepository") as mock_repo:
            mock_instance = mock_repo.return_value
            mock_instance.read_from_csv.side_effect = ClusterFileNotFound("クラスタファイルが見つかりません")

            # エンドポイントにリクエストを送信
            response = client.get(
                "/admin/reports/test-slug/cluster-labels",
                headers={"x-api-key": "test-api-key"},
            )

            # レスポンスを検証
            assert response.status_code == 404
            assert "クラスタファイルが見つかりません" in response.json()["detail"]

    def test_get_clusters_csv_parse_error(self, client):
        """異常系：CSVパースエラーのケース"""
        # ClusterRepositoryのread_from_csvメソッドをモック化してClusterCSVParseErrorを発生させる
        with patch("src.routers.admin_report.ClusterRepository") as mock_repo:
            mock_instance = mock_repo.return_value
            mock_instance.read_from_csv.side_effect = ClusterCSVParseError("CSVのパースに失敗しました")

            # エンドポイントにリクエストを送信
            response = client.get(
                "/admin/reports/test-slug/cluster-labels",
                headers={"x-api-key": "test-api-key"},
            )

            # レスポンスを検証
            assert response.status_code == 500
            assert "CSVのパースに失敗しました" in response.json()["detail"]

    def test_get_clusters_general_exception(self, client):
        """異常系：その他の例外が発生するケース"""
        # ClusterRepositoryのread_from_csvメソッドをモック化して一般的な例外を発生させる
        with patch("src.routers.admin_report.ClusterRepository") as mock_repo:
            mock_instance = mock_repo.return_value
            mock_instance.read_from_csv.side_effect = Exception("予期しないエラーが発生しました")

            # エンドポイントにリクエストを送信
            response = client.get(
                "/admin/reports/test-slug/cluster-labels",
                headers={"x-api-key": "test-api-key"},
            )

            # レスポンスを検証
            assert response.status_code == 500
            assert response.json()["detail"] == "Internal server error"


class TestUpdateClusterLabel:
    """update_cluster_labelエンドポイントのテスト"""

    def test_update_cluster_label_success(self, client):
        """正常系：クラスタラベルが正常に更新されるケース"""
        # テスト用の更新データ
        update_data = {
            "id": "cluster-1",
            "label": "更新されたラベル",
            "description": "更新された説明",
        }

        # ClusterRepositoryのupdate_csvメソッドとexecute_aggregationをモック化
        with (
            patch("src.routers.admin_report.ClusterRepository") as mock_repo,
            patch("src.routers.admin_report.execute_aggregation") as mock_execute,
        ):
            # モックオブジェクトの設定
            mock_instance = mock_repo.return_value
            mock_instance.update_csv.return_value = True
            mock_execute.return_value = True

            # エンドポイントにリクエストを送信
            response = client.patch(
                "/admin/reports/test-slug/cluster-label",
                json=update_data,
                headers={"x-api-key": "test-api-key"},
            )

            # レスポンスを検証
            assert response.status_code == 200
            assert response.json() == {"success": True}

            # モックが正しく呼び出されたことを確認
            mock_repo.assert_called_once_with("test-slug")
            mock_instance.update_csv.assert_called_once()
            mock_execute.assert_called_once_with("test-slug")

    def test_update_cluster_label_csv_update_failed(self, client):
        """異常系：CSVの更新に失敗するケース"""
        # テスト用の更新データ
        update_data = {
            "id": "cluster-1",
            "label": "更新されたラベル",
            "description": "更新された説明",
        }

        # ClusterRepositoryのupdate_csvメソッドをモック化して失敗を返す
        with patch("src.routers.admin_report.ClusterRepository") as mock_repo:
            mock_instance = mock_repo.return_value
            mock_instance.update_csv.return_value = False

            # エンドポイントにリクエストを送信
            response = client.patch(
                "/admin/reports/test-slug/cluster-label",
                json=update_data,
                headers={"x-api-key": "test-api-key"},
            )

            # レスポンスを検証
            assert response.status_code == 500
            assert "意見グループの更新に失敗しました" in response.json()["detail"]

    def test_update_cluster_label_aggregation_failed(self, client):
        """異常系：集計処理の実行に失敗するケース"""
        # テスト用の更新データ
        update_data = {
            "id": "cluster-1",
            "label": "更新されたラベル",
            "description": "更新された説明",
        }

        # ClusterRepositoryのupdate_csvメソッドとexecute_aggregationをモック化
        with (
            patch("src.routers.admin_report.ClusterRepository") as mock_repo,
            patch("src.routers.admin_report.execute_aggregation") as mock_execute,
        ):
            # モックオブジェクトの設定
            mock_instance = mock_repo.return_value
            mock_instance.update_csv.return_value = True
            mock_execute.return_value = False

            # エンドポイントにリクエストを送信
            response = client.patch(
                "/admin/reports/test-slug/cluster-label",
                json=update_data,
                headers={"x-api-key": "test-api-key"},
            )

            # レスポンスを検証
            assert response.status_code == 500
            assert "意見グループ更新の集計に失敗しました" in response.json()["detail"]
