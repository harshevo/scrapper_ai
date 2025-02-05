import firebase_admin
from firebase_admin import credentials, firestore


cred = credentials.Certificate("./getstrollr-46a44d10fddf.json")


class db:
    __db = None
    __initialized = False

    def __init__(self):
        if not db.__initialized:
            firebase_admin.initialize_app(cred, name="default")
            db.__initialized = True
        self.__db = firestore.client()
        print("connected to firestore")

    # async def add_data(self, collection_name, data_name, data):
    #     try:
    #         if self.__db:
    #             doc_ref = self.__db.collection(collection_name).document(data_name)
    #             print(f"db_doc_ref ==> {doc_ref}")
    #             doc_ref.set(data)
    #             print("data added successfully")
    #         else:
    #             print("error adding data to firestore")
    #     except Exception as e:
    #         print(f"Error adding data {e}")

    async def add_data(self, collection_name: str, data: dict) -> bool:
        """Add new data as a separate document to a Firestore collection.

        Args:
            collection_name: Name of the collection
            data: Dictionary containing the document data

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.__db:
            return False

        try:
            self.__db.collection(collection_name).add(data)
            return True

        except Exception as e:
            print(f"Unexpected error: {e}")
            return False
