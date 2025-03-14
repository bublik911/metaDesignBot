import os
import peewee_async
from dotenv import load_dotenv

load_dotenv()

db = peewee_async.PooledMySQLDatabase(
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    host=os.getenv('DB_HOST'),
    password=os.getenv('DB_PASSWORD', default='')
)


