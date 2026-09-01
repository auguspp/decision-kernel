from pathlib import Path

from decision_kernel.research import ResearchStatus
from decision_kernel.research_commit import ResearchCommitPackage, commit_research_package


def test_600519_dogfood_package_remains_kernel_valid() -> None:
    package_path = Path("dogfood/600519-moutai.json")
    package = ResearchCommitPackage.model_validate_json(
        package_path.read_text(encoding="utf-8")
    )

    result = commit_research_package(package)

    assert package.research_snapshot.ticker == "600519"
    assert package.research_snapshot.status is ResearchStatus.REVIEW
    assert result.research_snapshot.status is ResearchStatus.COMMITTED
    assert result.information_bundle_hash == package.research_snapshot.information_bundle_hash
