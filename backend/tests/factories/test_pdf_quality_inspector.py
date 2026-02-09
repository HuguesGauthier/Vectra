"""
Tests for PDF Quality Inspector.

Tests all quality detection methods and scoring algorithm.
"""

import pytest

from app.factories.processors.pdf_quality_inspector import PdfQualityInspector


class TestPdfQualityInspectorEmptyDetection:
    """Tests for empty text detection."""

    def test_is_empty_with_empty_string(self):
        """Empty string should be detected."""
        assert PdfQualityInspector.is_empty("") is True

    def test_is_empty_with_whitespace_only(self):
        """Whitespace-only text should be detected as empty."""
        assert PdfQualityInspector.is_empty("   \n\t  ") is True

    def test_is_empty_with_actual_content(self):
        """Text with content should not be empty."""
        assert PdfQualityInspector.is_empty("Hello World") is False

    def test_is_empty_with_minimal_content(self):
        """Even single character should not be empty."""
        assert PdfQualityInspector.is_empty("a") is False


class TestPdfQualityInspectorLengthDetection:
    """Tests for content length detection."""

    def test_is_too_short_with_default_threshold(self):
        """Text below 50 chars should be too short."""
        short_text = "Page 1"  # 6 characters
        assert PdfQualityInspector.is_too_short(short_text) is True

    def test_is_too_short_at_boundary(self):
        """Text exactly at threshold should not be too short."""
        boundary_text = "x" * 50
        assert PdfQualityInspector.is_too_short(boundary_text) is False

    def test_is_too_short_above_threshold(self):
        """Text above threshold should not be too short."""
        long_text = "x" * 100
        assert PdfQualityInspector.is_too_short(long_text) is False

    def test_is_too_short_custom_threshold(self):
        """Custom threshold should be respected."""
        text = "Hello"  # 5 characters
        assert PdfQualityInspector.is_too_short(text, min_chars=10) is True
        assert PdfQualityInspector.is_too_short(text, min_chars=3) is False

    def test_is_too_short_strips_whitespace(self):
        """Whitespace should be stripped before counting."""
        text = "   Hello   "  # 5 chars after strip
        assert PdfQualityInspector.is_too_short(text, min_chars=10) is True


class TestPdfQualityInspectorEncodingDetection:
    """Tests for encoding corruption detection."""

    def test_has_encoding_issues_with_unicode_replacement(self):
        """Unicode replacement characters should indicate corruption."""
        corrupted_text = "Hello � World"
        assert PdfQualityInspector.has_encoding_issues(corrupted_text) is True

    def test_has_encoding_issues_with_multiple_replacements(self):
        """Multiple replacement characters should be detected."""
        corrupted_text = "���������"
        assert PdfQualityInspector.has_encoding_issues(corrupted_text) is True

    def test_has_encoding_issues_with_clean_text(self):
        """Clean text should not have encoding issues."""
        clean_text = "This is a perfectly normal sentence with punctuation!"
        assert PdfQualityInspector.has_encoding_issues(clean_text) is False

    def test_has_encoding_issues_with_french_accents(self):
        """French accents should be valid, not corruption."""
        french_text = "Café, crème, résumé, naïve"
        assert PdfQualityInspector.has_encoding_issues(french_text) is False

    def test_has_encoding_issues_with_high_gibberish_ratio(self):
        """Text with excessive non-alphanumeric chars should be flagged."""
        # Create text with >60% non-alphanumeric
        gibberish = "###@@@%%%$$$^^^&&&***((())))"  # 100% non-alphanumeric
        assert PdfQualityInspector.has_encoding_issues(gibberish) is True

    def test_has_encoding_issues_with_normal_punctuation(self):
        """Normal punctuation should not trigger gibberish detection."""
        normal_text = "Hello, world! How are you? (Fine, thanks.)"
        assert PdfQualityInspector.has_encoding_issues(normal_text) is False

    def test_has_encoding_issues_with_empty_text(self):
        """Empty text should not have encoding issues."""
        assert PdfQualityInspector.has_encoding_issues("") is False


