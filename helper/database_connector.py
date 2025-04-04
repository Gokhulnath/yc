import os


def get_db_params_from_env():
    """Get database connection parameters from environment variables"""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'port': os.getenv('DB_PORT', '5432')
    }