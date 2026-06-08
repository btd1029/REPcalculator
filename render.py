"""物件YAMLをJSONとして埋め込んだdocs/ranking.htmlを生成する。
スコア計算はブラウザ側JS（templates/ranking.html）で行う。
"""

import json
from datetime import datetime
from pathlib import Path

import yaml


def render():
    properties = []
    for path in sorted(Path("properties").glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            prop = yaml.safe_load(f)
        if prop:
            properties.append(prop)

    data_json = json.dumps(properties, ensure_ascii=False)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    template = Path("templates/ranking.html").read_text(encoding="utf-8")

    # Inject data
    output = template.replace(
        "/* __PROPERTIES__ */[]",
        "/* __PROPERTIES__ */" + data_json,
    ).replace(
        '/* __GENERATED__ */"\"',
        '/* __GENERATED__ */"' + timestamp + '"',
    )
    # Simpler timestamp replace
    output = output.replace(
        '/* __GENERATED__ */""',
        '/* __GENERATED__ */"' + timestamp + '"',
    )

    out = Path("docs/ranking.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(output, encoding="utf-8")
    print(f"Written {out} ({len(properties)} properties, {timestamp})")


if __name__ == "__main__":
    render()
