import argparse
import datetime

from .gitee_api import GiteeApi
from .ohdl import download_oh

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('oh_path', type=str)
    parser.add_argument('-a', '--access-token', type=str, required=True)
    parser.add_argument('--since', type=datetime.date.fromisoformat)
    parser.add_argument('--until', type=datetime.date.fromisoformat)
    parser.add_argument('--no-sync', action="store_true")
    
    args = parser.parse_args()

    api = GiteeApi(args.access_token)
    download_oh(args.oh_path, api, since=args.since, until=args.until, no_sync=args.no_sync)

if __name__ == "__main__":
    main()