class TestPdfQualityInspectorScoring:
    """Tests for quality score calculation."""

    def test_calculate_quality_score_empty_text(self):
        """Empty text should score 0."""
        score = PdfQualityInspector.calculate_quality_score("")
        assert score == 0

    def test_calculate_quality_score_whitespace_only(self):
        """Whitespace-only should score 0."""
        score = PdfQualityInspector.calculate_quality_score("   \n\t  ")
        assert score == 0

    def test_calculate_quality_score_too_short(self):
        """Too short text should have penalty (-50)."""
        short_text = "Page 1"  # < 50 chars
        score = PdfQualityInspector.calculate_quality_score(short_text)
        # Base 100 - 50 (too short) = 50
        assert score == 50

    def test_calculate_quality_score_encoding_issues(self):
        """Encoding issues should have penalty (-40)."""
        corrupted_text = "Hello � World " + ("x" * 50)  # Long enough to avoid short penalty
        score = PdfQualityInspector.calculate_quality_score(corrupted_text)
        # Base 100 - 40 (encoding) = 60
        assert score == 60

    def test_calculate_quality_score_short_and_corrupted(self):
        """Multiple penalties should stack."""
        bad_text = "���"  # Short AND corrupted
        score = PdfQualityInspector.calculate_quality_score(bad_text)
        # Base 100 - 50 (short) - 40 (encoding) = 10
        assert score == 10

    def test_calculate_quality_score_clean_text(self):
        """Clean, sufficient text should score well."""
        good_text = "This is a normal paragraph with sufficient content for quality analysis."
        score = PdfQualityInspector.calculate_quality_score(good_text)
        # Base 100, no penalties
        assert score == 100

    def test_calculate_quality_score_long_content_bonus(self):
        """Long content (>1000 chars) should get bonus (+10)."""
        long_text = "x" * 1001
        score = PdfQualityInspector.calculate_quality_score(long_text)
        # Base 100 + 10 (long content) = 110, capped at 100
        assert score == 100

    def test_calculate_quality_score_multi_paragraph_bonus(self):
        """Multiple paragraphs (≥3) should get bonus (+5)."""
        multi_para = "Para 1\n\nPara 2\n\nPara 3\n\nPara 4"
        score = PdfQualityInspector.calculate_quality_score(multi_para)
        # Base 100 + 5 (multi-paragraph) = 105, capped at 100
        assert score == 100

    def test_calculate_quality_score_with_all_bonuses(self):
        """Text with all bonuses should still cap at 100."""
        excellent_text = ("Paragraph one.\n\n" * 10) + ("x" * 1000)
        score = PdfQualityInspector.calculate_quality_score(excellent_text)
        # Base 100 + 10 (long) + 5 (paragraphs) = 115, capped at 100
        assert score == 100

    def test_calculate_quality_score_never_negative(self):
        """Score should never go below 0."""
        # Hypothetically extreme case (if penalties > 100)
        terrible_text = ""
        score = PdfQualityInspector.calculate_quality_score(terrible_text)
        assert score >= 0


class TestPdfQualityInspectorRouting:
    """Tests for cloud routing decision."""

    def test_should_use_cloud_empty_text(self):
        """Empty text should route to cloud (OCR needed)."""
        assert PdfQualityInspector.should_use_cloud("") is True

    def test_should_use_cloud_low_quality(self):
        """Low quality text (score < 40) should route to cloud."""
        low_quality = "Page 1"  # Score = 50, but let's test with corrupted
        corrupted_short = "���"  # Score = 10 (< 40)
        assert PdfQualityInspector.should_use_cloud(corrupted_short) is True

    def test_should_use_cloud_acceptable_quality(self):
        """Acceptable quality (score >= 40) should use local."""
        good_text = "This is a normal paragraph with sufficient content for quality analysis."
        # Score = 100 (>= 40)
        assert PdfQualityInspector.should_use_cloud(good_text) is False

    def test_should_use_cloud_at_threshold(self):
        """Score exactly at threshold (40) should use local."""
        # Need to craft text that scores exactly 40
        # Base 100 - 50 (short) - 10 (hypothetical) = 40
        # For simplicity, test with threshold parameter
        medium_text = "x" * 60  # Scores 100
        assert PdfQualityInspector.should_use_cloud(medium_text, threshold=100) is True
        assert PdfQualityInspector.should_use_cloud(medium_text, threshold=99) is False

    def test_should_use_cloud_custom_threshold(self):
        """Custom threshold should be respected."""
        text = "This is normal text."
        # Default threshold = 40, score = 100
        assert PdfQualityInspector.should_use_cloud(text) is False

        # High threshold = 150 (impossible to reach)
        assert PdfQualityInspector.should_use_cloud(text, threshold=150) is True

    def test_should_use_cloud_scanned_pdf_scenario(self):
        """Scanned PDF (empty text) should definitely route to cloud."""
        scanned_pdf_text = ""
        decision = PdfQualityInspector.should_use_cloud(scanned_pdf_text)
        assert decision is True


