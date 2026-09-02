from pathlib import Path

import pytest

from decision_kernel.research import ResearchStatus
from decision_kernel.research_commit import ResearchCommitPackage, commit_research_package


@pytest.mark.parametrize(
    ("package_path", "ticker"),
    (
        (Path("dogfood/600519-moutai.json"), "600519"),
        (Path("dogfood/300750-catl.json"), "300750"),
        (Path("dogfood/600036-cmb.json"), "600036"),
        (Path("dogfood/601088-shenhua.json"), "601088"),
    ),
)
def test_checked_in_dogfood_packages_remain_kernel_valid(
    package_path: Path,
    ticker: str,
) -> None:
    package = ResearchCommitPackage.model_validate_json(
        package_path.read_text(encoding="utf-8")
    )

    result = commit_research_package(package)

    assert package.research_snapshot.ticker == ticker
    assert package.research_snapshot.status is ResearchStatus.REVIEW
    assert result.research_snapshot.status is ResearchStatus.COMMITTED
    assert result.information_bundle_hash == package.research_snapshot.information_bundle_hash
