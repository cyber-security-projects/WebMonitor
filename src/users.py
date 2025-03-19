from mongo_handler import MongoHandler
import re
import bcrypt

class Users:
    def __init__(self, mongo_handler: MongoHandler):
        self._mongo = mongo_handler
        self._mongo.connect()
    
    def set_database(self, database:str):
        self._mongo.set_database(database)
    
    def get_database(self) -> str:
        return self._mongo.get_database()
    
    def set_collection(self, collection:str):
        self._mongo.set_collection(collection)
    
    def get_collection(self) -> str:
        return self._mongo.get_collection()

    def get_user(self, username: str) -> dict:
        user = self._mongo.find_one({"username": username})
        if user:
            return user
        return {}

    def get_all_users(self, limit: int = 0):
        return self._mongo.find_many({}, limit)

    @staticmethod
    def hash_password(password:str) -> str:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

class RegularUser(Users):
    def __init__(self, mongo_handler: MongoHandler, database: str=None, collection: str=None):
        super().__init__(mongo_handler)
        if database is not None:
            self.set_database(database)
        if collection is not None:
            self.set_collection(collection)

    def create_user(self, username: str,  email: str, password: str):
        if re.match(r"^([a-z\d\.-]+)@([a-z\d-]+)\.([a-z]{2,8})(\.[a-z]{2,8})?$", email) is None:
            raise ValueError("E-mail inválido!")
        if self.get_user(username) != {}:
            raise ValueError("Usuário já existe!")
        if not password or password.isspace():
            raise ValueError("Senha inválida!")
        password = Users.hash_password(password)
        self._mongo.insert_one({
            "username": username,
            "email": email,
            "password": password
        })

    def update_user(self, username: str, update_data: dict):
        if not any(key.startswith("$") for key in update_data.keys()):
            update_data = {"$set": update_data}
        if re.match(r"^([a-z\d\.-]+)@([a-z\d-]+)\.([a-z]{2,8})(\.[a-z]{2,8})?$", update_data["email"]) is None:
            raise ValueError("E-mail inválido!")
        # Continuar daqui caraio
        if not update_data["password"] or update_data["password"].isspace():
            raise ValueError("Senha inválida!")
        result = self._mongo.update_one({"username": username}, update_data)
        return result

    def delete_user(self, username: str):
        result = self._mongo.delete_one({"username": username})
        return result

class FakeUser(Users):
    def __init__(self, mongo_handler: MongoHandler, database: str=None, collection:str=None, regular_user_database:str=None, regular_user_collection: str=None):
        super().__init__(mongo_handler)
        if database is not None:
            self._mongo.set_database(database)
            self.database = database
        if collection is not None:
            self._mongo.set_collection(collection)
            self.collection = collection
        if regular_user_database is not None:
            self.regular_user_database = regular_user_database
        else:
            self.regular_user_database = database
        if regular_user_collection is not None:
            self.regular_user_collection = regular_user_collection

    def create_user(self, username: str,  email: str, password: str, desc:str=""):
        if re.match(r"^([a-z\d\.-]+)@([a-z\d-]+)\.([a-z]{2,8})(\.[a-z]{2,8})?$", email) is None:
            raise ValueError("E-mail inválido!")
        self.set_database(self.regular_user_database)
        self.set_collection(self.regular_user_collection)
        if self.get_user(username) == {}:
            raise ValueError("Usuário referido não existe!")
        self.set_database(self.database)
        self.set_collection(self.collection)
        if not password or password.isspace():
            raise ValueError("Senha inválida!")
        self._mongo.insert_one({
            "username": username,
            "email": email,
            "password": password,
            "desc": desc
        })

import os
import dotenv

dotenv.load_dotenv()
mongo_handler = MongoHandler(mongo_atlas=True)
mongo_handler.set_username(os.getenv("MONGO_USER"))
mongo_handler.set_password(os.getenv("MONGO_PASS"))
mongo_handler.set_cluster(os.getenv("MONGO_CLUSTER"))
regular_user = RegularUser(mongo_handler, "users", "regular_users")
fake_user = FakeUser(mongo_handler, database="users", collection="fake_users", regular_user_collection="regular_users")
# users.create_user("Marcos_Miotto", "marcos@miotto.com", "@Senha123")
# fake_user = FakeUsers(mongo_handler, "fake_users", )
# fake_user.create_user("regular_users", "Marcos-Miotto", "marcos", "marcos@marcos.com", "Senha123")
