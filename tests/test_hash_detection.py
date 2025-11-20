"""Comprehensive test suite for hash type detection.

Tests hash detection functionality without requiring GPU or actual hashcat execution.
"""
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vastcat.detect import (
    detect_hash_modes,
    sample_from_file,
    _extract_candidate,
    _detect_with_regex,
    HashGuess,
    NTH_AVAILABLE,
)


class TestHashDetection:
    """Test hash type detection functionality."""

    def test_md5_detection(self):
        """Test MD5 hash detection."""
        sample = "5f4dcc3b5aa765d61d8327deb882cf99"
        results = detect_hash_modes(sample)

        assert len(results) > 0, "Should detect at least one hash type"
        # MD5 should be in the results (mode 0)
        modes = [r.mode for r in results]
        assert "0" in modes, f"MD5 (mode 0) should be detected, got modes: {modes}"

        # First result should be MD5 (highest confidence)
        assert results[0].name == "MD5", f"First result should be MD5, got {results[0].name}"
        assert results[0].confidence >= 0.85, "MD5 should have high confidence"

    def test_sha1_detection(self):
        """Test SHA-1 hash detection."""
        sample = "356a192b7913b04c54574d18c28d46e6395428ab"
        results = detect_hash_modes(sample)

        assert len(results) > 0, "Should detect at least one hash type"
        modes = [r.mode for r in results]
        assert "100" in modes, f"SHA-1 (mode 100) should be detected, got modes: {modes}"

    def test_sha256_detection(self):
        """Test SHA-256 hash detection."""
        sample = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        results = detect_hash_modes(sample)

        assert len(results) > 0, "Should detect at least one hash type"
        modes = [r.mode for r in results]
        assert "1400" in modes, f"SHA-256 (mode 1400) should be detected, got modes: {modes}"

    def test_sha512_detection(self):
        """Test SHA-512 hash detection."""
        sample = "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e"
        results = detect_hash_modes(sample)

        assert len(results) > 0, "Should detect at least one hash type"
        modes = [r.mode for r in results]
        assert "1700" in modes, f"SHA-512 (mode 1700) should be detected, got modes: {modes}"

    def test_bcrypt_detection(self):
        """Test bcrypt hash detection."""
        sample = "$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy"
        results = detect_hash_modes(sample)

        assert len(results) > 0, "Should detect at least one hash type"
        modes = [r.mode for r in results]
        assert "3200" in modes, f"bcrypt (mode 3200) should be detected, got modes: {modes}"

        # bcrypt should have high confidence
        bcrypt_results = [r for r in results if r.mode == "3200"]
        assert len(bcrypt_results) > 0, "Should have bcrypt in results"
        assert bcrypt_results[0].confidence >= 0.9, "bcrypt should have high confidence"

    def test_md5crypt_detection(self):
        """Test md5crypt ($1$) hash detection."""
        sample = "$1$28772684$iEwNOgGugqO9.bIz5sk8k/"
        results = detect_hash_modes(sample)

        assert len(results) > 0, "Should detect at least one hash type"
        modes = [r.mode for r in results]
        assert "500" in modes, f"md5crypt (mode 500) should be detected, got modes: {modes}"

    def test_sha256crypt_detection(self):
        """Test sha256crypt ($5$) hash detection."""
        sample = "$5$rounds=5000$GX7BopJZJxPc/KEK$le16UF8I2Anb.rOrn22AUPWvzUETDGefUmAV8AZkGcD"
        results = detect_hash_modes(sample)

        assert len(results) > 0, "Should detect at least one hash type"
        modes = [r.mode for r in results]
        assert "7400" in modes, f"sha256crypt (mode 7400) should be detected, got modes: {modes}"

    def test_sha512crypt_detection(self):
        """Test sha512crypt ($6$) hash detection."""
        sample = "$6$52450745$k5ka2p8bFuSmoVT1tzOyyuaREkkKBcCNqoDKzYiJL9RaE8yMnPgh2XzzF0NDrUhgrcLwg78xs1w5pJiypEdFX/"
        results = detect_hash_modes(sample)

        assert len(results) > 0, "Should detect at least one hash type"
        modes = [r.mode for r in results]
        assert "1800" in modes, f"sha512crypt (mode 1800) should be detected, got modes: {modes}"

    def test_ntlm_detection(self):
        """Test NTLM hash detection."""
        # NTLM is 32 hex chars (same as MD5), so it should be detected
        sample = "8846f7eaee8fb117ad06bdd830b7586c"
        results = detect_hash_modes(sample)

        assert len(results) > 0, "Should detect at least one hash type"
        modes = [r.mode for r in results]
        # NTLM (1000) or MD5 (0) could be detected for 32 hex chars
        assert "1000" in modes or "0" in modes, f"NTLM or MD5 should be detected, got modes: {modes}"

    def test_netntlmv2_detection(self):
        """Test NetNTLMv2 hash detection."""
        sample = "admin::N46iSNekpT:08ca45b7d7ea58ee:88dcbe4446168966a153a0064958dac6:5c7830315c7830310000000000000b45c67103d07d7b95acd12ffa11230e0000000052920b85f78d013c31cdb3b92f5d765c783030"
        results = detect_hash_modes(sample)

        assert len(results) > 0, "Should detect at least one hash type"
        modes = [r.mode for r in results]
        assert "5600" in modes, f"NetNTLMv2 (mode 5600) should be detected, got modes: {modes}"

    def test_netntlmv1_detection(self):
        """Test NetNTLMv1 hash detection."""
        sample = "u4-netntlm::kNS:338d08f8e26de93300000000000000000000000000000000:9526fb8c23a90751cdd619b6cea564742e1e4bf33006ba41:cb8086049ec4736c"
        results = detect_hash_modes(sample)

        assert len(results) > 0, "Should detect at least one hash type"
        modes = [r.mode for r in results]
        # NetNTLMv1 and v2 have similar formats, so either could match
        assert "5500" in modes or "5600" in modes, f"NetNTLM (mode 5500/5600) should be detected, got modes: {modes}"

    def test_kerberos_tgs_detection(self):
        """Test Kerberos 5 TGS-REP detection."""
        sample = "$krb5tgs$23$*user$realm$test/spn*$63386d22d359fe42230300d56852c9eb$891ad31d09ab89c6b3b8c5e5de6c06a7f49fd559d7a9a3c32576c8fedf705376"
        results = detect_hash_modes(sample)

        assert len(results) > 0, "Should detect at least one hash type"
        modes = [r.mode for r in results]
        assert "13100" in modes, f"Kerberos TGS (mode 13100) should be detected, got modes: {modes}"

    def test_empty_string(self):
        """Test that empty string returns no results."""
        results = detect_hash_modes("")
        assert len(results) == 0, "Empty string should return no results"

    def test_whitespace_only(self):
        """Test that whitespace-only string returns no results."""
        results = detect_hash_modes("   \n\t  ")
        assert len(results) == 0, "Whitespace-only string should return no results"

    def test_invalid_hash(self):
        """Test that invalid hash format returns appropriate results."""
        # Random string that's not a hash
        results = detect_hash_modes("this is not a hash")
        # Should return empty or very low confidence results
        # (behavior depends on whether name-that-hash is available)
        assert isinstance(results, list), "Should return a list"

    def test_hash_with_salt(self):
        """Test hash with username:hash format."""
        sample = "user:5f4dcc3b5aa765d61d8327deb882cf99"
        # The extract_candidate function should pick the longest field (the hash)
        candidate = _extract_candidate(sample)
        assert candidate == "5f4dcc3b5aa765d61d8327deb882cf99", f"Should extract hash part, got: {candidate}"

        results = detect_hash_modes(candidate)
        assert len(results) > 0, "Should detect hash type after extracting from username:hash format"


