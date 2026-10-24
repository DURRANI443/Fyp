"""Set the public Oracle HTTPS origin in the checked-in Vercel routing config."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit


def configure(origin, target):
    parsed = urlsplit(origin)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
            or parsed.hostname in {"localhost", "127.0.0.1"} or parsed.hostname.endswith(".invalid")):
        raise ValueError("Use a public HTTPS origin without a path, query, credentials, or fragment.")
    config = json.loads(target.read_text(encoding="utf-8"))
    route = next(entry for entry in config["rewrites"] if entry["source"] == "/api/:path*")
    route["destination"] = origin.rstrip("/") + "/api/:path*"
    target.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("origin")
    args = parser.parse_args()
    try:
        configure(args.origin, Path(__file__).resolve().parents[1] / "frontend" / "vercel.json")
    except ValueError as error:
        parser.exit(2, str(error) + "\n")
    print("Updated frontend/vercel.json. Commit this public hostname change before deploying Vercel.")
