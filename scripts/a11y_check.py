"""Accessibility audit: run axe-core on every screen, as each role, in English and Hindi.

    cd frontend && npm install          # installs axe-core (dev dependency)
    npm run dev                         # app on http://localhost:5173, backend running
    python scripts/a11y_check.py [http://localhost:5173]

Prints violations grouped by rule and exits with status 1 if there are any.
Uses the demo accounts, so run it against a development database.
"""
import sys
from collections import defaultdict
from pathlib import Path

from playwright.sync_api import sync_playwright

UI = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173"
AXE = Path(__file__).resolve().parents[1] / "frontend" / "node_modules" / "axe-core" / "axe.min.js"
PAGES = {
    "operator": ["/upload", "/documents"],
    "verifier": ["/review", "/documents/1", "/dashboard", "/records", "/records/1/extract"],
    "admin": ["/audit", "/users", "/help"],
}
PASSWORDS = {"operator": "upload@123", "verifier": "verify@123", "admin": "admin@123"}
# "region" is off: it wants every piece of text inside a landmark, which toasts and skip links are not
RUN = """async () => {
  const r = await axe.run(document, { resultTypes: ['violations'], rules: { region: { enabled: false } } })
  return r.violations.map(v => ({ id: v.id, impact: v.impact, help: v.help,
    nodes: v.nodes.map(n => n.target.join(' ')) }))
}"""


def sign_in(page, role: str, lang: str) -> None:
    page.goto(UI)
    page.evaluate(f"localStorage.removeItem('landlekha.token'); localStorage.setItem('landlekha.lang', '{lang}')")
    page.reload()
    page.wait_for_selector("#u")
    page.fill("#u", role)
    page.fill("#p", PASSWORDS[role])
    page.keyboard.press("Enter")
    page.wait_for_selector("#main")


def audit(page) -> list[dict]:
    page.add_script_tag(path=str(AXE))
    return page.evaluate(RUN)


def main() -> int:
    if not AXE.exists():
        sys.exit(f"axe-core not found at {AXE}; run `npm install` in frontend/")
    found = defaultdict(lambda: {"help": "", "impact": "", "where": set(), "nodes": set()})
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        for lang in ("en", "hi"):
            page.goto(UI)
            page.evaluate(f"localStorage.removeItem('landlekha.token'); localStorage.setItem('landlekha.lang', '{lang}')")
            page.reload()
            page.wait_for_selector("#u")
            results = [("sign-in", audit(page))]
            for role, paths in PAGES.items():
                sign_in(page, role, lang)
                for path in paths:
                    page.goto(UI + path)
                    page.wait_for_timeout(1500)
                    results.append((f"{role} {path}", audit(page)))
            for where, violations in results:
                for v in violations:
                    f = found[v["id"]]
                    f["help"], f["impact"] = v["help"], v["impact"]
                    f["where"].add(f"{lang}: {where}")
                    f["nodes"].update(v["nodes"][:3])
        browser.close()
    if not found:
        print("no accessibility violations on", sum(len(v) for v in PAGES.values()) + 1, "screens, English and Hindi")
        return 0
    for rule, f in sorted(found.items()):
        print(f"[{f['impact']}] {rule}: {f['help']}")
        print("   on:", ", ".join(sorted(f["where"])))
        for n in sorted(f["nodes"])[:4]:
            print("   -", n)
    return 1


if __name__ == "__main__":
    sys.exit(main())