class TestSampleExtraction:
    """Test hash sample extraction from files."""

    def test_extract_from_single_hash(self):
        """Test extracting hash from file with single hash."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("5f4dcc3b5aa765d61d8327deb882cf99\n")
            fname = f.name

        try:
            sample = sample_from_file(fname)
            assert sample == "5f4dcc3b5aa765d61d8327deb882cf99", f"Should extract hash, got: {sample}"
        finally:
            Path(fname).unlink()

    def test_extract_from_multiple_hashes(self):
        """Test extracting hash from file with multiple hashes."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("5f4dcc3b5aa765d61d8327deb882cf99\n")
            f.write("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n")
            fname = f.name

        try:
            sample = sample_from_file(fname)
            # Should get first hash
            assert sample == "5f4dcc3b5aa765d61d8327deb882cf99", f"Should extract first hash, got: {sample}"
        finally:
            Path(fname).unlink()

    def test_extract_from_username_hash_format(self):
        """Test extracting hash from username:hash format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("user:5f4dcc3b5aa765d61d8327deb882cf99\n")
            fname = f.name

        try:
            sample = sample_from_file(fname)
            # Should extract the longer part (the hash)
            assert sample == "5f4dcc3b5aa765d61d8327deb882cf99", f"Should extract hash part, got: {sample}"
        finally:
            Path(fname).unlink()

    def test_extract_skips_comments(self):
        """Test that comment lines are skipped."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("# This is a comment\n")
            f.write("5f4dcc3b5aa765d61d8327deb882cf99\n")
            fname = f.name

        try:
            sample = sample_from_file(fname)
            assert sample == "5f4dcc3b5aa765d61d8327deb882cf99", f"Should skip comment and extract hash, got: {sample}"
        finally:
            Path(fname).unlink()

    def test_extract_skips_empty_lines(self):
        """Test that empty lines are skipped."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("\n")
            f.write("   \n")
            f.write("5f4dcc3b5aa765d61d8327deb882cf99\n")
            fname = f.name

        try:
            sample = sample_from_file(fname)
            assert sample == "5f4dcc3b5aa765d61d8327deb882cf99", f"Should skip empty lines and extract hash, got: {sample}"
        finally:
            Path(fname).unlink()

    def test_nonexistent_file(self):
        """Test behavior with nonexistent file."""
        sample = sample_from_file("/nonexistent/path/to/file.txt")
        assert sample is None, "Should return None for nonexistent file"

    def test_empty_file(self):
        """Test behavior with empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            fname = f.name

        try:
            sample = sample_from_file(fname)
            assert sample is None, "Should return None for empty file"
        finally:
            Path(fname).unlink()


