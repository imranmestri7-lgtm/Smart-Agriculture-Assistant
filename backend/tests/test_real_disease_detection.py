import io
import os
import unittest
from backend.app import app as flask_app
from utils.auth_tokens import create_access_token


class RealDiseaseDetectionTests(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        self.token = create_access_token(user_id=1)
        self.test_img_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "test_leaf.jpg"
        )

    def test_predict_real_image(self):
        """Verify that a real image is evaluated by the model and returns structured results."""
        self.assertTrue(os.path.isfile(self.test_img_path), "test_leaf.jpg must exist")

        with open(self.test_img_path, "rb") as f:
            data = {"image": (io.BytesIO(f.read()), "test_leaf.jpg")}
            response = self.client.post(
                "/api/disease/predict",
                content_type="multipart/form-data",
                data=data
            )

        self.assertEqual(response.status_code, 200)
        res = response.get_json()
        self.assertEqual(res["status"], "success")

        # Prediction details
        pred = res["prediction"]
        self.assertIn("class_name", pred)
        self.assertIn("crop_name", pred)
        self.assertIn("disease_name", pred)
        self.assertIn("is_healthy", pred)
        self.assertIn("confidence", pred)

        confidence = pred["confidence"]
        self.assertIsInstance(confidence, (int, float))
        self.assertGreater(confidence, 0.0)
        self.assertLessEqual(confidence, 100.0)

        # Knowledge details
        knowledge = res.get("knowledge", {})
        self.assertIn("crop", knowledge)
        self.assertIn("display_name", knowledge)
        self.assertIn("symptoms", knowledge)
        self.assertIn("possible_causes", knowledge)
        self.assertIn("safe_treatment", knowledge)
        self.assertIn("prevention", knowledge)
        self.assertIsInstance(knowledge["symptoms"], list)

        # Top candidate predictions
        top_preds = res.get("top_predictions", [])
        self.assertEqual(len(top_preds), 3)

    def test_predict_authenticated_saves_history(self):
        """Verify that authenticated requests record diagnosis history."""
        with open(self.test_img_path, "rb") as f:
            data = {"image": (io.BytesIO(f.read()), "test_leaf.jpg")}
            response = self.client.post(
                "/api/disease/predict",
                content_type="multipart/form-data",
                data=data,
                headers={"Authorization": f"Bearer {self.token}"}
            )

        self.assertEqual(response.status_code, 200)
        res = response.get_json()
        self.assertEqual(res["status"], "success")
        self.assertTrue(res.get("history_saved"))

    def test_predict_missing_image(self):
        """Verify 400 when no image is provided."""
        response = self.client.post(
            "/api/disease/predict",
            content_type="multipart/form-data",
            data={}
        )
        self.assertEqual(response.status_code, 400)
        res = response.get_json()
        self.assertEqual(res["status"], "error")

    def test_predict_invalid_extension(self):
        """Verify 400 when an invalid file extension is uploaded."""
        data = {"image": (io.BytesIO(b"dummy data"), "test_file.txt")}
        response = self.client.post(
            "/api/disease/predict",
            content_type="multipart/form-data",
            data=data
        )
        self.assertEqual(response.status_code, 400)
        res = response.get_json()
        self.assertEqual(res["status"], "error")

    def test_predict_corrupted_image(self):
        """Verify 400 when an image file is corrupted or not a valid image."""
        data = {"image": (io.BytesIO(b"not a valid image content"), "corrupt.jpg")}
        response = self.client.post(
            "/api/disease/predict",
            content_type="multipart/form-data",
            data=data
        )
        self.assertEqual(response.status_code, 400)
        res = response.get_json()
        self.assertEqual(res["status"], "error")

    def test_disease_info_endpoint(self):
        """Verify the class info endpoint returns structured knowledge."""
        response = self.client.get("/api/disease/info/Tomato___Early_blight")
        self.assertEqual(response.status_code, 200)
        res = response.get_json()
        self.assertEqual(res["status"], "success")
        self.assertIn("knowledge", res)
        self.assertEqual(res["knowledge"]["crop"], "Tomato")

    def test_disease_info_marathi_translation(self):
        """Verify that language headers return translated disease knowledge."""
        response = self.client.get(
            "/api/disease/info/Tomato___Early_blight",
            headers={"X-Language": "mr"}
        )
        self.assertEqual(response.status_code, 200)
        res = response.get_json()
        self.assertEqual(res["status"], "success")
        kn = res["knowledge"]
        self.assertEqual(kn["display_name"], "टॉमॅटो प्रारंभिक ब्लाइट")


if __name__ == "__main__":
    unittest.main()
