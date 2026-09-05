"""Build and check in an isolated directory, without changing the live dist/.

Usage: python3 site/verify_rank_seo.py --output /absolute/new-validation-folder
Only reads existing public exports; does not run collectors, submit URLs or deploy.
"""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re

import build_v5
import i18n_apply
from PIL import Image
from test_rank_seo import ParsedPage


def main(output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Use a new validation directory; existing output is never overwritten")
    output.mkdir(parents=True)
    dist = output / "dist"
    original_dist = build_v5.DIST
    log = io.StringIO()
    try:
        build_v5.DIST = str(dist)
        with contextlib.redirect_stdout(log):
            build_v5.main()
            i18n_apply.main(str(dist), build_v5.BASE)
    finally:
        build_v5.DIST = original_dist
    results = []
    for file in [dist / "rank.html"] + sorted((dist / "rank").glob("*.html")):
        rel = file.relative_to(dist)
        for local_rel in (rel, Path("en") / rel):
            html = (dist / local_rel).read_text(encoding="utf-8")
            parsed = ParsedPage(html)
            graph = parsed.graphs[0]
            url = build_v5.BASE + "/" + str(local_rel)[:-5]
            assert [x["href"] for x in parsed.links if x.get("rel") == "canonical"] == [url]
            assert graph["url"] == parsed.meta["og:url"] == url
            assert graph["name"] == parsed.meta["og:title"]
            assert graph["description"] == parsed.meta["description"] == parsed.meta["og:description"]
            zh_url = build_v5.BASE + "/" + str(rel)[:-5]
            alternates = {x.get("hreflang"): x["href"] for x in parsed.links if x.get("hreflang")}
            assert alternates["zh-CN"] == zh_url
            assert alternates["en"] == build_v5.BASE + "/en/" + str(rel)[:-5]
            assert "<loc>" + url + "</loc>" in (dist / "sitemap.xml").read_text(encoding="utf-8")
            image_url = parsed.meta["og:image"]
            assert image_url == parsed.meta["twitter:image"] == graph["primaryImageOfPage"]["url"]
            image_path = dist / image_url[len(build_v5.BASE) + 1:]
            with Image.open(image_path) as image:
                assert image.size == (1200, 630) and image.format == "PNG"
            schema_rows = [item["item"]["url"] for board in graph["mainEntity"] for item in board["itemListElement"]]
            assert schema_rows == [build_v5.BASE + href for href in parsed.rank_rows]
            if str(local_rel).startswith("en/"):
                assert not re.search(r"[一-鿿]", graph["name"] + graph["description"] + graph["primaryImageOfPage"]["caption"])
            results.append({"page": str(local_rel), "canonical": url,
                            "edition": graph["identifier"], "data_date": graph["dateModified"],
                            "ordered_lists": len(graph["mainEntity"]), "listed_rows": len(schema_rows),
                            "image": str(image_path.relative_to(output)),
                            "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                            "verified": True})
    summary = {"public_export_generated_at": build_v5.D["generated_at"],
               "pages_checked": len(results), "checks": results,
               "production_dist_untouched": True, "deployed_by_this_check": False,
               "note": "Local HTML/JSON-LD/image checks only; not a Google indexing or AI citation result."}
    (output / "verification.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "build.log").write_text(log.getvalue(), encoding="utf-8")
    print(json.dumps({"pages_checked": len(results), "report": str(output / "verification.json"),
                      "build_log": str(output / "build.log"), "deployed": False}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    main(parser.parse_args().output)
