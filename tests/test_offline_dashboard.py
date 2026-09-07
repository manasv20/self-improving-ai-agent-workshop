from pathlib import Path
import unittest

from parcelco.web.app import app


class OfflineDashboardTests(unittest.TestCase):
    def test_dashboard_uses_only_local_page_assets(self):
        client = app.test_client()
        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertNotIn("fonts.googleapis.com", html)
        self.assertNotIn("fonts.gstatic.com", html)
        self.assertNotIn("cdn.jsdelivr.net", html)
        self.assertIn('/static/vendor/chart.umd.min.js', html)

    def test_vendored_chart_and_license_ship_with_the_package(self):
        static_dir = Path(__file__).resolve().parents[1] / "parcelco" / "static"

        self.assertGreater((static_dir / "vendor" / "chart.umd.min.js").stat().st_size, 100_000)
        license_text = (static_dir / "vendor" / "chart.js.LICENSE.md").read_text()
        self.assertIn("The MIT License", license_text)


if __name__ == "__main__":
    unittest.main()
