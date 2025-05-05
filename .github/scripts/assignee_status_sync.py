from sync_status import Config, GithubHandler, STATUS_NO_STATUS, STATUS_COLD_LIST, STATUS_NEED_REFINEMENT, STATUS_READY, STATUS_IN_PROGRESS
import os

def main():
    config = Config()
    
    if not all([config.github_token, config.github_repo, 
               config.project_token, config.project_id, 
               config.issue_number, config.status_field_id]):
        print("必要な環境変数が設定されていません。処理を中止します。")
        return
    
    github_handler = GithubHandler(config)
    
    action = os.getenv("GITHUB_EVENT_ACTION")
    if not action:
        print("GITHUB_EVENT_ACTIONが見つかりません。処理を中止します。")
        return
    
    current_status = github_handler.get_issue_status()
    
    if action == "assigned":
        if current_status in [STATUS_NO_STATUS, STATUS_COLD_LIST, STATUS_NEED_REFINEMENT, STATUS_READY]:
            print(f"担当者が割り当てられ、ステータスが '{current_status}' のため、'In Progess' に更新します。")
            github_handler.update_issue_status(STATUS_IN_PROGRESS)
            print(f"Issueのステータスを '{STATUS_IN_PROGRESS}' に更新しました。")
        else:
            print(f"ステータスは '{current_status}' です。更新は不要です。")
    elif action == "unassigned":
        if current_status == STATUS_IN_PROGRESS:
            print(f"担当者が外れ、ステータスが '{STATUS_IN_PROGRESS}' のため、'Ready' に更新します。")
            github_handler.update_issue_status(STATUS_READY)
            print(f"Issueのステータスを '{STATUS_READY}' に更新しました。")
        else:
            print(f"ステータスは '{current_status}' です。更新は不要です。")

if __name__ == "__main__":
    main()