class TestRegexFallback:
    """Test regex-based detection fallback."""

    def test_regex_md5(self):
        """Test regex detection of MD5."""
        sample = "5f4dcc3b5aa765d61d8327deb882cf99"
        results = _detect_with_regex(sample)

        assert len(results) > 0, "Regex should detect MD5"
        modes = [r.mode for r in results]
        assert "0" in modes, f"MD5 (mode 0) should be in regex results, got: {modes}"

    def test_regex_bcrypt(self):
        """Test regex detection of bcrypt."""
        sample = "$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy"
        results = _detect_with_regex(sample)

        assert len(results) > 0, "Regex should detect bcrypt"
        modes = [r.mode for r in results]
        assert "3200" in modes, f"bcrypt (mode 3200) should be in regex results, got: {modes}"

    def test_regex_sha512crypt(self):
        """Test regex detection of sha512crypt."""
        sample = "$6$52450745$k5ka2p8bFuSmoVT1tzOyyuaREkkKBcCNqoDKzYiJL9RaE8yMnPgh2XzzF0NDrUhgrcLwg78xs1w5pJiypEdFX/"
        results = _detect_with_regex(sample)

        assert len(results) > 0, "Regex should detect sha512crypt"
        modes = [r.mode for r in results]
        assert "1800" in modes, f"sha512crypt (mode 1800) should be in regex results, got: {modes}"

    def test_regex_no_duplicates(self):
        """Test that regex detection doesn't return duplicates."""
        sample = "5f4dcc3b5aa765d61d8327deb882cf99"
        results = _detect_with_regex(sample)

        modes = [r.mode for r in results]
        # Check for duplicates
        assert len(modes) == len(set(modes)), f"Should not have duplicate modes, got: {modes}"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_long_hash(self):
        """Test handling of very long hash string."""
        # Create a very long hex string
        sample = "a" * 1000
        results = detect_hash_modes(sample)
        # Should handle gracefully (may or may not match)
        assert isinstance(results, list), "Should return a list"

    def test_hash_with_newlines(self):
        """Test that newlines in hash are handled."""
        sample = "5f4dcc3b5aa765d61d8327deb882cf99\n"
        results = detect_hash_modes(sample)
        # Should strip and detect
        assert len(results) > 0, "Should strip newline and detect hash"

    def test_mixed_case_hash(self):
        """Test that mixed case hex hashes work."""
        sample = "5F4DcC3B5aa765d61d8327dEB882cF99"
        results = detect_hash_modes(sample)
        # Should detect (regex patterns use case-insensitive matching)
        assert len(results) > 0, "Should detect mixed case hash"

    def test_hash_with_spaces(self):
        """Test hash with leading/trailing spaces."""
        sample = "  5f4dcc3b5aa765d61d8327deb882cf99  "
        results = detect_hash_modes(sample)
        # Should strip and detect
        assert len(results) > 0, "Should strip spaces and detect hash"


def run_tests():
    """Run all tests and report results."""
    import traceback

    test_classes = [
        TestHashDetection,
        TestSampleExtraction,
        TestRegexFallback,
        TestEdgeCases,
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    print("="*70)
    print("Hash Detection Test Suite")
    print("="*70)
    print(f"name-that-hash available: {NTH_AVAILABLE}")
    print()

    for test_class in test_classes:
        class_name = test_class.__name__
        print(f"\n{class_name}:")
        print("-" * 50)

        # Get all test methods
        test_methods = [m for m in dir(test_class) if m.startswith('test_')]

        for method_name in test_methods:
            total_tests += 1
            test_name = f"{class_name}.{method_name}"

            try:
                # Create instance and run test
                instance = test_class()
                method = getattr(instance, method_name)
                method()

                print(f"  ✓ {method_name}")
                passed_tests += 1

            except AssertionError as e:
                print(f"  ✗ {method_name}")
                print(f"    {str(e)}")
                failed_tests.append((test_name, str(e)))

            except Exception as e:
                print(f"  ✗ {method_name} (ERROR)")
                print(f"    {str(e)}")
                traceback.print_exc()
                failed_tests.append((test_name, f"ERROR: {str(e)}"))

    # Print summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")

    if failed_tests:
        print("\nFailed tests:")
        for test_name, error in failed_tests:
            print(f"  - {test_name}")
            print(f"    {error}")

    print("="*70)

    return len(failed_tests) == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
