import os
import json
import requests
from github import Github

if not os.getenv('GITHUB_ACTIONS'):
    from dotenv import load_dotenv
    load_dotenv()

STATUS_NO_STATUS = "No Status"
STATUS_COLD_LIST = "Cold List"
STATUS_NEED_REFINEMENT = "Need Refinement"
STATUS_READY = "Ready"
STATUS_IN_PROGRESS = "In Progress"

class Config:
    def __init__(self):
        print("設定の初期化を開始します...")
        self.github_token = os.getenv("GITHUB_TOKEN")
        if self.github_token is None:
            print("GITHUB_TOKENが見つかりません ...")
            return
        else:
            print("GITHUB_TOKENからトークンを正常に取得しました。")
        
        self.project_token = os.getenv("PROJECT_TOKEN")
        if self.project_token is None:
            print("PROJECT_TOKENが見つかりません ...")
            return
        else:
            print("PROJECT_TOKENからトークンを正常に取得しました。")
        
        self.github_repo = os.getenv("GITHUB_REPOSITORY")
        print("GITHUB_REPOSITORYの状態:", "取得済み" if self.github_repo else "見つかりません")
        
        self.issue_number = os.getenv("GITHUB_EVENT_ISSUE_NUMBER")
        if self.issue_number:
            self.issue_number = int(self.issue_number)
            print(f"GITHUB_EVENT_ISSUE_NUMBER: {self.issue_number}")
        else:
            print("GITHUB_EVENT_ISSUE_NUMBERが見つかりません")
        
        
        self.project_id = os.getenv("PROJECT_ID")
        if self.project_id is None:
            print("PROJECT_IDが見つかりません ...")
            return
        
        self.status_field_id = os.getenv("STATUS_FIELD")
        if self.status_field_id is None:
            print("STATUS_FIELDが見つかりません ...")
            return
        
        print("設定の初期化が完了しました。")

