from mongo_handler import MongoHandler
from dotenv import load_dotenv
from os import getenv
import re
import bcrypt

class Users:
    def __init__(self):
        load_dotenv()
        username = getenv("MONGO_USER")
        password = getenv("MONGO_PASS")
        cluster = getenv("MONGO_CLUSTER")
        mongo_atlas = getenv("MONGO_ATLAS", "false").lower() == "true"
        self._mongo = MongoHandler(username, password, cluster, mongo_atlas)
        self._mongo.connect()

class RegularUsers(Users):
    def __init__(self):
        super().__init__()
        self._mongo.set_database("users")
        self._mongo.set_collection("regular_users")

    def create_user(self, username: str,  email: str, password: str):
        pattern = r"^([a-z\d\.-]+)@([a-z\d-]+)\.([a-z]{2,8})(\.[a-z]{2,8})?$"
        if re.match(pattern, email) is None:
            raise ValueError("E-mail inválido!")
        pattern = r"^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[a-zA-Z]).{8,}$"
        if re.match(pattern, password) is None:
            raise ValueError("Senha muito fraca!")
        if self._mongo.find_one({"username": username}):
            raise ValueError("Usuário já existe!")
        password = RegularUsers.hash_password(password)
        user = {
            "username": username,
            "email": email,
            "password": password
        }
        self._mongo.insert_one(user)

    def get_user(self, username: str) -> dict:
        user = self._mongo.find_one({"username": username})
        if user:
            return user
        return {}

    def get_all_users(self, limit: int = 0):
        return self._mongo.find_many({}, limit)

    def update_user(self, username: str, update_data: dict):
        if not any(key.startswith("$") for key in update_data.keys()):
            update_data = {"$set": update_data}
        result = self._mongo.update_one({"username": username}, update_data)
        return result

    def delete_user(self, username: str):
        result = self._mongo.delete_one({"username": username})
        return result

    @staticmethod
    def hash_password(password:str) -> str:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

class FakeUsers(Users):
    def __init__(self):
        super().__init__()
        self._mongo.set_database("users")
        self._mongo.set_collection("fake_users")

    def create_user(self, main_user:str, username: str,  email: str, password: str):
        result = self._mongo.aggregate([
            {
                "$lookup": {
                    "from": "regular_users",
                    "localField": "username",
                    "foreignField": "username",
                    "as": "match"
                }
            },
            {
                "$match": { "match": { "$ne": [] } }
            }
        ])
        print(result)
        pattern = r"^([a-z\d\.-]+)@([a-z\d-]+)\.([a-z]{2,8})(\.[a-z]{2,8})?$"
        if re.match(pattern, email) is None:
            raise ValueError("E-mail inválido!")
        pattern = r"^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[a-zA-Z]).{8,}$"
        if re.match(pattern, password) is None:
            raise ValueError("Senha muito fraca!")
        if self._mongo.find_one({"username": username}):
            raise ValueError("Usuário já existe!")
        password = RegularUsers.hash_password(password)
        user = {
            "username": username,
            "email": email,
            "password": password
        }
        self._mongo.insert_one(user)
