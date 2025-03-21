from mongo_handler import MongoHandler
import re
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from bson import ObjectId

cipher = Fernet
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
        return self._mongo.find_one({"username": username})

    def get_user_by_id(self, id: str) -> dict:
        return self._mongo.find_one({"_id": ObjectId(id)})

    def delete_user(self, username: str):
        result = self._mongo.delete_one({"username": username})
        return result

    def delete_user_by_id(self, id: str):
        result = self._mongo.delete_one({"_id": ObjectId(id)})
        return result

    @staticmethod
    def hash_password(password:str) -> str:
        digest = hashes.Hash(hashes.SHA256())
        digest.update(password.encode())
        return digest.finalize().hex()

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
            new_hashed_password = hashed_password(password)
            return new_hashed_password == hashed_password
    
    @staticmethod
    def encrypt_password(password: str, key: str):
        cipher = Fernet(key.encode())
        return cipher.encrypt(password.encode()).decode()
    
    @staticmethod
    def decrypt_password(password: str, key: str):
        cipher = Fernet(key.encode())
        return cipher.decrypt(password).decode()

class RegularUser(Users):
    def __init__(self, mongo_handler: MongoHandler, database: str=None, collection: str=None):
        super().__init__(mongo_handler)
        if database is not None:
            self._mongo.set_database(database)
        if collection is not None:
            self._mongo.set_collection(collection)

    def create_user(self, username: str,  email: str, password: str) -> dict:
        if re.match(r"^([a-z\d\.-]+)@([a-z\d-]+)\.([a-z]{2,8})(\.[a-z]{2,8})?$", email) is None:
            raise ValueError("E-mail inválido!")
        if self.get_user(username) != {}:
            raise ValueError("Usuário já existe!")
        if not password or password.isspace():
            raise ValueError("Senha inválida!")
        value = self._mongo.insert_one({
            "username": username,
            "email": email,
            "password": f"{Users.hash_password(password)}"
        })
        return value

    def update_user(self, username: str, update_data: dict):
        dict_structure = {"username", "email", "password"}
        if not any(key.startswith("$") for key in update_data.keys()):
            update_data = {"$set": update_data}
        invalid_keys = set(update_data.keys()) - dict_structure
        if invalid_keys:
            raise ValueError(f"Campos inválidos detectados: {invalid_keys}")
        if re.match(r"^([a-z\d\.-]+)@([a-z\d-]+)\.([a-z]{2,8})(\.[a-z]{2,8})?$", update_data["email"]) is None:
            raise ValueError("E-mail inválido!")
        if not update_data["password"] or update_data["password"].isspace():
            raise ValueError("Senha inválida!")
        result = self._mongo.update_one({"username": username}, update_data)
        return result

    def valid_user(self, username: str, password: str):
        value = self._mongo.find_one(username)
        if value["password"] == password:
            return True
        return False

class FakeUser(Users):
    def __init__(self, mongo_handler: MongoHandler, database: str=None, collection:str=None, main_user_database:str=None, main_user_collection: str=None):
        super().__init__(mongo_handler)
        self.database:str = None
        self.collection:str = None
        self.main_user_collection:str = None
        if database is not None:
            self._mongo.set_database(database)
            self.database = database
        if collection is not None:
            self._mongo.set_collection(collection)
            self.collection = collection
        if main_user_database is not None:
            self.main_user_database = main_user_database
        else:
            self.main_user_database = database
        if main_user_collection is not None:
            self.main_user_collection = main_user_collection

    def create_user(self, main_user: str, username: str,  email: str, password: str, desc:str=""):
        if self.database is None or self.collection is None or self.main_user_collection is None:
            raise ConnectionError(f"Algum dado de conexão importante não foi fornecido!\nDatabase = {self.database}, Collection = {self.collection}, MainUserCollection = {self.collection}")
        self._mongo.set_database(self.main_user_database)
        self._mongo.set_collection(self.main_user_collection)
        if self.get_user(main_user) == {}:
            raise ValueError("Usuário referido não existe!")
        self._mongo.set_database(self.database)
        self._mongo.set_collection(self.collection)
        if not username or username.isspace():
            raise ValueError("Nome de usuário inválido!")
        if re.match(r"^([a-z\d\.-]+)@([a-z\d-]+)\.([a-z]{2,8})(\.[a-z]{2,8})?$", email) is None:
            raise ValueError("E-mail inválido!")
        if not password or password.isspace():
            raise ValueError("Senha inválida!")
        value = self._mongo.insert_one({
            "main_user": main_user,
            "username": username,
            "email": email,
            "password": password,
            "desc": desc
        })
        return value

    def set_database(self, database:str):
        self._mongo.set_database(database)
        self.database = database

    def set_collection(self, collection:str):
        self._mongo.set_collection(collection)
        self.collection = collection

    def set_main_user_database(self, database:str):
        self.main_user_database = database

    def set_main_user_collection(self, collection:str):
        self.main_user_collection = collection

    def get_all_users(self, limit: int = 0):
        if self.get_database() is None or self.get_collection() is None:
            raise ConnectionError("Database ou Document não foi definido!")
        return self._mongo.find_many({}, limit)

    def get_main_user_database(self) -> str:
        return self.main_user_database

    def get_main_user_collection(self) -> str:
        return self.main_user_collection

    def update_user(self, id: str, update_data: dict):
        dict_structure = {"_id", "username", "email", "password"}
        if not any(key.startswith("$") for key in update_data.keys()):
            update_data = {"$set": update_data}
        invalid_keys = set(update_data.keys()) - dict_structure
        if invalid_keys:
            raise ValueError(f"Campos inválidos detectados: {invalid_keys}")
        if re.match(r"^([a-z\d\.-]+)@([a-z\d-]+)\.([a-z]{2,8})(\.[a-z]{2,8})?$", update_data["email"]) is None:
            raise ValueError("E-mail inválido!")
        if not update_data["password"] or update_data["password"].isspace():
            raise ValueError("Senha inválida!")
        result = self._mongo.update_one({"_id": ObjectId(id)}, update_data)
        return result


import dotenv
import os

dotenv.load_dotenv()

database = MongoHandler()
database.set_username(os.getenv("MONGO_USER"))
database.set_password(os.getenv("MONGO_PASS"))
database.set_cluster(os.getenv("MONGO_CLUSTER"))
database.set_atlas(True)
database.connect()
database.set_database("users")
database.set_collection("regular_users")