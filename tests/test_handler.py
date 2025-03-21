import json
import os
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from gadjit.handler import lambda_handler, run

def test_lambda_handler_success():
    # Test successful execution
    event = {"test": "event"}
    context = MagicMock()
    
    with patch('gadjit.handler.run') as mock_run:
        response = lambda_handler(event, context)
        
        # Verify the response
        assert response["statusCode"] == 200
        assert response["headers"]["Content-Type"] == "application/json"
        assert json.loads(response["body"])["success"] is True
        
        # Verify run was called with correct arguments
        mock_run.assert_called_once_with(event=event)

def test_lambda_handler_failure():
    # Test execution with an error
    event = {"test": "event"}
    context = MagicMock()
    
    with patch('gadjit.handler.run', side_effect=Exception("Test error")):
        response = lambda_handler(event, context)
        
        # Verify the error response
        assert response["statusCode"] == 500
        assert response["headers"]["Content-Type"] == "application/json"
        assert json.loads(response["body"])["success"] is False
        assert "Test error" in json.loads(response["body"])["message"]

def test_run_with_config_file(tmp_path):
    # Create a temporary config file
    config_content = """
    gadjit:
      plugins:
        scoring:
          enabled:
            - test_scoring
        iga:
          enabled:
            - test_iga
    """
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)
    
    with patch('gadjit.handler._config_from_environment') as mock_env_config, \
         patch('gadjit.handler.utils.load_plugins') as mock_load_plugins:
        # Set up mock return values
        mock_load_plugins.side_effect = lambda plugin_type, config: [MagicMock()]
        
        run(config_path=str(config_file))
        # Verify that _config_from_environment was not called
        mock_env_config.assert_not_called()
        # Verify load_plugins was called
        assert mock_load_plugins.call_count == 3  # Called for iga, llm, and scoring plugins

def test_run_without_config_file():
    # Test running without a config file
    with patch('gadjit.handler._config_from_environment') as mock_env_config, \
         patch('gadjit.handler.utils.load_plugins') as mock_load_plugins:
        # Set up mock return values
        mock_env_config.return_value = {
            "gadjit": {
                "plugins": {
                    "scoring": {"enabled": ["test_scoring"]},
                    "iga": {"enabled": ["test_iga"]}
                }
            }
        }
        mock_load_plugins.side_effect = lambda plugin_type, config: [MagicMock()]
        
        run()
        # Verify that _config_from_environment was called
        mock_env_config.assert_called_once()
        # Verify load_plugins was called
        assert mock_load_plugins.call_count == 3  # Called for iga, llm, and scoring plugins

def test_run_with_event():
    # Test running with an event
    test_event = {"test": "event"}
    with patch('gadjit.handler._config_from_environment') as mock_env_config, \
         patch('gadjit.handler.utils.load_plugins') as mock_load_plugins:
        # Set up mock return values
        mock_env_config.return_value = {
            "gadjit": {
                "plugins": {
                    "scoring": {"enabled": ["test_scoring"]},
                    "iga": {"enabled": ["test_iga"]}
                }
            }
        }
        mock_load_plugins.side_effect = lambda plugin_type, config: [MagicMock()]
        
        run(event=test_event)
        # Verify that _config_from_environment was called
        mock_env_config.assert_called_once()
        # Verify load_plugins was called
        assert mock_load_plugins.call_count == 3  # Called for iga, llm, and scoring plugins 