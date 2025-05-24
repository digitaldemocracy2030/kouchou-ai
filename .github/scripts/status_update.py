from status_update_common import Config, GithubHandler
from repo_config import REPO_CONFIG

def update_issue_status(github_handler, status, item_id):
    try:
        github_handler.update_issue_status(status, item_id)
        print(f"ステータスを '{status}' に更新しました。")
    except Exception as e:
        print(f"ステータスの更新に失敗しました: {e}")
        raise ValueError("ステータスの更新に失敗しました") from e

def main():
    config = Config()
    github_handler = GithubHandler(config)
    
    try:
        current_status, item_id = github_handler.get_issue_status_and_id()
    except Exception as e:
        print(f"ステータスの取得に失敗しました: {e}")
        raise ValueError("ステータスの取得に失敗しました") from e
    
    if github_handler.action == "assigned":
        if current_status in [
            REPO_CONFIG["status"]["no_status"],
            REPO_CONFIG["status"]["cold_list"],
            REPO_CONFIG["status"]["need_refinement"],
            REPO_CONFIG["status"]["ready"]
            ]:
            print(f"担当者が割り当てられ、ステータスが '{current_status}' のため、'{REPO_CONFIG["status"]["in_progress"]}' に更新します。")
            update_issue_status(github_handler, REPO_CONFIG["status"]["in_progress"], item_id)
        else:
            print(f"ステータスは '{current_status}' です。更新は不要です。")

    elif github_handler.action == "unassigned":
        if current_status == REPO_CONFIG["status"]["in_progress"]:
            print(f"担当者が外れ、ステータスが '{current_status}' のため、'{REPO_CONFIG["status"]["ready"]}' に更新します。")
            update_issue_status(github_handler, REPO_CONFIG["status"]["ready"], item_id)
        else:
            print(f"ステータスは '{current_status}' です。更新は不要です。")

    elif github_handler.action == "ready":
        update_issue_status(github_handler, REPO_CONFIG["status"]["ready"], item_id)

    elif github_handler.action == "archive":
        update_issue_status(github_handler, REPO_CONFIG["status"]["archived"], item_id)

    else :
        print(f"アクション '{github_handler.action}' はサポートされていません。")
        raise ValueError(f"アクション '{github_handler.action}' はサポートされていません。")

if __name__ == "__main__":
    main()