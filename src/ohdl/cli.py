import argparse
import datetime

from .gitee_api import GiteeApi
from .sha_cache import ShaCache
from .ohdl import download_oh, save_sha_cache

def handle_download(args):
    api = GiteeApi(args.access_token)
    sha_cache = ShaCache()
    download_oh(args.oh_path, api, sha_cache, entry=args.entry, since=args.since, until=args.until, no_sync=args.no_sync)

def handle_save_sha_cache(args):
    sha_cache = ShaCache()
    save_sha_cache(args.oh_path, sha_cache, args.entry)

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="subcommands", required=True)

    parser_download = subparsers.add_parser('download')
    parser_download.add_argument('oh_path', type=str)
    parser_download.add_argument('-a', '--access-token', type=str, required=True)
    parser_download.add_argument('-e', '--entry', type=str, help='use custom sha_cache entry')
    parser_download.add_argument('--since', type=datetime.date.fromisoformat)
    parser_download.add_argument('--until', type=datetime.date.fromisoformat)
    parser_download.add_argument('--no-sync', action="store_true")
    parser_download.set_defaults(func=handle_download)

    parser_save_sha_cache = subparsers.add_parser('save-sha-cache')
    parser_save_sha_cache.add_argument('oh_path', type=str)
    parser_save_sha_cache.add_argument('entry', type=str, help='custom entry name')
    parser_save_sha_cache.set_defaults(func=handle_save_sha_cache)
    
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
