import logging


def setup_logging():
    handlers = [
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler(),
    ]

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )
