import unittest

from userls import LoginDefs, classify


class ClassifyTests(unittest.TestCase):
    ranges = LoginDefs()

    def test_root_is_system(self):
        self.assertEqual(classify(0, "/bin/bash", "/root", self.ranges), "system")

    def test_regular_login_is_normal(self):
        self.assertEqual(
            classify(1000, "/usr/bin/fish", "/home/juan", self.ranges),
            "normal",
        )

    def test_nologin_is_service(self):
        self.assertEqual(
            classify(105, "/usr/sbin/nologin", "/run/foo", self.ranges),
            "service",
        )

    def test_false_shell_is_service(self):
        self.assertEqual(
            classify(1001, "/bin/false", "/home/x", self.ranges),
            "service",
        )

    def test_bogus_home_is_service(self):
        self.assertEqual(
            classify(1001, "/bin/bash", "/nonexistent", self.ranges),
            "service",
        )

    def test_legacy_uid_below_sys_min_is_system(self):
        self.assertEqual(classify(4, "/bin/sync", "/bin", self.ranges), "system")

    def test_nobody_is_service(self):
        self.assertEqual(
            classify(65534, "/usr/sbin/nologin", "/nonexistent", self.ranges),
            "service",
        )

    def test_out_of_range_is_unknown(self):
        self.assertEqual(
            classify(70000, "/bin/bash", "/home/weird", self.ranges),
            "unknown",
        )

    def test_normal_range_with_nologin_is_service(self):
        self.assertEqual(
            classify(1001, "/usr/sbin/nologin", "/home/x", self.ranges),
            "service",
        )

    def test_custom_ranges(self):
        custom = LoginDefs(uid_min=5000, uid_max=9000, sys_uid_min=500, sys_uid_max=999)
        self.assertEqual(classify(6000, "/bin/bash", "/home/x", custom), "normal")
        self.assertEqual(classify(3000, "/bin/bash", "/home/x", custom), "system")
        self.assertEqual(classify(10000, "/bin/bash", "/home/x", custom), "unknown")


if __name__ == "__main__":
    unittest.main()