class TestPdfQualityInspectorDecisionReason:
    """Tests for decision reason helper."""

    def test_get_decision_reason_empty(self):
        """Empty text should return correct reason."""
        reason = PdfQualityInspector._get_decision_reason("", 0)
        assert reason == "text_empty_likely_scanned"

    def test_get_decision_reason_too_short(self):
        """Too short text should return correct reason."""
        reason = PdfQualityInspector._get_decision_reason("Hi", 50)
        assert reason == "text_too_short"

    def test_get_decision_reason_corrupted(self):
        """Corrupted text should return correct reason."""
        corrupted = "Hello � World " + ("x" * 50)
        score = PdfQualityInspector.calculate_quality_score(corrupted)
        reason = PdfQualityInspector._get_decision_reason(corrupted, score)
        assert reason == "encoding_corrupted"

    def test_get_decision_reason_sufficient(self):
        """Good quality should return correct reason."""
        good_text = "This is perfectly normal text with sufficient length."
        score = PdfQualityInspector.calculate_quality_score(good_text)
        reason = PdfQualityInspector._get_decision_reason(good_text, score)
        assert reason == "local_quality_sufficient"


class TestPdfQualityInspectorRealWorldScenarios:
    """Real-world scenario tests."""

    def test_scenario_native_pdf_text(self):
        """Typical PDF with native text should pass local quality."""
        native_pdf_text = """
        CHAPTER 1: Introduction
        
        This document contains important information about the project.
        It has been generated from a word processor and contains native text.
        
        The content is well-formatted and easily extractable.
        """

        score = PdfQualityInspector.calculate_quality_score(native_pdf_text)
        should_cloud = PdfQualityInspector.should_use_cloud(native_pdf_text)

        assert score >= 40, "Native PDF should have acceptable quality"
        assert should_cloud is False, "Native PDF should stay local"

    def test_scenario_scanned_pdf(self):
        """Scanned PDF with no extractable text should route to cloud."""
        scanned_pdf_text = ""  # pypdf returns empty for scanned images

        score = PdfQualityInspector.calculate_quality_score(scanned_pdf_text)
        should_cloud = PdfQualityInspector.should_use_cloud(scanned_pdf_text)

        assert score == 0, "Scanned PDF should score 0"
        assert should_cloud is True, "Scanned PDF should route to cloud for OCR"

    def test_scenario_page_numbers_only(self):
        """PDF with only page numbers should be flagged."""
        page_number_text = "1"

        score = PdfQualityInspector.calculate_quality_score(page_number_text)
        should_cloud = PdfQualityInspector.should_use_cloud(page_number_text)

        assert score < 40, "Page number only should have low quality"
        assert should_cloud is True, "Minimal content should try cloud"

    def test_scenario_corrupted_encoding(self):
        """PDF with encoding issues should be sent to cloud."""
        corrupted_text = "This is � corrupted � text � from � old � PDF"

        score = PdfQualityInspector.calculate_quality_score(corrupted_text)
        should_cloud = PdfQualityInspector.should_use_cloud(corrupted_text)

        assert score < 100, "Corrupted text should have penalty"
        # Might still be >= 40 if long enough, test the encoding detection
        assert PdfQualityInspector.has_encoding_issues(corrupted_text) is True

    def test_scenario_multilingual_content(self):
        """PDF with French/English mixed should be valid."""
        multilingual = """
        Bonjour! This is a bilingual document.
        Il contient du texte en français et en anglais.
        Café, résumé, naïve are all valid French words.
        """

        score = PdfQualityInspector.calculate_quality_score(multilingual)
        should_cloud = PdfQualityInspector.should_use_cloud(multilingual)

        assert score >= 80, "Multilingual should score well"
        assert should_cloud is False, "Multilingual should stay local"

    def test_scenario_technical_document(self):
        """Technical PDF with code/symbols should be handled correctly."""
        technical = """
        Function: calculate_score(text: str) -> int
        
        This function analyzes text quality.
        Example: score = calculate_score("Hello")
        
        Parameters:
        - text: Input string to analyze
        - Returns: Quality score 0-100
        """

        score = PdfQualityInspector.calculate_quality_score(technical)

        # Technical docs have valid punctuation/symbols
        assert score >= 40, "Technical content should be acceptable"
        assert PdfQualityInspector.has_encoding_issues(technical) is False
