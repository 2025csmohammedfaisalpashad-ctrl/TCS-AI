from database.mongodb import test_mongodb_connection


if __name__ == "__main__":
    try:
        test_mongodb_connection()
        print("MongoDB connection successful!")
    except Exception as e:
        print("MongoDB connection failed:")
        print(e)