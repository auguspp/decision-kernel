from decision_kernel.cli import build_parser


def test_result_only_disclosure_receipt_command_is_not_exposed() -> None:
    help_text = build_parser().format_help()

    assert "apply-disclosure-assessment" in help_text
    assert "record-disclosure-assessment" not in help_text
