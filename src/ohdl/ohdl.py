import os
import subprocess
from typing import List, Optional
from xml.etree import ElementTree
from datetime import datetime

from .gitee_api import GiteeApi
from .sha_cache import ShaCache

def _get_latest_commit_sha(api: GiteeApi, project: str, since: datetime | None, until: datetime | None) -> Optional[str]:
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

    update_ref_cmd = f'git update-ref refs/remotes/origin/master {sha}';
    print(update_ref_cmd)
    res = os.system(update_ref_cmd)
    if res:
        print(f'error = {res}')
    
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

def _get_local_sha(project_path: str) -> str | None:
    print(f'getting local sha in {project_path}')
    if not os.path.exists(project_path):
        print(f'{project_path} not exists')
        return None

    out = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=project_path)
    out = out.decode("utf-8").strip()
    if out.startswith('fatal'):
        print(f'error: {out}')
        return None
    else:
        return out

def download_oh(oh_path: str, api: GiteeApi, sha_cache: ShaCache,
                entry=None,
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

    _entry = ''
    if entry:
        _entry = entry
    else:
        _entry = ShaCache.entry_from_date(since, until)

    sha_cache.load(ShaCache.path_from_oh_dir(oh_path), _entry)

    if '.repo' not in os.listdir(oh_path):
        init_cmd = 'repo init -u https://gitee.com/openharmony/manifest.git -b master -m default.xml --no-clone-bundle --no-repo-verify'
        print(init_cmd)
        res = os.system(init_cmd)
        if res:
            print(f'error = {res}')
            return
        
    manifests_path = os.path.join(oh_path, '.repo/manifests')

    if entry or since or until:
        sha = sha_cache.get(_entry, 'manifest')
        if sha is None:
            if entry is not None:
                print("project manifest sha is not found in custom entry")
                return
            sha = _get_latest_commit_sha(api, 'manifest', since, until)
            if sha is None:
                return
            sha_cache.add(sha, _entry, 'manifest', '.repo/manifests')

        if not _git_reset_by_sha(manifests_path, sha):
            if entry is None:
                sha_cache.save(ShaCache.path_from_oh_dir(oh_path))
            return

    if not no_sync:
        sync_cmd = 'repo sync -c --no-manifest-update --force-sync'
        print(sync_cmd)
        res = os.system(sync_cmd)
        if res:
            print(f'error = {res}')
            return

    if entry or since or until:
        projects = []
        _parse_projects_from_xml(manifests_path, 'default.xml', projects)

        for project in projects:
            project_sha = sha_cache.get(_entry, project['name'])
            if project_sha is None:
                if entry is not None:
                    print(f"project {project['name']} sha is not found in custom entry")
                    return
                project_sha = _get_latest_commit_sha(api, project['name'], since, until)
                if project_sha is None:
                    sha_cache.save(ShaCache.path_from_oh_dir(oh_path))
                    return
                sha_cache.add(project_sha, _entry, project['name'], project['path'])
        if entry is None:
            sha_cache.save(ShaCache.path_from_oh_dir(oh_path))

        for project in projects:
            project_sha = sha_cache.get(_entry, project['name'])
            print(f'{project}: sha is {project_sha}')
            if not project_sha or not _git_reset_by_sha(os.path.join(oh_path, project['path']), project_sha):
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

def save_sha_cache(oh_path: str, sha_cache: ShaCache, entry: str):
    if not os.path.exists(oh_path):
        print(f'{oh_path} not exists')
        return
    if not os.path.isdir(oh_path):
        print(f'{oh_path} is not a directory')
        return

    print(f'change to path: {oh_path}')
    os.chdir(oh_path)

    sha_cache.load(ShaCache.path_from_oh_dir(oh_path), entry)

    manifests_path = os.path.join(oh_path, '.repo/manifests')
    sha = _get_local_sha(manifests_path)
    if not sha:
        return
    else:
        sha_cache.add(sha, entry, 'manifest', '.repo/manifests')

    projects = []
    _parse_projects_from_xml(manifests_path, 'default.xml', projects)
    for project in projects:
        project_sha = _get_local_sha(os.path.join(oh_path, project['path']))
        if project_sha is None:
            sha_cache.save(ShaCache.path_from_oh_dir(oh_path))
            return
        sha_cache.add(project_sha, entry, project['name'], project['path'])
    sha_cache.save(ShaCache.path_from_oh_dir(oh_path))
