import logging


def configure_logging(logger_name) -> logging.Logger:
    """
    Configure logging

    ### Returns
    logger with configuration set up
    """
    logger = logging.getLogger(logger_name)
    logging.basicConfig(
        filename="playwright_scraping.log",
        level=logging.INFO,
        filemode="a",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logger
