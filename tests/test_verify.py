"""Tests for the comparison rules.

Each case here traces back to something a stakeholder said in the interview notes.
"""

from app.verify import (
    GOVERNMENT_WARNING,
    Status,
    check_alcohol_content,
    check_brand_name,
    check_government_warning,
    check_net_contents,
    verify,
)


class TestBrandName:
    def test_identical(self):
        assert check_brand_name("OLD TOM DISTILLERY", "OLD TOM DISTILLERY").status is Status.MATCH

    def test_dave_case(self):
        """Dave: 'STONE'S THROW' on the label vs 'Stone's Throw' in the application."""
        result = check_brand_name("Stone's Throw", "STONE’S THROW")
        assert result.status is Status.MATCH
        assert "capitalization" in result.note

    def test_near_miss_goes_to_an_agent(self):
        assert check_brand_name("Old Tom Distillery", "Old Tomm Distillery").status is Status.REVIEW

    def test_different_brand(self):
        assert check_brand_name("Old Tom Distillery", "Iron Gate Spirits").status is Status.MISMATCH

    def test_unreadable(self):
        assert check_brand_name("Old Tom Distillery", None).status is Status.MISSING


class TestAlcoholContent:
    def test_matching_abv_with_proof(self):
        assert check_alcohol_content("45% Alc./Vol.", "45% Alc./Vol. (90 Proof)").status is Status.MATCH

    def test_wrong_abv(self):
        result = check_alcohol_content("45% Alc./Vol.", "40% Alc./Vol.")
        assert result.status is Status.MISMATCH
        assert "45" in result.note and "40" in result.note

    def test_proof_inconsistent_with_abv(self):
        """Proof must be exactly twice the ABV; 45% with '80 Proof' is a label error."""
        assert check_alcohol_content("45% Alc./Vol.", "45% Alc./Vol. (80 Proof)").status is Status.MISMATCH

    def test_proof_only_label(self):
        assert check_alcohol_content("45% Alc./Vol.", "90 Proof").status is Status.MATCH


class TestNetContents:
    def test_unit_conversion(self):
        assert check_net_contents("750 mL", "0.75 L").status is Status.MATCH

    def test_wrong_volume(self):
        assert check_net_contents("750 mL", "700 mL").status is Status.MISMATCH


class TestGovernmentWarning:
    def test_exact(self):
        assert check_government_warning(GOVERNMENT_WARNING).status is Status.MATCH

    def test_whitespace_and_line_breaks_are_fine(self):
        wrapped = GOVERNMENT_WARNING.replace(" ", "\n  ", 3)
        assert check_government_warning(wrapped).status is Status.MATCH

    def test_jenny_case_title_case_prefix(self):
        """Jenny: caught one using 'Government Warning' in title case. Rejected."""
        result = check_government_warning(GOVERNMENT_WARNING.replace("GOVERNMENT WARNING:", "Government Warning:"))
        assert result.status is Status.MISMATCH
        assert "all capitals" in result.note

    def test_reworded(self):
        result = check_government_warning(
            "GOVERNMENT WARNING: Drinking during pregnancy may cause birth defects."
        )
        assert result.status is Status.MISMATCH
        assert "word-for-word" in result.note

    def test_absent(self):
        assert check_government_warning(None).status is Status.MISSING
        assert check_government_warning("   ").status is Status.MISSING


class TestWholeLabel:
    APPLICATION = {"brand_name": "Old Tom Distillery", "alcohol_content": "45% Alc./Vol.", "net_contents": "750 mL"}

    def test_clean_label_passes(self):
        report = verify(self.APPLICATION, {
            "brand_name": "OLD TOM DISTILLERY",
            "alcohol_content": "45% Alc./Vol. (90 Proof)",
            "net_contents": "750 mL",
            "government_warning": GOVERNMENT_WARNING,
        })
        assert report.passed
        assert report.status is Status.MATCH

    def test_worst_result_wins(self):
        report = verify(self.APPLICATION, {
            "brand_name": "Old Tomm Distillery",   # review
            "alcohol_content": "40% Alc./Vol.",    # mismatch
            "net_contents": "750 mL",
            "government_warning": GOVERNMENT_WARNING,
        })
        assert report.status is Status.MISMATCH
        assert not report.passed

    def test_missing_warning_is_caught(self):
        report = verify(self.APPLICATION, {
            "brand_name": "OLD TOM DISTILLERY",
            "alcohol_content": "45% Alc./Vol.",
            "net_contents": "750 mL",
            "government_warning": None,
        })
        assert report.status is Status.MISSING
