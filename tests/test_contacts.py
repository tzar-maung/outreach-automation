"""Contact-storage requirements, tested with disposable SQLite databases."""

import tempfile
import unittest
from pathlib import Path

from outreach_bot.core.database import Database


class ContactStorageTests(unittest.TestCase):
    def setUp(self):
        # Never use the application's real database in these tests.
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / "contacts_test.db"
        self.db = Database(str(self.db_path))

    def test_new_database_has_no_contacts(self):
        self.assertEqual(self.db.list_contacts(), [])

    def test_add_contact_saves_fields_and_default_status(self):
        contact_id = self.db.add_contact(
            name="Sample Person",
            organization="Example Organization",
            profile_url="https://example.com/sample-person",
        )

        self.assertIsInstance(contact_id, int)
        self.assertGreater(contact_id, 0)
        contacts = self.db.list_contacts()
        self.assertEqual(len(contacts), 1)
        contact = contacts[0]
        self.assertEqual(contact["id"], contact_id)
        self.assertEqual(contact["name"], "Sample Person")
        self.assertEqual(contact["organization"], "Example Organization")
        self.assertEqual(contact["profile_url"], "https://example.com/sample-person")
        self.assertEqual(contact["status"], "Not contacted")
        self.assertTrue(contact["created_at"])
        self.assertTrue(contact["updated_at"])

    def test_contact_survives_reopening_database(self):
        contact_id = self.db.add_contact(name="Sample Person")
        self.assertTrue(self.db.update_contact_status(contact_id, "Drafted"))

        reopened_db = Database(str(self.db_path))
        contact = reopened_db.list_contacts()[0]
        self.assertEqual(contact["id"], contact_id)
        self.assertEqual(contact["name"], "Sample Person")
        self.assertEqual(contact["status"], "Drafted")

    def test_status_update_changes_only_selected_contact(self):
        first_id = self.db.add_contact(name="First Sample")
        second_id = self.db.add_contact(name="Second Sample")

        # Status changes record a human's action; they must not send messages.
        for status in ("Drafted", "Sent", "Replied", "Not contacted"):
            with self.subTest(status=status):
                self.assertTrue(self.db.update_contact_status(first_id, status))
                contacts = {row["id"]: row for row in self.db.list_contacts()}
                self.assertEqual(contacts[first_id]["status"], status)
                self.assertEqual(contacts[second_id]["status"], "Not contacted")

    def test_blank_name_is_rejected_without_saving(self):
        for name in ("", "   ", "\t\n"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.db.add_contact(name=name)
                self.assertEqual(self.db.list_contacts(), [])

    def test_invalid_status_is_rejected_without_changing_contact(self):
        contact_id = self.db.add_contact(name="Sample Person")

        with self.assertRaises(ValueError):
            self.db.update_contact_status(contact_id, "Unknown status")

        self.assertEqual(self.db.list_contacts()[0]["status"], "Not contacted")

    def test_name_is_trimmed_and_optional_fields_can_be_omitted(self):
        self.db.add_contact(name="  Sample Person  ")
        contact = self.db.list_contacts()[0]
        self.assertEqual(contact["name"], "Sample Person")
        self.assertIsNone(contact["organization"])
        self.assertIsNone(contact["profile_url"])

    def test_missing_contact_returns_false(self):
        self.assertFalse(self.db.update_contact_status(999, "Drafted"))
        self.assertEqual(self.db.list_contacts(), [])

    def test_invalid_contact_id_is_rejected(self):
        for contact_id in (0, -1, True, "1", None):
            with self.subTest(contact_id=contact_id):
                with self.assertRaises(ValueError):
                    self.db.update_contact_status(contact_id, "Drafted")

    def test_invalid_field_types_are_rejected(self):
        for fields in ({"name": None}, {"name": 123},
                       {"name": "Sample", "organization": 123},
                       {"name": "Sample", "profile_url": 123}):
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):
                    self.db.add_contact(**fields)
                self.assertEqual(self.db.list_contacts(), [])

    def test_status_update_refreshes_timestamp(self):
        contact_id = self.db.add_contact(name="Sample Person")
        # Use a fixed old timestamp instead of making the test sleep.
        with self.db.get_connection() as conn:
            conn.execute("UPDATE contacts SET updated_at = ? WHERE id = ?",
                         ("2000-01-01 00:00:00", contact_id))

        self.db.update_contact_status(contact_id, "Drafted")
        self.assertNotEqual(self.db.list_contacts()[0]["updated_at"],
                            "2000-01-01 00:00:00")

    def test_contact_changes_leave_legacy_target_unchanged(self):
        target_id = self.db.add_target("https://example.com/legacy", "generic")
        original_target = self.db.get_target(target_id)
        contact_id = self.db.add_contact(name="Sample Person")
        self.db.update_contact_status(contact_id, "Replied")

        self.assertEqual(self.db.get_target(target_id), original_target)


if __name__ == "__main__":
    unittest.main()
