import os
import regex as re
from github import Github
import openai

if not os.getenv('GITHUB_ACTIONS'):
    from dotenv import load_dotenv
    load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
COLLECTION_NAME = "issue_collection"
GPT_MODEL = "gpt-4.1-nano"
MAX_RESULTS = 3

class Config:
    def __init__(self):
        print("設定の初期化を開始します...")
        self.github_token = os.getenv("GITHUB_TOKEN")
        if self.github_token is None:
            print("GITHUB_TOKENが見つかりません ...")
        else:
            print("GITHUB_TOKENからトークンを正常に取得しました。")
        
        self.github_repo = os.getenv("GITHUB_REPOSITORY")
        print("GITHUB_REPOSITORYの状態:", "取得済み" if self.github_repo else "見つかりません")
        
        self.issue_number = os.getenv("GITHUB_EVENT_ISSUE_NUMBER")
        if self.issue_number:
            self.issue_number = int(self.issue_number)
            print(f"GITHUB_EVENT_ISSUE_NUMBER: {self.issue_number}")
        else:
            print("GITHUB_EVENT_ISSUE_NUMBERが見つかりません")
        print("設定の初期化が完了しました。")

class GithubHandler:
    def __init__(self, config: Config):
        self.github = Github(config.github_token)
        self.repo = self.github.get_repo(config.github_repo)
        self.issue = self.repo.get_issue(config.issue_number)

    def add_label(self, label: str):
        """Issueにラベルを追加する"""
        self.issue.add_to_labels(label)

class IssueProcessor:
    def __init__(self, github_handler: GithubHandler, openai_client: openai.Client):
        self.github_handler = github_handler
        self.openai_client = openai_client
        self.available_labels = [
            'Admin', 'Algorithm', 'API', 'bug', 'Client', 'dependencies', 'design', 
            'docker', 'documentation', 'e2e-test-required', 'enhancement', 
            'github_actions', 'good first issue', 'invalid', 'javascript', 'python'
        ]

    def process_issue(self, issue_content: str, issue_title: str = ""):
        """Issueを処理する"""
        if issue_title:
            self._check_and_add_title_labels(issue_title)
        
        self._analyze_and_add_content_labels(issue_content)
        
    def _check_and_add_title_labels(self, title: str):
        """タイトル内の[text]形式の文字列や絵文字を検出し、対応するラベルを付与する"""
        tag_matches = re.findall(r'\[([^\[\]]+)\]', title)
        if tag_matches:
            tag_to_label = {
                'admin': 'Admin',
                'algorithm': 'Algorithm',
                'api': 'API',
                'bug': 'bug',
                'client': 'Client',
                'dependencies': 'dependencies',
                'design': 'design',
                'docker': 'docker',
                'documentation': 'documentation',
                'enhancement': 'enhancement',
                'github': 'github_actions',
                'github actions': 'github_actions',
                'javascript': 'javascript',
                'js': 'javascript',
                'python': 'python',
                'py': 'python',
                'invalid': 'invalid'
            }
            
            for tag_match in tag_matches:
                tag = tag_match.strip().lower()
                if tag in tag_to_label:
                    self.github_handler.add_label(tag_to_label[tag])
        
        emoji_matches = re.findall(r'([^\w\s])', title)
        if emoji_matches:
            emoji_to_label = {
                '🐛': 'bug',
                '✨': 'enhancement',
                '📚': 'documentation',
                '📝': 'documentation',
                '🎨': 'design',
                '🤖': 'Algorithm'
            }
            
            for emoji in emoji_matches:
                if emoji in emoji_to_label:
                    self.github_handler.add_label(emoji_to_label[emoji])
                
    def _analyze_and_add_content_labels(self, issue_content: str):
        """OpenAIを使ってIssueの内容からラベルを判定する"""
        prompt = f"""
        以下はGitHubのIssueの内容です。この内容を分析して、最も適切なラベルを選んでください。
        
        Issue内容:
        {issue_content}
        
        選択可能なラベル:
        {', '.join(self.available_labels)}
        
        このIssueに付与すべきラベルを3つまで選んでJSON形式で返してください。
        例: {{"labels": ["bug", "javascript", "enhancement"]}}
        
        Issueの内容に合わないラベルは選ばないでください。適切なラベルが1つか2つしかない場合は、無理に3つ選ぶ必要はありません。
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=GPT_MODEL,
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=1024
            )
            
            result = response.choices[0].message.content
            print(f"OpenAIからのレスポンス: {result}")
            
            import json
            try:
                labels_data = json.loads(result)
                if "labels" in labels_data and isinstance(labels_data["labels"], list):
                    for label in labels_data["labels"]:
                        if label in self.available_labels:
                            self.github_handler.add_label(label)
                            print(f"ラベルを追加しました: {label}")
            except json.JSONDecodeError as e:
                print(f"JSONのパースに失敗しました: {e}")
                
        except Exception as e:
            print(f"OpenAIによるラベル判定中にエラーが発生しました: {e}")

def setup():
    """セットアップを行い、必要なオブジェクトを返す"""
    config = Config()
    github_handler = GithubHandler(config)

    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key is None:
            print("OPENAI_API_KEYが見つかりません ...")
            return github_handler, None
    except Exception as e:
        print(f"OpenAI APIキーの取得中にエラーが発生しました: {e}")
    openai_client = openai.Client(api_key=openai_api_key)

    return github_handler, openai_client

def main():
    github_handler, openai_client = setup()
    if github_handler is None or openai_client is None:
        print("セットアップに失敗しました。")
        return

    issue_processor = IssueProcessor(github_handler, openai_client)
    issue_title = github_handler.issue.title
    issue_content = f"{issue_title}\n{github_handler.issue.body}"
    issue_processor.process_issue(issue_content, issue_title)

if __name__ == "__main__":
    main()
