from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError
from pymongo.server_api import ServerApi
import re

class MongoHandler:
    URI = None
    def __init__(self, username:str=None, password:str=None, cluster:str=None, mongo_atlas:bool=False, database:str=None, collection:str=None):
        self.__client = MongoClient()
        self.__username = None
        self.__password = None
        self.__cluster = None
        self.__database = None
        self.__collection = None
        self.__mongo_atlas = mongo_atlas
        validations = {
            "username": (username, MongoHandler.is_valid_username, "Username inválido!"),
            "password": (password, MongoHandler.is_valid_password, "Senha inválida!"),
            "cluster": (cluster, MongoHandler.is_valid_cluster, "Mongo Cluster inválido!"),
            "database": (database, MongoHandler.is_valid_database, "Nome de banco inválido!"),
            "collection": (collection, MongoHandler.is_valid_cluster, "Nome de coleção inválido!")
        }
        for attr, (value, validator, error_msg) in validations.items():
            if value is not None:
                if not validator(value):
                    raise ValueError(error_msg)
                setattr(self, f"_{self.__class__.__name__}__{attr}", value)

    def set_username(self, username:str = None):
        if MongoHandler.is_valid_username(username):
            self.__username = username

    def get_username(self) -> str:
        return self.__username

    def set_password(self, password:str):
        if MongoHandler.is_valid_password(password):
            self.__password = password

    def get_password(self) -> str:
        return self.__password

    def set_cluster(self, cluster:str):
        if MongoHandler.is_valid_cluster(cluster):
            self.__cluster = cluster

    def get_cluster(self) -> str:
        return self.__cluster
    
    def set_atlas(self, atlas:bool):
        self.__mongo_atlas = atlas

    def is_atlas(self) -> bool:
        return self.__mongo_atlas

    def set_database(self, database:str):
        if MongoHandler.is_valid_database(database):
            self.__database = database

    def get_database(self) -> str:
        return self.__database

    def set_collection(self, collection:str):
        if MongoHandler.is_valid_collection(collection):
            self.__collection = collection

    def get_collection(self) -> str:
        return self.__collection

    def connect(self):
        if None in [self.__username, self.__password, self.__cluster]:
            raise ConnectionError("Não é possível iniciar conexão com o banco pois algum parâmetro essencial não foi passado!")
        self.URI = "mongodb+srv://" if self.__mongo_atlas else "mongodb://"
        self.URI += f"{self.__username}:{self.__password}@{self.__cluster}/?retryWrites=true&w=majority&appName=WebMonitor"
        try:
            self.__client = MongoClient(self.URI, serverSelectionTimeoutMS=5000)
            self.__ping()
        except OperationFailure as e:
            raise ConnectionError(f"Erro de autenticação: {e.details.get('errmsg', 'Credenciais inválidas')}")
        except ConnectionError:
            raise ConnectionError("Erro de conexão: Não foi possível alcançar o servidor MongoDB.")
        except Exception as e:
            raise ConnectionError(f"Erro inesperado ao conectar ao MongoDB: {str(e)}")

    def disconnect(self):
        if self.__client:
            self.__client.close()
            self.URI = None

    def insert_one(self, value:dict):
        if self.URI is None:
            raise ConnectionError("Não há conexão ativa")
        if None in [self.__database, self.__collection]:
            raise ValueError("Não foi definido banco ou coleção para inserção!")
        if value == {}:
            raise ValueError("Nenhum valor para ser adicionado!")
        try:
            result = self.__client.get_database(self.__database)[self.__collection].insert_one(value)
            response = {
                "_id": result.inserted_id
            }
            for key in value.keys():
                response[key] = value[key]
            return {"message": "Documento inserido com sucesso!", "value": response}
        except PyMongoError as e:
            raise RuntimeError(f"Erro ao inserir documento: {str(e)}")

    def find_one(self, query: dict) -> dict:
        if self.URI is None:
            raise ConnectionError("Não há conexão ativa")
        if None in [self.__database, self.__collection]:
            raise ValueError("Não foi definido banco ou coleção para procura!")
        try:
            result = self.__client.get_database(self.__database)[self.__collection].find_one(query)
            return result if result is not None else {}
        except PyMongoError as e:
            raise RuntimeError(f"Erro ao encontrar documento: {str(e)}")

    def update_one(self, query: dict, update: dict):
        if self.URI is None:
            raise ConnectionError("Não há conexão ativa")
        if None in [self.__database, self.__collection]:
            raise ValueError("Não foi definido banco ou coleção para atualização!")
        if not any(key.startswith("$") for key in update.keys()):
            raise ValueError("O dicionário de atualização deve conter pelo menos um operador `$`, tente usar {$set: {update}}!")
        try:
            result = self.__client[self.__database][self.__collection].update_one(query, update)
            if result.matched_count == 0:
                return {"message": "Nenhum documento encontrado para atualizar.", "modified": 0}
            return {"message": "Documento atualizado com sucesso!", "modified": result.modified_count}
        except PyMongoError as e:
            raise RuntimeError(f"Erro ao atualizar documento: {str(e)}")

    def delete_one(self, query: dict):
        if self.URI is None:
            raise ConnectionError("Não há conexão ativa")
        if None in [self.__database, self.__collection]:
            raise ValueError("Não foi definido banco ou coleção para remoção!")
        try:
            result = self.__client[self.__database][self.__collection].delete_one(query)
            if result.deleted_count == 0:
                return {"message": "Nenhum documento encontrado para deletar", "deleted": 0}
            return {"message": "Documento deletado com sucesso!", "deleted": result.deleted_count}
        except PyMongoError as e:
            raise RuntimeError(f"Erro ao deletar documento: {str(e)}")

    def insert_many(self, documents: list):
        if self.URI is None:
            raise ConnectionError("Não há conexão ativa")
        if None in [self.__database, self.__collection]:
            raise ValueError("Não foi definido banco ou coleção para inserção!")
        if not isinstance(documents, list) or not all(isinstance(doc, dict) for doc in documents):
            raise ValueError("Os documentos devem ser fornecidos em uma lista de dicionários")
        if documents == [] or {} in documents:
            raise ValueError("A lista ou algum valor da lista está vazio")
        try:
            result = self.__client[self.__database][self.__collection].insert_many(documents)
            return {"message": "Documentos inseridos com sucesso!", "inserted": len(result.inserted_ids)}
        except PyMongoError as e:
            raise RuntimeError(f"Erro ao inserir documentos: {str(e)}")

    def find_many(self, query: dict, limit: int = 0):
        if self.URI is None:
            raise ConnectionError("Não há conexão ativa")
        if None in [self.__database, self.__collection]:
            raise ValueError("Não foi definido banco ou coleção para procura!")
        try:
            results = self.__client[self.__database][self.__collection].find(query).limit(limit)
            return list(results)
        except PyMongoError as e:
            raise RuntimeError(f"Erro ao buscar documentos: {str(e)}")

    def update_many(self, query: dict, update: dict):
        if self.URI is None:
            raise ConnectionError("Não há conexão ativa")
        if None in [self.__database, self.__collection]:
            raise ValueError("Não foi definido banco ou coleção para atualização!")
        if not any(key.startswith("$") for key in update.keys()):
            raise ValueError("O dicionário de atualização deve conter pelo menos um operador `$`, tente usar {$set: {update}}!")
        if update == [] or {} in update:
            raise ValueError("A lista ou algum valor da lista está vazio")
        try:
            result = self.__client[self.__database][self.__collection].update_many(query, update)
            return {"message": "Documentos atualizados com sucesso!", "modified": result.modified_count}
        except PyMongoError as e:
            raise RuntimeError(f"Erro ao atualizar documentos: {str(e)}")

    def delete_many(self, query: dict):
        if self.URI is None:
            raise ConnectionError("Não há conexão ativa")
        if None in [self.__database, self.__collection]:
            raise ValueError("Não foi definido banco ou coleção para atualização!")
        try:
            result = self.__client[self.__database][self.__collection].delete_many(query)
            return {"message": "Documentos deletados com sucesso!", "deleted": result.deleted_count}
        except PyMongoError as e:
            raise RuntimeError(f"Erro ao deletar documentos: {str(e)}")

    def aggregate(self, pipeline: list):
        if self.URI is None:
            raise ConnectionError("Não há conexão ativa")
        if None in [self.__database, self.__collection]:
            raise ValueError("Não foi definido banco ou coleção para agragação!")
        if not isinstance(pipeline, list):
            raise ValueError("O pipeline de agregação deve ser uma lista de estágios")
        try:
            results = self.__client[self.__database][self.__collection].aggregate(pipeline)
            return list(results)
        except PyMongoError as e:
            raise RuntimeError(f"Erro ao executar agregação: {str(e)}")

    @staticmethod
    def is_valid_username(username: str) -> bool:
        if not username or username.isspace():
            return False
        pattern = r"^(?![_.-])(?!.*[_.-]{2})[a-zA-Z0-9._-]{3,30}(?<![_.-])$"
        return bool(re.match(pattern, username))

    @staticmethod
    def is_valid_password(password: str) -> bool:
        return bool(password and password.strip())

    @staticmethod
    def is_valid_cluster(cluster:str) -> bool:
        pattern = r"^([\w.-]+|\[[a-fA-F0-9:]+\])(,([\w.-]+|\[[a-fA-F0-9:]+\]))*$"
        return re.match(pattern, cluster) is not None

    @staticmethod
    def is_valid_database(database: str) -> bool:
        if not database or database.isspace():
            return False
        pattern = r"^[a-zA-Z0-9._]{1,64}$"
        reserved_db_names = {"admin", "local", "config"}
        return bool(re.match(pattern, database)) and database not in reserved_db_names

    @staticmethod
    def is_valid_collection(collection: str) -> bool:
        if not collection or collection.isspace():
            return False
        pattern = r"^(?!system\.)([\w.]{1,120})$"
        return bool(re.match(pattern, collection))

    def __ping(self):
        client = MongoClient(self.URI, server_api=ServerApi('1'))
        client.admin.command('ping')
