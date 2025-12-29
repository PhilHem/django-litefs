"""Unit tests for binary-related domain value objects."""

import pytest
from datetime import datetime
from pathlib import Path

from litefs.domain.binary import (
    Platform,
    BinaryVersion,
    BinaryLocation,
    BinaryMetadata,
)
from litefs.domain.exceptions import LiteFSConfigError


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.Platform")
class TestPlatform:
    """Test Platform value object."""

    def test_create_linux_amd64(self):
        """Test creating platform with linux/amd64."""
        platform = Platform(os="linux", arch="amd64")
        assert platform.os == "linux"
        assert platform.arch == "amd64"

    def test_create_linux_arm64(self):
        """Test creating platform with linux/arm64."""
        platform = Platform(os="linux", arch="arm64")
        assert platform.os == "linux"
        assert platform.arch == "arm64"

    def test_create_darwin_amd64(self):
        """Test creating platform with darwin/amd64."""
        platform = Platform(os="darwin", arch="amd64")
        assert platform.os == "darwin"
        assert platform.arch == "amd64"

    def test_create_darwin_arm64(self):
        """Test creating platform with darwin/arm64."""
        platform = Platform(os="darwin", arch="arm64")
        assert platform.os == "darwin"
        assert platform.arch == "arm64"

    def test_frozen_dataclass(self):
        """Test that Platform is immutable."""
        platform = Platform(os="linux", arch="amd64")
        with pytest.raises(AttributeError):
            platform.os = "darwin"  # type: ignore

    def test_reject_invalid_os(self):
        """Test that invalid OS is rejected."""
        with pytest.raises(LiteFSConfigError, match="os must be one of"):
            Platform(os="windows", arch="amd64")  # type: ignore

    def test_reject_invalid_arch(self):
        """Test that invalid arch is rejected."""
        with pytest.raises(LiteFSConfigError, match="arch must be one of"):
            Platform(os="linux", arch="x86")  # type: ignore

    def test_equality(self):
        """Test that platforms with same values are equal."""
        p1 = Platform(os="linux", arch="amd64")
        p2 = Platform(os="linux", arch="amd64")
        assert p1 == p2

    def test_inequality(self):
        """Test that platforms with different values are not equal."""
        p1 = Platform(os="linux", arch="amd64")
        p2 = Platform(os="darwin", arch="amd64")
        assert p1 != p2

    def test_hash_consistency(self):
        """Test that platforms with same values have same hash."""
        p1 = Platform(os="linux", arch="amd64")
        p2 = Platform(os="linux", arch="amd64")
        assert hash(p1) == hash(p2)

    def test_can_use_in_set(self):
        """Test that Platform can be used in sets."""
        p1 = Platform(os="linux", arch="amd64")
        p2 = Platform(os="linux", arch="amd64")
        p3 = Platform(os="darwin", arch="arm64")
        platform_set = {p1, p2, p3}
        assert len(platform_set) == 2


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.BinaryVersion")
class TestBinaryVersion:
    """Test BinaryVersion value object."""

    def test_create_with_components(self):
        """Test creating version with major, minor, patch."""
        version = BinaryVersion(major=0, minor=8, patch=0)
        assert version.major == 0
        assert version.minor == 8
        assert version.patch == 0

    def test_from_string_valid(self):
        """Test parsing version from string."""
        version = BinaryVersion.from_string("0.8.0")
        assert version.major == 0
        assert version.minor == 8
        assert version.patch == 0

    def test_from_string_with_v_prefix(self):
        """Test parsing version with v prefix."""
        version = BinaryVersion.from_string("v1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_from_string_larger_numbers(self):
        """Test parsing version with larger numbers."""
        version = BinaryVersion.from_string("10.20.30")
        assert version.major == 10
        assert version.minor == 20
        assert version.patch == 30

    def test_frozen_dataclass(self):
        """Test that BinaryVersion is immutable."""
        version = BinaryVersion(major=0, minor=8, patch=0)
        with pytest.raises(AttributeError):
            version.major = 1  # type: ignore

    def test_reject_invalid_format_missing_patch(self):
        """Test that version without patch is rejected."""
        with pytest.raises(LiteFSConfigError, match="Invalid version format"):
            BinaryVersion.from_string("0.8")

    def test_reject_invalid_format_non_numeric(self):
        """Test that non-numeric version is rejected."""
        with pytest.raises(LiteFSConfigError, match="Invalid version format"):
            BinaryVersion.from_string("abc.def.ghi")

    def test_reject_empty_string(self):
        """Test that empty string is rejected."""
        with pytest.raises(LiteFSConfigError, match="Invalid version format"):
            BinaryVersion.from_string("")

    def test_reject_negative_major(self):
        """Test that negative major version is rejected."""
        with pytest.raises(LiteFSConfigError, match="Version components must be non-negative"):
            BinaryVersion(major=-1, minor=0, patch=0)

    def test_reject_negative_minor(self):
        """Test that negative minor version is rejected."""
        with pytest.raises(LiteFSConfigError, match="Version components must be non-negative"):
            BinaryVersion(major=0, minor=-1, patch=0)

    def test_reject_negative_patch(self):
        """Test that negative patch version is rejected."""
        with pytest.raises(LiteFSConfigError, match="Version components must be non-negative"):
            BinaryVersion(major=0, minor=0, patch=-1)

    def test_comparison_less_than_major(self):
        """Test version comparison by major."""
        v1 = BinaryVersion(major=0, minor=9, patch=9)
        v2 = BinaryVersion(major=1, minor=0, patch=0)
        assert v1 < v2

    def test_comparison_less_than_minor(self):
        """Test version comparison by minor."""
        v1 = BinaryVersion(major=1, minor=0, patch=9)
        v2 = BinaryVersion(major=1, minor=1, patch=0)
        assert v1 < v2

    def test_comparison_less_than_patch(self):
        """Test version comparison by patch."""
        v1 = BinaryVersion(major=1, minor=1, patch=0)
        v2 = BinaryVersion(major=1, minor=1, patch=1)
        assert v1 < v2

    def test_comparison_equal(self):
        """Test version equality comparison."""
        v1 = BinaryVersion(major=1, minor=2, patch=3)
        v2 = BinaryVersion(major=1, minor=2, patch=3)
        assert v1 == v2
        assert not (v1 < v2)
        assert not (v1 > v2)

    def test_comparison_greater_than(self):
        """Test version greater than comparison."""
        v1 = BinaryVersion(major=2, minor=0, patch=0)
        v2 = BinaryVersion(major=1, minor=9, patch=9)
        assert v1 > v2

    def test_comparison_less_than_or_equal(self):
        """Test version less than or equal comparison."""
        v1 = BinaryVersion(major=1, minor=0, patch=0)
        v2 = BinaryVersion(major=1, minor=0, patch=0)
        v3 = BinaryVersion(major=1, minor=0, patch=1)
        assert v1 <= v2
        assert v1 <= v3

    def test_comparison_greater_than_or_equal(self):
        """Test version greater than or equal comparison."""
        v1 = BinaryVersion(major=1, minor=0, patch=1)
        v2 = BinaryVersion(major=1, minor=0, patch=0)
        v3 = BinaryVersion(major=1, minor=0, patch=1)
        assert v1 >= v2
        assert v1 >= v3

    def test_str_representation(self):
        """Test string representation of version."""
        version = BinaryVersion(major=0, minor=8, patch=0)
        assert str(version) == "0.8.0"

    def test_hash_consistency(self):
        """Test that versions with same values have same hash."""
        v1 = BinaryVersion(major=1, minor=2, patch=3)
        v2 = BinaryVersion(major=1, minor=2, patch=3)
        assert hash(v1) == hash(v2)

    def test_can_use_in_set(self):
        """Test that BinaryVersion can be used in sets."""
        v1 = BinaryVersion(major=1, minor=0, patch=0)
        v2 = BinaryVersion(major=1, minor=0, patch=0)
        v3 = BinaryVersion(major=2, minor=0, patch=0)
        version_set = {v1, v2, v3}
        assert len(version_set) == 2


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.BinaryLocation")
class TestBinaryLocation:
    """Test BinaryLocation value object."""

    def test_create_with_local_path(self):
        """Test creating location with local path."""
        location = BinaryLocation(path=Path("/usr/local/bin/litefs"), is_custom=False)
        assert location.path == Path("/usr/local/bin/litefs")
        assert location.is_custom is False

    def test_create_with_custom_path(self):
        """Test creating location with custom user-specified path."""
        location = BinaryLocation(path=Path("/home/user/litefs"), is_custom=True)
        assert location.path == Path("/home/user/litefs")
        assert location.is_custom is True

    def test_create_with_relative_path(self):
        """Test creating location with relative path."""
        location = BinaryLocation(path=Path("bin/litefs"), is_custom=True)
        assert location.path == Path("bin/litefs")

    def test_frozen_dataclass(self):
        """Test that BinaryLocation is immutable."""
        location = BinaryLocation(path=Path("/usr/bin/litefs"), is_custom=False)
        with pytest.raises(AttributeError):
            location.path = Path("/other/path")  # type: ignore

    def test_reject_empty_path(self):
        """Test that empty path is rejected."""
        with pytest.raises(LiteFSConfigError, match="path cannot be empty"):
            BinaryLocation(path=Path(""), is_custom=False)

    def test_reject_dot_path(self):
        """Test that single dot path is rejected."""
        with pytest.raises(LiteFSConfigError, match="path cannot be empty"):
            BinaryLocation(path=Path("."), is_custom=False)

    def test_equality(self):
        """Test that locations with same values are equal."""
        loc1 = BinaryLocation(path=Path("/bin/litefs"), is_custom=False)
        loc2 = BinaryLocation(path=Path("/bin/litefs"), is_custom=False)
        assert loc1 == loc2

    def test_inequality_path(self):
        """Test that locations with different paths are not equal."""
        loc1 = BinaryLocation(path=Path("/bin/litefs"), is_custom=False)
        loc2 = BinaryLocation(path=Path("/usr/bin/litefs"), is_custom=False)
        assert loc1 != loc2

    def test_inequality_is_custom(self):
        """Test that locations with different is_custom are not equal."""
        loc1 = BinaryLocation(path=Path("/bin/litefs"), is_custom=False)
        loc2 = BinaryLocation(path=Path("/bin/litefs"), is_custom=True)
        assert loc1 != loc2

    def test_hash_consistency(self):
        """Test that locations with same values have same hash."""
        loc1 = BinaryLocation(path=Path("/bin/litefs"), is_custom=False)
        loc2 = BinaryLocation(path=Path("/bin/litefs"), is_custom=False)
        assert hash(loc1) == hash(loc2)


@pytest.mark.tier(1)
@pytest.mark.tra("Domain.Invariant.BinaryMetadata")
class TestBinaryMetadata:
    """Test BinaryMetadata value object."""

    def test_create_with_required_fields(self):
        """Test creating metadata with only required fields."""
        platform = Platform(os="linux", arch="amd64")
        version = BinaryVersion(major=0, minor=8, patch=0)
        location = BinaryLocation(path=Path("/bin/litefs"), is_custom=False)

        metadata = BinaryMetadata(
            platform=platform,
            version=version,
            location=location,
        )

        assert metadata.platform == platform
        assert metadata.version == version
        assert metadata.location == location
        assert metadata.checksum is None
        assert metadata.size_bytes is None
        assert metadata.downloaded_at is None

    def test_create_with_all_fields(self):
        """Test creating metadata with all fields."""
        platform = Platform(os="darwin", arch="arm64")
        version = BinaryVersion(major=1, minor=0, patch=0)
        location = BinaryLocation(path=Path("/opt/litefs"), is_custom=True)
        downloaded = datetime(2024, 1, 15, 12, 30, 0)

        metadata = BinaryMetadata(
            platform=platform,
            version=version,
            location=location,
            checksum="abc123def456",
            size_bytes=1024000,
            downloaded_at=downloaded,
        )

        assert metadata.platform == platform
        assert metadata.version == version
        assert metadata.location == location
        assert metadata.checksum == "abc123def456"
        assert metadata.size_bytes == 1024000
        assert metadata.downloaded_at == downloaded

    def test_frozen_dataclass(self):
        """Test that BinaryMetadata is immutable."""
        platform = Platform(os="linux", arch="amd64")
        version = BinaryVersion(major=0, minor=8, patch=0)
        location = BinaryLocation(path=Path("/bin/litefs"), is_custom=False)

        metadata = BinaryMetadata(
            platform=platform,
            version=version,
            location=location,
        )

        with pytest.raises(AttributeError):
            metadata.checksum = "new_checksum"  # type: ignore

    def test_reject_negative_size_bytes(self):
        """Test that negative size_bytes is rejected."""
        platform = Platform(os="linux", arch="amd64")
        version = BinaryVersion(major=0, minor=8, patch=0)
        location = BinaryLocation(path=Path("/bin/litefs"), is_custom=False)

        with pytest.raises(LiteFSConfigError, match="size_bytes must be non-negative"):
            BinaryMetadata(
                platform=platform,
                version=version,
                location=location,
                size_bytes=-1,
            )

    def test_reject_empty_checksum(self):
        """Test that empty checksum is rejected."""
        platform = Platform(os="linux", arch="amd64")
        version = BinaryVersion(major=0, minor=8, patch=0)
        location = BinaryLocation(path=Path("/bin/litefs"), is_custom=False)

        with pytest.raises(LiteFSConfigError, match="checksum cannot be empty"):
            BinaryMetadata(
                platform=platform,
                version=version,
                location=location,
                checksum="",
            )

    def test_equality(self):
        """Test that metadata with same values are equal."""
        platform = Platform(os="linux", arch="amd64")
        version = BinaryVersion(major=0, minor=8, patch=0)
        location = BinaryLocation(path=Path("/bin/litefs"), is_custom=False)

        m1 = BinaryMetadata(platform=platform, version=version, location=location)
        m2 = BinaryMetadata(platform=platform, version=version, location=location)
        assert m1 == m2

    def test_inequality(self):
        """Test that metadata with different values are not equal."""
        platform1 = Platform(os="linux", arch="amd64")
        platform2 = Platform(os="darwin", arch="arm64")
        version = BinaryVersion(major=0, minor=8, patch=0)
        location = BinaryLocation(path=Path("/bin/litefs"), is_custom=False)

        m1 = BinaryMetadata(platform=platform1, version=version, location=location)
        m2 = BinaryMetadata(platform=platform2, version=version, location=location)
        assert m1 != m2

    def test_hash_consistency(self):
        """Test that metadata with same values have same hash."""
        platform = Platform(os="linux", arch="amd64")
        version = BinaryVersion(major=0, minor=8, patch=0)
        location = BinaryLocation(path=Path("/bin/litefs"), is_custom=False)

        m1 = BinaryMetadata(platform=platform, version=version, location=location)
        m2 = BinaryMetadata(platform=platform, version=version, location=location)
        assert hash(m1) == hash(m2)

    def test_zero_size_bytes_allowed(self):
        """Test that zero size_bytes is allowed."""
        platform = Platform(os="linux", arch="amd64")
        version = BinaryVersion(major=0, minor=8, patch=0)
        location = BinaryLocation(path=Path("/bin/litefs"), is_custom=False)

        metadata = BinaryMetadata(
            platform=platform,
            version=version,
            location=location,
            size_bytes=0,
        )
        assert metadata.size_bytes == 0
