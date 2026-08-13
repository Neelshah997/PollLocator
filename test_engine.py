import sys
import unittest
import json
import traceback

sys.path.append('.')
from app import app
from database.models import User, Division, Subdivision, Feeder, Transformer, Pole

class PollLocatorTestEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up isolated test hierarchy and test client."""
        cls.app = app
        cls.client = app.test_client()
        cls.app_context = app.app_context()
        cls.app_context.push()

        cls.TEST_PREFIX = "ENGINE_TEST_"
        print("\n=== [TEST ENGINE STARTED] Initializing test fixtures ===")

        # Create isolated test hierarchy
        cls.division = Division(name=f"{cls.TEST_PREFIX}DIV").save()
        cls.subdivision = Subdivision(name=f"{cls.TEST_PREFIX}SUBDIV", division=cls.division).save()
        cls.feeder = Feeder(name=f"{cls.TEST_PREFIX}FEEDER", subdivision=cls.subdivision).save()
        print(f"  Created test hierarchy: Feeder ID = {cls.feeder.id}")

    @classmethod
    def tearDownClass(cls):
        """Clean up all test data created during testing."""
        print("\n=== [TEARDOWN] Cleaning up all test seed data from MongoDB Atlas ===")
        try:
            # Delete test poles
            test_tcs = Transformer.objects(tc_number__startswith=cls.TEST_PREFIX)
            test_tc_ids = [t.id for t in test_tcs]
            Pole.objects(tc__in=test_tc_ids).delete()
            Pole.objects(pole_number__startswith=cls.TEST_PREFIX).delete()

            # Delete test transformers
            Transformer.objects(tc_number__startswith=cls.TEST_PREFIX).delete()

            # Delete test hierarchy
            Feeder.objects(name__startswith=cls.TEST_PREFIX).delete()
            Subdivision.objects(name__startswith=cls.TEST_PREFIX).delete()
            Division.objects(name__startswith=cls.TEST_PREFIX).delete()
            print("  [TEARDOWN COMPLETED] All seed data successfully removed from DB!")
        except Exception as e:
            print(f"  [TEARDOWN WARNING] Error during cleanup: {e}")
        finally:
            cls.app_context.pop()

    # --- TRANSFORMER ENDPOINT TESTS ---

    def test_01_transformer_online_mode_create(self):
        """Test creating a Transformer in Online mode using Feeder ObjectId."""
        tc_num = f"{self.TEST_PREFIX}TC_ONLINE_001"
        payload = {
            "tc_number": tc_num,
            "tc_name": "Online Transformer 1",
            "feeder_id": str(self.feeder.id),
            "lat": 23.0225,
            "long": 72.5714,
            "capacity": "100KVA"
        }
        response = self.client.post('/transformer', json=payload)
        self.assertIn(response.status_code, [200, 201])
        data = response.get_json()
        self.assertIn("tc_id", data)
        self.assertEqual(data.get("tc", {}).get("tc_number"), tc_num)
        print("  [PASSED] Transformer Online Creation")

    def test_02_transformer_offline_mode_tc_number(self):
        """Test creating & querying a Transformer using string TC Number."""
        tc_num = f"{self.TEST_PREFIX}TC_OFFLINE_8231456"
        payload = {
            "tc_number": tc_num,
            "tc_name": "Offline Transformer 8231456",
            "feeder_id": str(self.feeder.id),
            "lat": 23.0500,
            "long": 72.5800,
            "capacity": "63KVA"
        }
        response = self.client.post('/transformer', json=payload)
        self.assertIn(response.status_code, [200, 201])
        
        # Test Query by TC Number string
        get_res = self.client.get(f'/transformer?tc_id={tc_num}')
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.get_json().get("tc", {}).get("tc_number"), tc_num)
        print("  [PASSED] Transformer Offline TC Number Handling")

    def test_03_transformer_upsert_resubmission(self):
        """Test Transformer Upsert / Idempotent resubmission."""
        tc_num = f"{self.TEST_PREFIX}TC_UPSERT_001"
        payload = {
            "tc_number": tc_num,
            "tc_name": "Initial Name",
            "feeder_id": str(self.feeder.id),
            "lat": 23.0000,
            "long": 72.0000
        }
        res1 = self.client.post('/transformer', json=payload)
        self.assertEqual(res1.status_code, 201)
        tc_id1 = res1.get_json().get("tc_id")

        # Resubmit with updated capacity & name
        payload["tc_name"] = "Updated Name"
        payload["capacity"] = "200KVA"
        res2 = self.client.post('/transformer', json=payload)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertEqual(data2.get("tc_id"), tc_id1)
        self.assertEqual(data2.get("tc", {}).get("capacity"), "200KVA")
        print("  [PASSED] Transformer Upsert & Idempotency")

    def test_04_transformer_update_verifies_attached_poles(self):
        """CRITICAL: Test that updating a Transformer preserves all attached Poles, pole numbers, material survey data, and new pole additions."""
        tc_num = f"{self.TEST_PREFIX}TC_POLE_INTEGRITY"
        
        # 1. Create Transformer
        tc_res = self.client.post('/transformer', json={
            "tc_number": tc_num,
            "tc_name": "TC Original Name",
            "feeder_id": str(self.feeder.id),
            "lat": 23.100,
            "long": 72.100,
            "capacity": "100KVA"
        })
        self.assertEqual(tc_res.status_code, 201)
        tc_id = tc_res.get_json().get("tc_id")

        # 2. Attach multiple Poles to this Transformer
        p1_res = self.client.post('/pole', json={
            "tc_id": tc_id,
            "pole_number": f"{self.TEST_PREFIX}P_ATTACHED_01",
            "is_existing": True,
            "lat": 23.101,
            "long": 72.101
        })
        self.assertEqual(p1_res.status_code, 201)
        p1_id = p1_res.get_json().get("pole_id")

        p2_res = self.client.post('/pole', json={
            "tc_id": tc_num,
            "pole_number": f"{self.TEST_PREFIX}P_ATTACHED_02",
            "is_existing": False,
            "previous_connector_type": "pole",
            "previous_connector_id": f"{self.TEST_PREFIX}P_ATTACHED_01",
            "lat": 23.102,
            "long": 72.102
        })
        self.assertEqual(p2_res.status_code, 201)

        # 3. Submit Material Info for attached Pole
        mat_res = self.client.post(f'/material-info/{self.TEST_PREFIX}P_ATTACHED_01?poleType=existing', json={
            "Type of Pole": "PSC",
            "Condition of Pole": "Good"
        })
        self.assertEqual(mat_res.status_code, 200)

        # 4. UPDATE TRANSFORMER details via PATCH /transformer and POST /transformer
        patch_res = self.client.patch('/transformer', query_string={"tc_id": tc_num}, json={
            "tc_name": "TC Updated Name via PATCH",
            "capacity": "250KVA",
            "lat": 23.110,
            "long": 72.110
        })
        self.assertEqual(patch_res.status_code, 200)

        upsert_res = self.client.post('/transformer', json={
            "tc_number": tc_num,
            "tc_name": "TC Updated Name via POST Upsert",
            "feeder_id": str(self.feeder.id),
            "capacity": "500KVA"
        })
        self.assertEqual(upsert_res.status_code, 200)

        # 5. POLE INTEGRITY CHECKS AFTER TRANSFORMER UPDATE:
        # A. Query poles list by Transformer ID and TC Number
        poles_by_id = self.client.get(f'/poles?tc_id={tc_id}')
        self.assertEqual(poles_by_id.status_code, 200)
        self.assertEqual(len(poles_by_id.get_json().get("pole_numbers", [])), 2)

        poles_by_num = self.client.get(f'/poles?tc_id={tc_num}')
        self.assertEqual(poles_by_num.status_code, 200)
        self.assertEqual(len(poles_by_num.get_json().get("pole_numbers", [])), 2)

        # B. Verify individual Pole details & materials remain valid
        p1_check = self.client.get(f'/pole?poleId={self.TEST_PREFIX}P_ATTACHED_01')
        self.assertEqual(p1_check.status_code, 200)
        self.assertEqual(p1_check.get_json().get("tc_number"), tc_num)
        self.assertEqual(p1_check.get_json().get("existing_info", {}).get("Type of Pole"), "PSC")

        # C. Verify attaching a NEW Pole to the updated Transformer works smoothly
        p3_res = self.client.post('/pole', json={
            "tc_id": tc_num,
            "pole_number": f"{self.TEST_PREFIX}P_ATTACHED_03",
            "is_existing": False,
            "previous_connector_type": "pole",
            "previous_connector_id": f"{self.TEST_PREFIX}P_ATTACHED_02",
            "lat": 23.103,
            "long": 72.103
        })
        self.assertEqual(p3_res.status_code, 201)

        print("  [PASSED] Transformer Update & Attached Poles Integrity Verification")

    # --- POLE ENDPOINT TESTS ---

    def test_05_pole_online_mode_create(self):
        """Test creating a Pole in Online mode using Transformer Mongo ID."""
        tc_num = f"{self.TEST_PREFIX}TC_POLE_TEST"
        tc_res = self.client.post('/transformer', json={
            "tc_number": tc_num,
            "feeder_id": str(self.feeder.id),
            "lat": 23.100,
            "long": 72.100
        })
        tc_id = tc_res.get_json().get("tc_id")

        pole_num = f"{self.TEST_PREFIX}P_ONLINE_001"
        payload = {
            "tc_id": tc_id,
            "pole_number": pole_num,
            "is_existing": True,
            "previous_connector_type": "tc",
            "previous_connector_id": tc_id,
            "lat": 23.101,
            "long": 72.101
        }
        res = self.client.post('/pole', json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn("pole_id", data)
        self.assertGreater(data.get("span_length", 0), 0)
        print("  [PASSED] Pole Online Creation & Haversine Span Calculation")

    def test_06_pole_offline_mode_tc_number(self):
        """Test creating a Pole using string TC Number and Pole Number references."""
        tc_num = f"{self.TEST_PREFIX}TC_OFFLINE_POLE"
        self.client.post('/transformer', json={
            "tc_number": tc_num,
            "feeder_id": str(self.feeder.id),
            "lat": 24.000,
            "long": 73.000
        })

        pole_num1 = f"{self.TEST_PREFIX}P1"
        payload1 = {
            "tc_id": tc_num,
            "pole_number": pole_num1,
            "is_existing": False,
            "lat": 24.001,
            "long": 73.001
        }
        res1 = self.client.post('/pole', json=payload1)
        self.assertEqual(res1.status_code, 201)

        # Create second pole referencing previous pole by pole_number
        pole_num2 = f"{self.TEST_PREFIX}P2"
        payload2 = {
            "tc_id": tc_num,
            "pole_number": pole_num2,
            "is_existing": False,
            "previous_connector_type": "pole",
            "previous_connector_id": pole_num1,
            "lat": 24.002,
            "long": 73.002
        }
        res2 = self.client.post('/pole', json=payload2)
        self.assertEqual(res2.status_code, 201)
        print("  [PASSED] Pole Offline TC Number & Pole Number References")

    def test_07_pole_idempotency_and_upsert(self):
        """Test Pole Upsert with duplicate (tc_id, pole_number) and client_tx_id."""
        tc_num = f"{self.TEST_PREFIX}TC_IDEMP_POLE"
        self.client.post('/transformer', json={
            "tc_number": tc_num,
            "feeder_id": str(self.feeder.id)
        })

        pole_num = f"{self.TEST_PREFIX}P_IDEMP_001"
        tx_id = "local_tx_pole_9999"
        payload = {
            "tc_id": tc_num,
            "pole_number": pole_num,
            "is_existing": False,
            "lat": 23.500,
            "long": 72.500,
            "client_tx_id": tx_id
        }

        # Initial submit -> 201
        res1 = self.client.post('/pole', json=payload)
        self.assertEqual(res1.status_code, 201)
        pole_id1 = res1.get_json().get("pole_id")

        # Duplicate submit -> 200 (Upsert)
        payload["lat"] = 23.505
        res2 = self.client.post('/pole', json=payload)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.get_json().get("pole_id"), pole_id1)
        print("  [PASSED] Pole Idempotency & Upsert")

    def test_08_material_info_submit_and_upsert(self):
        """Test Material Info key-value submission and upsert updates."""
        tc_num = f"{self.TEST_PREFIX}TC_MAT_TEST"
        self.client.post('/transformer', json={
            "tc_number": tc_num,
            "feeder_id": str(self.feeder.id)
        })

        pole_num = f"{self.TEST_PREFIX}P_MAT_001"
        p_res = self.client.post('/pole', json={
            "tc_id": tc_num,
            "pole_number": pole_num,
            "is_existing": True,
            "lat": 23.0,
            "long": 72.0
        })
        pole_id = p_res.get_json().get("pole_id")

        # Initial material submit
        mat1 = {
            "Type of Pole": "PSC",
            "Condition of Pole": "Good"
        }
        res1 = self.client.post(f'/material-info/{pole_num}?poleType=existing', json=mat1)
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(res1.get_json().get("success"))

        # Resubmit / update material
        mat2 = {
            "Condition of Pole": "Rusted",
            "Danger Board": "Yes"
        }
        res2 = self.client.post(f'/material-info/{pole_num}?poleType=existing', json=mat2)
        self.assertEqual(res2.status_code, 200)
        updated_info = res2.get_json().get("pole", {}).get("existing_info", {})
        self.assertEqual(updated_info.get("Condition of Pole"), "Rusted")
        self.assertEqual(updated_info.get("Danger Board"), "Yes")
        print("  [PASSED] Material Info Key-Value Upsert")

if __name__ == '__main__':
    unittest.main(verbosity=2)