class GithubHandler:
    def __init__(self, config: Config):
        self.github = Github(config.github_token)
        self.repo = self.github.get_repo(config.github_repo)
        self.issue = self.repo.get_issue(config.issue_number)
        self.config = config
    
    def get_issue_status(self):
        """GraphQL APIを使用してIssueの現在のステータスを取得する"""
        headers = {
            "Authorization": f"Bearer {self.config.project_token}",
            "Content-Type": "application/json"
        }
        
        issue_node_id = self.issue.raw_data['node_id']
        issue_number = self.issue.number
        
        print(f"Issueノード ID: {issue_node_id}")
        print(f"Issue番号: {issue_number}")
        print(f"プロジェクトID: {self.config.project_id}")
        
        query = """
        query($projectId: ID!, $issueNumber: Int!, $repoOwner: String!, $repoName: String!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              items(first: 100) {
                nodes {
                  id
                  content {
                    ... on Issue {
                      number
                      repository {
                        name
                        owner {
                          login
                        }
                      }
                    }
                  }
                  fieldValueByName(name: "Status") {
                    ... on ProjectV2ItemFieldSingleSelectValue {
                      name
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        repo_parts = self.config.github_repo.split('/')
        repo_owner = repo_parts[0]
        repo_name = repo_parts[1]
        
        variables = {
            "projectId": self.config.project_id,
            "issueNumber": issue_number,
            "repoOwner": repo_owner,
            "repoName": repo_name
        }
        
        print(f"リポジトリ所有者: {repo_owner}")
        print(f"リポジトリ名: {repo_name}")
        
        response = requests.post(
            "https://api.github.com/graphql",
            headers=headers,
            json={"query": query, "variables": variables}
        )
        
        if response.status_code != 200:
            print(f"GraphQL APIからのエラー: {response.text}")
            return None
        
        data = response.json()
        project_items = data.get("data", {}).get("node", {}).get("items", {}).get("nodes", [])
        
        for item in project_items:
            content = item.get("content")
            if content and content.get("__typename") == "Issue":
                if (content.get("number") == issue_number and 
                    content.get("repository", {}).get("name") == repo_name and 
                    content.get("repository", {}).get("owner", {}).get("login") == repo_owner):
                    
                    field_value = item.get("fieldValueByName")
                    if field_value:
                        return field_value.get("name")
                    return None
        
        print("Projectにこのissueが見つかりません。アイテム数:", len(project_items))
        
        
        return None
    
    def update_issue_status(self, status: str):
        """GraphQL APIを使用してIssueのステータスを更新する"""
        headers = {
            "Authorization": f"Bearer {self.config.project_token}",
            "Content-Type": "application/json"
        }
        
        query = """
        query($fieldId: ID!) {
          node(id: $fieldId) {
            ... on ProjectV2SingleSelectField {
              options {
                id
                name
              }
            }
          }
        }
        """
        
        variables = {
            "fieldId": self.config.status_field_id
        }
        
        response = requests.post(
            "https://api.github.com/graphql",
            headers=headers,
            json={"query": query, "variables": variables}
        )
        
        if response.status_code != 200:
            print(f"GraphQL APIからのエラー: {response.text}")
            return False
        
        data = response.json()
        options = data.get("data", {}).get("node", {}).get("options", [])
        
        option_id = None
        for option in options:
            if option["name"] == status:
                option_id = option["id"]
                break
        
        if not option_id:
            print(f"ステータス '{status}' のオプションが見つかりません")
            return False
        
        issue_node_id = self.issue.raw_data['node_id']
        issue_number = self.issue.number
        
        repo_parts = self.config.github_repo.split('/')
        repo_owner = repo_parts[0]
        repo_name = repo_parts[1]
        
        query = """
        query($projectId: ID!, $issueNumber: Int!, $repoOwner: String!, $repoName: String!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              items(first: 100) {
                nodes {
                  id
                  content {
                    ... on Issue {
                      number
                      repository {
                        name
                        owner {
                          login
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {
            "projectId": self.config.project_id,
            "issueNumber": issue_number,
            "repoOwner": repo_owner,
            "repoName": repo_name
        }
        
        response = requests.post(
            "https://api.github.com/graphql",
            headers=headers,
            json={"query": query, "variables": variables}
        )
        
        if response.status_code != 200:
            print(f"GraphQL APIからのエラー: {response.text}")
            return False
        
        data = response.json()
        project_items = data.get("data", {}).get("node", {}).get("items", {}).get("nodes", [])
        
        item_id = None
        for item in project_items:
            content = item.get("content")
            if content and content.get("__typename") == "Issue":
                if (content.get("number") == issue_number and 
                    content.get("repository", {}).get("name") == repo_name and 
                    content.get("repository", {}).get("owner", {}).get("login") == repo_owner):
                    item_id = item["id"]
                    break
        
        if not item_id:
            print("Projectにこのissueが見つかりません。イシューを追加します。")
            item_id = self.add_issue_to_project(issue_node_id)
            if not item_id:
                return False
        
        mutation = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: ID!) {
          updateProjectV2ItemFieldValue(input: {
            projectId: $projectId,
            itemId: $itemId,
            fieldId: $fieldId,
            value: {
              singleSelectOptionId: $optionId
            }
          }) {
            clientMutationId
          }
        }
        """
        
        variables = {
            "projectId": self.config.project_id,
            "itemId": item_id,
            "fieldId": self.config.status_field_id,
            "optionId": option_id
        }
        
        response = requests.post(
            "https://api.github.com/graphql",
            headers=headers,
            json={"query": mutation, "variables": variables}
        )
        
        if response.status_code != 200:
            print(f"GraphQL APIからのエラー: {response.text}")
            return False
        
        print(f"ステータスを '{status}' に正常に更新しました")
        return True
        
    def add_issue_to_project(self, issue_node_id):
        """GraphQL APIを使用してIssueをプロジェクトに追加する"""
        headers = {
            "Authorization": f"Bearer {self.config.project_token}",
            "Content-Type": "application/json"
        }
        
        mutation = """
        mutation($projectId: ID!, $contentId: ID!) {
          addProjectV2ItemById(input: {
            projectId: $projectId,
            contentId: $contentId
          }) {
            item {
              id
            }
          }
        }
        """
        
        variables = {
            "projectId": self.config.project_id,
            "contentId": issue_node_id
        }
        
        print(f"Issueをプロジェクトに追加します。Issue ID: {issue_node_id}")
        
        response = requests.post(
            "https://api.github.com/graphql",
            headers=headers,
            json={"query": mutation, "variables": variables}
        )
        
        if response.status_code != 200:
            print(f"GraphQL APIからのエラー: {response.text}")
            return None
        
        data = response.json()
        if "errors" in data:
            print(f"Issueの追加中にエラーが発生しました: {data['errors']}")
            return None
        
        item = data.get("data", {}).get("addProjectV2ItemById", {}).get("item")
        if item:
            print(f"Issueをプロジェクトに正常に追加しました。Item ID: {item['id']}")
            return item["id"]
        
        print("Issueをプロジェクトに追加できませんでした。")
        return None
