import os
import io
import unittest
from backend.app import app as flask_app
from backend.utils import disease_knowledge

class Phase2Tests(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()

    def test_knowledge_base_coverage(self):
        kb = disease_knowledge.load_knowledge_base()
        self.assertIsInstance(kb, dict)
        self.assertEqual(len(kb), 38)
        required = {"class_name", "display_name", "crop", "description", "symptoms", "possible_causes", "prevention", "care_recommendations", "safe_treatment"}
        for entry in kb.values():
            self.assertTrue(required.issubset(entry.keys()))

    def test_get_disease_info_known(self):
        info = disease_knowledge.get_disease_info("Apple___Apple_scab", confidence=95.0, user_crop="Apple")
        self.assertEqual(info["class_name"], "Apple___Apple_scab")
        self.assertFalse(info["is_healthy"])
        self.assertFalse(info["is_uncertain"])
        self.assertTrue(info["is_crop_compatible"])
        self.assertIn("description", info)
        self.assertIn("symptoms", info)
        self.assertIsInstance(info["symptoms"], list)

    def test_get_disease_info_healthy(self):
        info = disease_knowledge.get_disease_info("Apple___healthy", confidence=99.0, user_crop="Apple")
        self.assertTrue(info["is_healthy"])
        self.assertEqual(info["category"], "healthy")
        self.assertFalse(info["is_uncertain"])

    def test_get_disease_info_unknown(self):
        info = disease_knowledge.get_disease_info("Unknown___disease", confidence=50.0, user_crop="Rice")
        self.assertEqual(info["category"], "unknown")
        self.assertTrue(info["is_uncertain"])
        self.assertFalse(info["is_crop_compatible"])

    def test_predict_endpoint(self):
        img_path = os.path.join('backend', 'test_leaf.jpg')
        with open(img_path, 'rb') as img:
            data = {'image': (io.BytesIO(img.read()), 'test_leaf.jpg')}
            response = self.client.post('/api/disease/predict', content_type='multipart/form-data', data=data)
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data["status"], "success")
        self.assertIn("knowledge", json_data)
        self.assertIn("description", json_data["knowledge"])

    def test_recommend_endpoint_mismatch(self):
        payload = {
            "prediction": {"class_name": "Apple___Apple_scab", "confidence": 85.0},
            "answers": {"plant": "Tomato", "symptoms": "brown spots", "duration": "2 days", "spread": "many plants"}
        }
        response = self.client.post('/api/disease/recommend', json=payload)
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data["status"], "success")
        knowledge = json_data.get("knowledge")
        self.assertIsNotNone(knowledge)
        self.assertFalse(knowledge["is_crop_compatible"])

    def test_recommend_endpoint_low_confidence(self):
        payload = {
            "prediction": {"class_name": "Apple___Apple_scab", "confidence": 30.0},
            "answers": {"plant": "Apple", "symptoms": "brown spots", "duration": "2 days", "spread": "one leaf"}
        }
        response = self.client.post('/api/disease/recommend', json=payload)
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        knowledge = json_data.get("knowledge")
        self.assertTrue(knowledge["is_uncertain"])
