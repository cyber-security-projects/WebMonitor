from mongo_handler import MongoHandler
from dotenv import load_dotenv
from os import getenv
import re
import bcrypt

class RegularUsers:
    def __init__(self):
        load_dotenv()
        username = getenv("MONGO_USER")
        password = getenv("MONGO_PASS")
        cluster = getenv("MONGO_CLUSTER")
        mongo_atlas = getenv("MONGO_ATLAS", "false").lower() == "true"
        self._mongo = MongoHandler(username, password, cluster, mongo_atlas)
        self._mongo.set_database("users")
        self._mongo.set_collection("users")
        self._mongo.connect()

    def create_user(self, username: str,  email: str, password: str):
        if self.__class__.__name__ != "RegularUsers":
            raise NotImplementedError("Este método não pode ser implementado por outras classes")
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

class FakeUsers(RegularUsers):
    def __init__(self):
        super().__init__()
        self._mongo.set_collection("fake_identities")

    def create_fake_user(self, main_user: str, platform: str, username: str, email: str, password: str):
        password = RegularUsers.hash_password(password)
        fake_identity = {
            "main_user": main_user,  # Relaciona ao usuário principal
            "username": username,
            "email": email,
            "password": password
        }
        self._mongo.insert_one(fake_identity)
        return {"message": "Identidade falsa criada com sucesso!"}

FakeUsers().create_user("fadsf", "daf", "fasdf")