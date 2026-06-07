## 2024-05-18 - Python Unit Testing with pytest-mock

When writing unit tests for Python modules that use external or specific internal hooks, utilize `pytest-mock` (via the `mocker` fixture) to patch specific functions dynamically. This ensures proper isolation of tests. Be careful when mocking to target the exact namespace where the dependency is imported/used. For example, use `mocker.patch("koraku.profiles.product_hooks_active", return_value=True)` rather than mocking the original definition location. Also, make sure dependencies are correctly set up via `pip install -e '.[all,dev]'`.
