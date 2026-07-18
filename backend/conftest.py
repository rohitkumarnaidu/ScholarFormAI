def pytest_load_initial_conftests(early_config, parser):
    """Patch coverage.py to handle pydantic >= 2.13.x KeyError."""
    try:
        import coverage
    except ImportError:
        return
    _orig_start = coverage.Coverage.start
    def _patched_start(self):
        try:
            return _orig_start(self)
        except KeyError as e:
            if "pydantic.root_model" not in str(e):
                raise
    coverage.Coverage.start = _patched_start
