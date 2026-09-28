"""Entry point.

Contoh:
    python run_pipeline.py all        # generate data -> ETL -> laporan analitik
    python run_pipeline.py generate   # hanya membuat ulang database sumber
    python run_pipeline.py etl        # hanya menjalankan ETL
    python run_pipeline.py report     # hanya menjalankan query analitik
"""
import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s",
                    datefmt="%H:%M:%S")


def main() -> int:
    parser = argparse.ArgumentParser(description="Lucien Avenue Sales Analytics pipeline")
    parser.add_argument("step", choices=["generate", "etl", "report", "all"])
    args = parser.parse_args()

    if args.step in ("generate", "all"):
        from src.generator.generate_source import generate
        generate()
    if args.step in ("etl", "all"):
        from src.etl.pipeline import run_etl
        run_etl()
    if args.step in ("report", "all"):
        from src.analytics.report import run_reports
        run_reports()
    return 0


if __name__ == "__main__":
    sys.exit(main())
