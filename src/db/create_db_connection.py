import json
import sqlalchemy as sa

def load_db_config(path):
    """ Load the database configuration from a JSON file. """
    with open(path, "r") as file:
        config = json.load(file)
    return config

def create_connection(config):
    """ Create a database connection using the provided configuration. """
    connection_string = sa.engine.url.URL.create(
        drivername=config["drivername"],
        username=config["username"],
        password=config["password"],
        host=config["host"],
        port=config["port"],
        database=config["database"]
    )
    engine = sa.create_engine(connection_string)
    return engine

if __name__ == "__main__":
	config_path = "config/db_config.json"
	config = load_db_config(config_path)
	engine = create_connection(config)

