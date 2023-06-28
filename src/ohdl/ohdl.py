import os
from typing import List, Optional
from xml.etree import ElementTree
from datetime import datetime

from .gitee_api import GiteeApi

def _load_or_init_sha_cache(oh_path: str, since: datetime, until: datetime) -> dict:
    sha_cache_path = os.path.join(oh_path, '.sha_cache')
    sha_cache = {}
    sha_cache_entry = _sha_cache_entry(since, until)

    if os.path.exists(sha_cache_path) and os.path.isfile(sha_cache_path):
        sha_cache = eval(open(sha_cache_path, 'r').read())
    if sha_cache_entry not in sha_cache:
        sha_cache[sha_cache_entry] = {}
    return sha_cache

def _save_sha_cache(oh_path: str, sha_cache):
    open(os.path.join(oh_path, '.sha_cache'), 'w').write(str(sha_cache))

def _sha_cache_entry(since: datetime, until: datetime) -> str:
    return f'{since} to {until}'

def _get_sha_from_cache(sha_cache, project: str, since: datetime, until: datetime) -> Optional[str]:
    sha_cache_entry = _sha_cache_entry(since, until)
    if project in sha_cache[sha_cache_entry]:
        return sha_cache[sha_cache_entry][project]['sha']
    else:
        return None
    
def _add_sha_cache(sha_cache, sha: str, project_name: str, project_path: str, since: datetime, until: datetime):
    sha_cache_entry = _sha_cache_entry(since, until)
    sha_cache[sha_cache_entry][project_name] = {
        'path': project_path,
        'sha': sha
    }

def _get_latest_commit_sha(api: GiteeApi, project: str, since: datetime, until: datetime) -> Optional[str]:
    print(f'getting latest commit in {project} from {since} to {until}')
    sha = api.get_latest_commit_sha('openharmony', project, since, until)
    if not sha:
        print('failed to find')
        return None

    print(f'sha is {sha}')
    return sha

def _git_reset_by_sha(project_path: str, sha: str) -> bool:
    cwd = os.getcwd()

    print(f'change to path: {project_path}')
    os.chdir(project_path)

    for _ in range(2):
        reset_cmd = f'git reset --hard {sha}'
        print(reset_cmd)
        res = os.system(reset_cmd)
        if not res:
            break
        else:
            print(f'error = {res}, try again')

        fetch_cmd = 'git fetch'
        print(fetch_cmd)
        res = os.system(fetch_cmd)
        if res:
            print(f'error = {res}')
            return False
    
    print(f'change to path: {cwd}')
    os.chdir(cwd)
    return True

def _parse_projects_from_xml(base: str, xml_path: str, projects: List[dict]):
    print(f'parsing {xml_path}')
    tree = ElementTree.parse(os.path.join(base, xml_path))
    for e in tree.findall('.//project'):
        projects.append({
            'name': e.attrib['name'],
            'path': e.attrib['path']
            })
    for e in tree.findall('.//include'):
        include = e.attrib['name']
        _parse_projects_from_xml(base, include, projects)

def download_oh(oh_path: str, api: GiteeApi, 
                since=None, until=None,
                no_sync=False) -> None:
    if not os.path.exists(oh_path):
        print(f'{oh_path} not exists')
        os.mkdir(oh_path)
    if not os.path.isdir(oh_path):
        print(f'{oh_path} is not a directory')
        return
    
    print(f'change to path: {oh_path}')
    os.chdir(oh_path)

    sha_cache = _load_or_init_sha_cache(oh_path, since, until)

    if '.repo' not in os.listdir(oh_path):
        init_cmd = 'repo init -u https://gitee.com/openharmony/manifest.git -b master -m default.xml --no-clone-bundle --no-repo-verify'
        print(init_cmd)
        res = os.system(init_cmd)
        if res:
            print(f'error = {res}')
            return
        
    manifests_path = os.path.join(oh_path, '.repo/manifests')

    if since or until:
        sha = _get_sha_from_cache(sha_cache, 'manifest', since, until)
        if sha is None:
            sha = _get_latest_commit_sha(api, 'manifest', since, until)
            if sha is None:
                return
            _add_sha_cache(sha_cache, sha, 'manifest', '.repo/manifests', since, until)

        if not _git_reset_by_sha(manifests_path, sha):
            _save_sha_cache(oh_path, sha_cache)
            return

    if not no_sync:
        sync_cmd = 'repo sync -c --no-manifest-update --force-sync'
        print(sync_cmd)
        res = os.system(sync_cmd)
        if res:
            print(f'error = {res}')
            return

    if since or until:
        projects = []
        _parse_projects_from_xml(manifests_path, 'default.xml', projects)

        for project in projects:
            project_sha = _get_sha_from_cache(sha_cache, project['name'], since, until)
            if project_sha is None:
                project_sha = _get_latest_commit_sha(api, project['name'], since, until)
                if project_sha is None:
                    _save_sha_cache(oh_path, sha_cache)
                    return
                _add_sha_cache(sha_cache, project_sha, project['name'], project['path'], since, until)
        _save_sha_cache(oh_path, sha_cache)

        for project in projects:
            project_sha = _get_sha_from_cache(sha_cache, project['name'], since, until)
            print(f'{project}: sha is {project_sha}')
            if not _git_reset_by_sha(os.path.join(oh_path, project['path']), project_sha):
                return
        
    cmds = [
        "repo forall -c 'git lfs pull'",
        'bash build/prebuilts_download.sh',
    ]
    for cmd in cmds:
        print(cmd)
        res = os.system(cmd)
        if res:
            print(f'error = {res}')
            return
        