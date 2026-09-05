"""Run: python3 -m unittest discover -s site -p test_rank_seo.py -v"""
import copy
import importlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from html.parser import HTMLParser

import i18n_apply
from rank_seo import BASE, rank_image_path, rank_metadata, translate_rank_graph
from seo_assets import generate_rank_images, generate_rank_snapshot_images, og_rank
from PIL import Image

HERE = Path(__file__).resolve().parent


def sample():
    # Synthetic fixtures for tests only; never deployed or used in share assets.
    return {"week": "2026-w36", "date": "2026-09-05", "window_days": 7,
            "n_sites": 2, "n_quotes": 0, "eligible_uptime": 1,
            "fast": [{"domain": "b.example"}, {"domain": "a.example"}],
            "price": [], "low": [{"domain": "low.example"}],
            "uptime": [{"domain": "hidden.example"}], "probe": [{"domain": "probe.example"}],
            "flagship": [{"id": "example-model", "name": "Example Model", "rows": [{"vendor": "model.example"}]}],
            "media": {"video": [{"family": "example-video", "name": "Example Video", "rows": [{"site": "video.example"}]}]}}


class ParsedPage(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.meta = {}; self.links = []; self.graphs = []
        self._json = None; self.rank_rows = []; self._rank = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta": self.meta[attrs.get("property", attrs.get("name"))] = attrs.get("content")
        if tag == "link": self.links.append(attrs)
        if tag == "script" and attrs.get("type") == "application/ld+json": self._json = ""
        if tag == "ol" and attrs.get("class") == "rk": self._rank = True
        if tag == "a" and self._rank: self.rank_rows.append(attrs["href"])

    def handle_data(self, data):
        if self._json is not None: self._json += data

    def handle_endtag(self, tag):
        if tag == "script" and self._json is not None:
            self.graphs.append(json.loads(self._json)); self._json = None
        if tag == "ol": self._rank = False


def english(html, path):
    tr = i18n_apply.Tr(); tr.feed(html)
    return i18n_apply.head_fix(i18n_apply.relink("".join(tr.out), BASE), BASE, path)


class RankMetadataTests(unittest.TestCase):
    def test_does_not_mutate_snapshot_or_sort(self):
        rank = sample(); original = copy.deepcopy(rank)
        graph = rank_metadata(rank)["jsonld"]
        self.assertEqual(rank, original)
        self.assertEqual([r["item"]["name"] for r in graph["mainEntity"][0]["itemListElement"]], ["b.example", "a.example"])

    def test_positions_counts_and_only_visible_rankings(self):
        graph = rank_metadata(sample())["jsonld"]
        for board in graph["mainEntity"]:
            self.assertEqual(board["numberOfItems"], len(board["itemListElement"]))
            self.assertEqual([r["position"] for r in board["itemListElement"]], list(range(1, board["numberOfItems"] + 1)))
        self.assertNotIn("hidden.example", json.dumps(graph))
        self.assertNotIn("probe.example", json.dumps(graph))
        self.assertIn("最低可达率", json.dumps(graph, ensure_ascii=False))

    def test_does_not_claim_ratings_dataset_or_private_distribution(self):
        text = json.dumps(rank_metadata(sample()))
        for term in ("aggregateRating", "ratingValue", "review", "Dataset", "distribution", "/api/history/"):
            self.assertNotIn(term, text)

    def test_latest_and_permanent_urls(self):
        for path in ("/rank", "/rank/2026-w36"):
            graph = rank_metadata(sample(), path)["jsonld"]
            self.assertEqual(graph["url"], BASE + path)
            self.assertEqual(graph["@id"], BASE + path + "#rankings")

    def test_invalid_paths_weeks_dates_rejected(self):
        for week in ("../secret", "2026-w99", "2026-w00", "2025-w53", "2026-w36/other"):
            rank = sample(); rank["week"] = week
            with self.assertRaises(ValueError): rank_metadata(rank)
        rank = sample(); rank["date"] = "2026-99-05"
        with self.assertRaises(ValueError): rank_metadata(rank)
        with self.assertRaises(ValueError): rank_metadata(sample(), "/rank/2026-w35")

    def test_empty_boards_are_not_invented(self):
        rank = {k: sample()[k] for k in ("week", "date")}
        self.assertEqual(rank_metadata(rank)["jsonld"]["mainEntity"], [])

    def test_image_version_changes_only_with_displayed_facts(self):
        rank = sample(); before = rank_image_path(rank)
        rank["fast"].reverse()
        self.assertEqual(before, rank_image_path(rank))
        rank["n_quotes"] = 3
        self.assertNotEqual(before, rank_image_path(rank))
        self.assertIn("/en/", rank_image_path(rank, "en"))
        with self.assertRaises(ValueError): rank_image_path(rank, "fr")

    def test_english_graph_localizes_names_and_owned_urls(self):
        graph = rank_metadata(sample(), "/rank/2026-w36")["jsonld"]
        translated = translate_rank_graph(graph, i18n_apply.tr_text)
        self.assertEqual(graph["inLanguage"], "zh-CN")
        self.assertEqual(translated["url"], BASE + "/en/rank/2026-w36")
        self.assertEqual(translated["inLanguage"], "en")
        self.assertIn("/img/og/rank/en/", translated["primaryImageOfPage"]["url"])
        self.assertIsNone(re.search(r"[一-鿿]", json.dumps(translated, ensure_ascii=False)))
        self.assertEqual(translated, translate_rank_graph(translated, i18n_apply.tr_text))

    def test_unrelated_schema_unchanged(self):
        unrelated = {"@type": "Dataset", "name": "既有数据", "url": BASE + "/"}
        self.assertEqual(unrelated, translate_rank_graph(unrelated, i18n_apply.tr_text))

    def test_image_dimensions_zero_missing_and_large_counts(self):
        with tempfile.TemporaryDirectory(prefix="sinan-rank-image-test-") as output:
            for locale in ("zh", "en"):
                rank = sample()
                rank["n_sites"] = None; rank["eligible_uptime"] = 100000000000
                target = og_rank(rank, locale, output)
                with Image.open(target) as image:
                    self.assertEqual(image.size, (1200, 630))
                    self.assertEqual(image.format, "PNG")
            rank["n_quotes"] = -1
            with self.assertRaises(ValueError): og_rank(rank, output=output)

    def test_generates_historical_and_current_cards_without_collisions(self):
        with tempfile.TemporaryDirectory(prefix="sinan-rank-assets-test-") as output:
            archive = Path(output) / "snapshots"; archive.mkdir()
            old = sample()
            (archive / "2026-w36.json").write_text(json.dumps(old), encoding="utf-8")
            current = copy.deepcopy(old); current["n_quotes"] = 12
            images = generate_rank_images({"rank": current}, str(archive), output)
            self.assertEqual(len(images), 4)
            self.assertEqual(len(set(images)), 4)
            self.assertTrue(all(Path(path).is_file() for path in images))

    def test_snapshot_filename_mismatch_fails(self):
        with tempfile.TemporaryDirectory(prefix="sinan-rank-invalid-test-") as output:
            (Path(output) / "2026-w35.json").write_text(json.dumps(sample()), encoding="utf-8")
            with self.assertRaises(ValueError): generate_rank_images({}, output, output)


@unittest.skipUnless((HERE / "data_v2.json").is_file(), "Local public export needed for render integration")
class RankRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = importlib.import_module("build_v5")
        cls.snapshots = [(cls.build.D["rank"], "/rank")]
        for path in sorted((HERE / "rank").glob("*.json")):
            cls.snapshots.append((json.loads(path.read_text(encoding="utf-8")), "/rank/" + path.stem))
        cls.assets = tempfile.TemporaryDirectory(prefix="sinan-rank-render-test-")
        cls.addClassCleanup(cls.assets.cleanup)
        generate_rank_snapshot_images([rank for rank, _ in cls.snapshots], cls.assets.name)

    def test_actual_html_urls_jsonld_images_and_visible_order_match(self):
        for rank, path in self.snapshots:
            original = copy.deepcopy(rank)
            zh = self.build.build_rank(rank, [], path)
            self.assertEqual(rank, original)
            for locale, rendered in (("zh", zh), ("en", english(zh, path))):
                with self.subTest(path=path, locale=locale):
                    parsed = ParsedPage(rendered); graph = parsed.graphs[0]
                    expected = BASE + ("/en" if locale == "en" else "") + path
                    self.assertEqual([x["href"] for x in parsed.links if x.get("rel") == "canonical"], [expected])
                    self.assertEqual(parsed.meta["og:url"], expected)
                    self.assertEqual(graph["url"], expected)
                    self.assertEqual(graph["dateModified"], rank["date"])
                    self.assertEqual(parsed.meta["og:image"], BASE + rank_image_path(rank, locale))
                    self.assertEqual(parsed.meta["twitter:image"], parsed.meta["og:image"])
                    self.assertEqual(graph["primaryImageOfPage"]["url"], parsed.meta["og:image"])
                    self.assertEqual(parsed.meta["og:image:alt"], graph["primaryImageOfPage"]["caption"])
                    self.assertTrue((Path(self.assets.name) / rank_image_path(rank, locale)[len("/img/"):]).is_file())
                    schema_links = [row["item"]["url"] for board in graph["mainEntity"] for row in board["itemListElement"]]
                    self.assertEqual(schema_links, [BASE + link for link in parsed.rank_rows])
                    if locale == "en":
                        self.assertIsNone(re.search(r"[一-鿿]", graph["name"] + graph["description"] + graph["primaryImageOfPage"]["caption"]))

    def test_jsonld_cannot_close_script(self):
        rank = copy.deepcopy(self.snapshots[0][0])
        rank["flagship"][0]["name"] = '</script><script>alert("example")</script>'
        html = self.build.build_rank(rank, [])
        self.assertNotIn('<script>alert("example")', html)
        self.assertEqual(len(ParsedPage(html).graphs), 1)

    def test_non_rank_english_head_does_not_rewrite_image(self):
        html = self.build.build_index()
        result = english(html, "/")
        self.assertEqual(ParsedPage(html).meta["og:image"], ParsedPage(result).meta["og:image"])

    def test_wording_guard_on_rank_metadata(self):
        import sys
        sys.path.insert(0, str(HERE.parent))
        from core.wording import lint
        for rank, path in self.snapshots:
            seo = rank_metadata(rank, path)
            for key in ("title", "description", "image_alt"):
                for text in (seo[key], i18n_apply.tr_text(seo[key])):
                    self.assertEqual(lint(text), [])


if __name__ == "__main__":
    unittest.main()
