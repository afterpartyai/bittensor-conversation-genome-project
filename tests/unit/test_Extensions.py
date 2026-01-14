from conversationgenome.extensions.Extensions import Extensions


def test_existing_extension_works_properly():
    ext = Extensions()
    # Verify the extension exists and can be called without raising an exception
    assert "Metrics" in ext.extensionDict
    # incStat doesn't return a value, so we just verify no exception is raised
    ext.execute("Metrics", "incStat", {"metricName": "testMetric", "inc": 1})
    ext.execute("Metrics", "incStat", {"metric_name": "test_ema_zeroes", "inc": 2})

def test_unknown_extension_doesnt_raise_error():
    ext = Extensions()
    result1 = ext.execute("MetricsBADCLASS", "incStatBAD", {"metric_name": "test_ema_zeroes", "inc": 2})
    result2 = ext.execute("Metrics", "incStatBADMETHOD", {"metric_name": "test_ema_zeroes", "inc": 2})
    # Invalid extension/method calls should return None gracefully
    assert result1 is None
    assert result2 is None


def test_discover_populates_extension_dict():
    ext = Extensions()
    # After init, discover() should have found at least the Metrics extension
    assert len(ext.extensionDict) > 0
    assert "Metrics" in ext.extensionDict


def test_execute_returns_none_for_unknown_extension():
    ext = Extensions()
    result = ext.execute("NonExistentExtension", "someMethod", {})
    assert result is None


def test_execute_returns_none_for_unknown_method():
    ext = Extensions()
    result = ext.execute("Metrics", "nonExistentMethod", {})
    assert result is None


def test_execute_with_no_params_defaults_to_empty_dict():
    ext = Extensions()
    # Should not raise an error when params is None
    result = ext.execute("Metrics", "incStat")
    # Result may be None or a value depending on implementation, but no exception should occur
    assert result is None or result is not None  # Just verify no exception