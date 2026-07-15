import unittest


class UserDirectoryTests(unittest.TestCase):
    def test_prefers_email_then_username_from_the_existing_user_directory(self):
        from AgentBI.src.services.user_directory import MongoUserDirectory

        class Users:
            def __init__(self):
                self.queries = []

            def find_one(self, query):
                self.queries.append(query)
                return {"username": "Elysi", "email": "elysi@example.com"} if query == {"username": "Elysi"} else None

        directory = MongoUserDirectory(None, "unused", users=Users())

        self.assertEqual(directory.find_user("Elysi")["email"], "elysi@example.com")
        self.assertEqual(directory.users.queries, [{"email": "Elysi"}, {"username": "Elysi"}])


if __name__ == "__main__":
    unittest.main()
