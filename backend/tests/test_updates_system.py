import pytest
from app.services.update_service import UpdateService

def test_compare_versions():
    service = UpdateService()
    
    # 1.0.0 vs 1.0.0
    assert service._compare_versions("1.0.0", "1.0.0") == 0
    assert service._compare_versions("v1.0.0", "1.0.0") == 0
    
    # Minor update
    assert service._compare_versions("1.1.0", "1.0.0") > 0
    assert service._compare_versions("1.0.0", "1.1.0") < 0
    
    # Major update
    assert service._compare_versions("2.0.0", "1.9.9") > 0
    
    # Patch update
    assert service._compare_versions("1.0.1", "1.0.0") > 0
    
    # Pre-release ignoring (simple SemVer parser just looks at main parts)
    assert service._compare_versions("1.1.0-beta", "1.0.0") > 0

def test_parse_versions():
    service = UpdateService()
    
    assert service._parse_version("1.2.3") == (1, 2, 3)
    assert service._parse_version("v1.2.3") == (1, 2, 3)
    assert service._parse_version("1.2") == (1, 2, 0)
    assert service._parse_version("1.2.3-beta.1") == (1, 2, 3)
