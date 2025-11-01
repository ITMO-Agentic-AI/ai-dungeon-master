class VectorStoreService:
    def __init__(self):
        self.store = None

    async def initialize_chroma(self):
        pass

    async def search(self, query: str, k: int = 5):
        pass

    async def add_documents(self, documents: list):
        pass


vector_store_service = VectorStoreService()
