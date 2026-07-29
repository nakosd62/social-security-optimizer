#!/usr/bin/env python3
"""Start the Social Security filing timing optimizer web server."""

import argparse
from webapp import run_web_server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start the Social Security filing timing optimizer web server."
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Web server host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Web server port (default: 5000)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_web_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
