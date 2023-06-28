from typing import List, Optional
import requests
from datetime import datetime

class GiteeApi:
    def __init__(self, access_token) -> None:
        self.access_token = access_token
    
    def _get_commits(self, owner: str, repo: str,
                     since=None, until=None):
        url = f'https://gitee.com/api/v5/repos/{owner}/{repo}/commits'
        params = {
            'access_token': self.access_token,
        }

        if since is not None:
            params['since'] = since.isoformat()
        if until is not None:
            params['until'] = until.isoformat()

        response = requests.get(url=url, params=params)
        return response.json()

    def get_commits_sha(self, owner: str, repo: str,
                        since=None, until=None) -> List[str]:
        commits = self._get_commits(owner, repo, since=since, until=until)
        try:
            sha_list = [commit['sha'] for commit in commits]
        except:
            print(commits)
            return []
        return sha_list
    
    def get_latest_commit_sha(self, owner: str, repo: str, 
                               since: datetime, until: datetime) -> Optional[str]:
        sha_list = self.get_commits_sha(owner, repo, since=since, until=until)
        if not sha_list:
            return None
        return sha_list[0]
