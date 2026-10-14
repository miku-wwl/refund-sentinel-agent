"""Check current public Markdown references, curated images and immutable PayPal proof."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote


def public_markdown(root):
    if (root / ".git").exists():
        names = subprocess.check_output(
            ["git", "-C", str(root), "ls-files", "-z"], text=True
        ).split("\0")
        paths = [root / name for name in names if name.endswith(".md")]
    else:
        paths = list(root.glob("*.md")) + list((root / "docs").glob("*.md"))
        paths += list((root / "evidence").rglob("*.md"))
    return sorted({path for path in paths if path.is_file()})


def check(root):
    failures, links = [], 0
    for source in public_markdown(root):
        text = source.read_text("utf-8-sig")
        text = re.sub(r"^```[^\n]*\n.*?^```[^\n]*$", "", text, flags=re.M | re.S)
        text = re.sub(r"`[^`\n]+`", "", text)
        for url in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            if url.startswith(("http:", "https:", "mailto:")):
                continue
            links += 1
            path, _, fragment = unquote(url).partition("#")
            target = (source.parent / path).resolve() if path else source
            if not target.is_relative_to(root) or not target.exists():
                failures.append({"source": str(source.relative_to(root)), "link": url})
            elif fragment and target.suffix == ".md":
                headings = re.findall(r"^#{1,6} (.+)$", target.read_text("utf-8-sig"), re.M)
                slugs = {
                    re.sub(r"[^\w -]", "", title.lower()).replace(" ", "-") for title in headings
                }
                if fragment not in slugs:
                    failures.append({"source": str(source.relative_to(root)), "link": url})
    evidence = root / "evidence/submission"
    images = json.loads((evidence / "screenshots-manifest.json").read_text("utf-8"))
    for item in images:
        path = (evidence / item["file"]).resolve()
        if not path.is_relative_to(evidence) or not path.is_file():
            failures.append({"image": item["file"], "reason": "INVALID_IMAGE_PATH"})
            continue
        body = path.read_bytes()
        if len(body) != item["bytes"] or hashlib.sha256(body).hexdigest() != item["sha256"]:
            failures.append({"image": item["file"], "reason": "IMAGE_HASH_MISMATCH"})
    proof_path = root / "evidence/phase2-freeze/verified-refund.json"
    proof = proof_path.read_bytes()
    expected = "1c50dd2f86d63905b69dad4d3b83e3b37a77f7495d3ba1a1c4fee9a7c56f9853"
    if (
        hashlib.sha256(proof).hexdigest() != expected
        or proof != (root / "src/refund_sentinel/static/qualified-case.json").read_bytes()
    ):
        failures.append({"reason": "IMMUTABLE_PAYPAL_PROOF_CHANGED"})
    execution = json.loads(proof)["execution"]
    if not (
        execution["post_http_status"] == 201
        and execution["verification_http_status"] == 200
        and execution["refund_status"] == "COMPLETED"
        and execution["financial_post_count"] == 1
        and execution["receipt_persisted"]
    ):
        failures.append({"reason": "HISTORICAL_EVIDENCE_CONTRACT_INVALID"})
    return {
        "status": "FAIL" if failures else "PASS",
        "local_links_checked": links,
        "screenshot_hashes_checked": len(images),
        "immutable_paypal_proof": "PASS" if not failures else "CHECK_FAILURES",
        "failures": failures,
        "network_requests": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = check(args.root.resolve())
    print(json.dumps(result, indent=2))
    raise SystemExit(result["status"] != "PASS")


if __name__ == "__main__":
    main()
