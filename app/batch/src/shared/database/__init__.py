from shared.config import load_batch_config


def connect_database():
    import psycopg

    config = load_batch_config()
    return psycopg.connect(config.database_url)
