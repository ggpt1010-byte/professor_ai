"""공유용 웹페이지(교수님 답장 예측기)를 만든다.

    python web/build_page.py OUT.html

data/web_examples.json(공유해도 되는 말투 예시)을 web/template.html에 넣는다.
원본 카톡이나 messages.jsonl은 페이지에 넣지 않는다.
"""

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "web" / "index.html"
    style = json.loads((ROOT / "data" / "web_examples.json").read_text(encoding="utf-8"))
    style["updated"] = style.get("updated") or date.today().isoformat()
    payload = json.dumps(style, ensure_ascii=False).replace("</", "<\\/")
    html = (ROOT / "web" / "template.html").read_text(encoding="utf-8")
    out.write_text(html.replace("/*STYLE_DATA*/null", payload), encoding="utf-8")
    print(f"{out} ({len(style['examples'])}개 예시)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
