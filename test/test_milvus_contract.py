import inspect
import unittest

from pymilvus import MilvusClient


class MilvusSDKContractTest(unittest.TestCase):
    def test_required_milvus_client_methods_exist(self):
        for method in ("has_collection", "create_collection", "upsert", "search", "close"):
            self.assertTrue(hasattr(MilvusClient, method), method)

    def test_create_collection_contract(self):
        parameters = inspect.signature(MilvusClient.create_collection).parameters
        for name in (
            "collection_name",
            "dimension",
            "primary_field_name",
            "id_type",
            "vector_field_name",
            "metric_type",
            "auto_id",
        ):
            self.assertIn(name, parameters)

    def test_vector_operation_contract(self):
        search_parameters = inspect.signature(MilvusClient.search).parameters
        upsert_parameters = inspect.signature(MilvusClient.upsert).parameters
        self.assertIn("collection_name", search_parameters)
        self.assertIn("data", search_parameters)
        self.assertIn("output_fields", search_parameters)
        self.assertIn("collection_name", upsert_parameters)
        self.assertIn("data", upsert_parameters)


if __name__ == "__main__":
    unittest.main()
