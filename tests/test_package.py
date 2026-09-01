def test_package_imports() -> None:
    import decision_kernel

    assert decision_kernel.__all__ == ()
