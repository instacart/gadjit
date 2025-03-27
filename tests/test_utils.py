import os
import pytest
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from gadjit.utils import process_env_variables

def test_process_env_variables_dict():
    # Test with a dictionary containing environment variables
    test_config = {
        "api_key": "env:TEST_API_KEY",
        "nested": {
            "secret": "env:TEST_SECRET"
        }
    }
    
    # Set up test environment variables
    os.environ["TEST_API_KEY"] = "test_key_value"
    os.environ["TEST_SECRET"] = "test_secret_value"
    
    # Process the config
    result = process_env_variables(test_config)
    
    # Assert the values were replaced correctly
    assert result["api_key"] == "test_key_value"
    assert result["nested"]["secret"] == "test_secret_value"

def test_process_env_variables_list():
    # Test with a list containing environment variables
    test_config = [
        "env:TEST_VAR1",
        {"key": "env:TEST_VAR2"}
    ]
    
    # Set up test environment variables
    os.environ["TEST_VAR1"] = "value1"
    os.environ["TEST_VAR2"] = "value2"
    
    # Process the config
    result = process_env_variables(test_config)
    
    # Assert the values were replaced correctly
    assert result[0] == "value1"
    assert result[1]["key"] == "value2"

def test_process_env_variables_missing_env():
    # Test with a missing environment variable
    test_config = {
        "api_key": "env:MISSING_VAR"
    }
    
    # Ensure the environment variable is not set
    if "MISSING_VAR" in os.environ:
        del os.environ["MISSING_VAR"]
    
    # Assert that processing raises a RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        process_env_variables(test_config)
    assert "Environment variable 'MISSING_VAR' not found" in str(exc_info.value)

def test_process_env_variables_no_env_vars():
    # Test with a config containing no environment variables
    test_config = {
        "api_key": "static_value",
        "nested": {
            "key": "another_static_value"
        }
    }
    
    # Process the config
    result = process_env_variables(test_config)
    
    # Assert the values remained unchanged
    assert result["api_key"] == "static_value"
    assert result["nested"]["key"] == "another_static_value" 