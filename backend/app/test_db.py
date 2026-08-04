from app.db.database import engine

try:
    connection = engine.connect()
    print("Connected!")
    connection.close()
except Exception as e:
    print(e)
