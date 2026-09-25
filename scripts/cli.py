import asyncio
import logging

import typer

from config import settings
from scripts.seeds.constants import SUPPORTED_COUNTRIES
from scripts.seeds.geo_data import run_seed

app = typer.Typer(help="Service commands")


@app.callback()
def main() -> None:
    """Service commands."""


@app.command("seed-geo-data")
def seed_geo_data(
    country: str = typer.Option(
        None,
        "--country",
        "-c",
        help="ISO-код страны (RU, KZ, ...). Без флага — все страны из конфига.",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Принудительная синхронизация."
    ),
) -> None:
    """Загрузить справочники стран/регионов/городов (идемпотентно)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    countries = SUPPORTED_COUNTRIES
    if country:
        code = country.upper()
        countries = [c for c in SUPPORTED_COUNTRIES if c["code"] == code]
        if not countries:
            raise typer.BadParameter(f"Country {code} not in SUPPORTED_COUNTRIES")

    asyncio.run(run_seed(settings.DATABASE_URL, countries=countries, force=force))


if __name__ == "__main__":
    app()
