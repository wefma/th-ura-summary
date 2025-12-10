import yaml
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from html import escape
from collections import defaultdict, OrderedDict
from jinja2 import Template
from logging import getLogger
from log import init_logger
from datetime import datetime, timezone, timedelta
import shutil

current_dir = Path(__file__).resolve().parent
configs_dir = current_dir / "configs"
templates_dir = configs_dir / "templates"
files_dir = configs_dir / "files"
dist_dir = current_dir / "dist"
logger = getLogger("th_ura_summary")

init_logger()

with open(configs_dir / "config.yml", "r") as file:
    settings = yaml.safe_load(file)
    logger.info("Configuration loaded.")

logger.setLevel(settings["log_level"])


def increment_stat(stat_dict, player):
    if player not in stat_dict:
        stat_dict[player] = 0
    stat_dict[player] += 1


def scrape():
    stats_by_game = OrderedDict()
    stats_by_shot = OrderedDict()
    for game_id in range(1, settings["game_series_num"] + 1):

        if game_id in settings["exception_game_ids"]:
            logger.info(f"Skipping Game ID: {game_id}")
            continue

        url = f"https://thscore.pndsng.com/index.php?th={game_id}"
        logger.info(f"Fetching data for Game ID: {game_id} from {url}")
        res = requests.get(url)
        logger.info(f"Fetched data for Game ID: {game_id}")

        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table", {"id": "list"})
        if table is None:
            logger.critical(f"Game ID {game_id} has no score table.")
            raise Exception(f"Game ID {game_id} has no score table.")

        game_unique_players = []
        for row in table.find_all("tr")[1:]:
            player = escape(row.find_all("td")[4].text)
            increment_stat(stats_by_shot, player)
            if player not in game_unique_players:
                game_unique_players.append(player)
                increment_stat(stats_by_game, player)
    stats_by_game = OrderedDict(
        sorted(stats_by_game.items(), key=lambda x: x[1], reverse=True)
    )

    stats_by_shot = OrderedDict(
        sorted(stats_by_shot.items(), key=lambda x: x[1], reverse=True)
    )

    logger.debug(f"Stats by Game: {stats_by_game}")
    logger.debug(f"Stats by Shot: {stats_by_shot}")
    logger.info("Scraping completed.")

    return {"stats_by_game": stats_by_game, "stats_by_shot": stats_by_shot}


def build_rows(data: dict):
    grouped = defaultdict(list)
    for name, count in data.items():
        grouped[count].append(name)

    # count の大きい順にソートし、名前も必要ならソート
    rows = []
    for count in sorted(grouped.keys(), reverse=True):
        rows.append(
            {
                "count": count,
                "player_count": len(grouped[count]),
                "names": sorted(grouped[count]),
            }
        )
    logger.debug(f"Built rows: {rows}")
    return rows


def save_html(template: Template, filename: str, rows: list, meta: dict):

    with open(dist_dir / filename, "w", encoding="utf-8") as f:
        f.write(
            template.render(
                rows=rows,
                meta=meta,
            )
        )
    logger.info(f"Saved HTML file: {filename}")


fetched_structed_data = scrape()
fetched_time = datetime.now(timezone(timedelta(hours=9))).strftime(
    "%Y年%m月%d日 %H時%M分"
)


with open(templates_dir / "table.html.j2", "r", encoding="utf-8") as f:
    template_source = f.read()
    template_table = Template(source=template_source)
    logger.info("Loaded table.html template.")

if not dist_dir.exists():
    dist_dir.mkdir()
    logger.info(f"Created distribution directory at {dist_dir}")


save_html(
    template_table,
    "stat-by-game.html",
    build_rows(fetched_structed_data["stats_by_game"]),
    {
        "title": "裏スコボまとめ(作品数)",
        "table": {
            "header": {
                "count": "作品数",
                "player_count": "人数",
                "names": "プレイヤー名",
            },
            "rows": {
                "unit": {
                    "count": "作品",
                    "player_count": "名",
                },
            },
        },
        "fetched_time": fetched_time,
    },
)

save_html(
    template_table,
    "stat-by-shot.html",
    build_rows(fetched_structed_data["stats_by_shot"]),
    {
        "title": "裏スコボまとめ(機体数)",
        "table": {
            "header": {
                "count": "機体数",
                "player_count": "人数",
                "names": "プレイヤー名",
            },
            "rows": {
                "unit": {
                    "count": "機体",
                    "player_count": "名",
                },
            },
        },
        "fetched_time": fetched_time,
    },
)

with open(templates_dir / "index.html.j2", "r", encoding="utf-8") as f:
    template_source = f.read()
    template_index = Template(source=template_source)
    logger.info("Loaded index.html template.")

with open(dist_dir / "index.html", "w", encoding="utf-8") as f:
    f.write(
        template_index.render(
            meta={"fetched_time": fetched_time},
        )
    )

# shutil.copy(files_dir / "index.html", dist_dir / "index.html")
shutil.copytree(files_dir, dist_dir, dirs_exist_ok=True)

logger.info("All tasks completed successfully.")
