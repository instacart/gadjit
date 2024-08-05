import importlib
import os

from . import models


def process_env_variables(config):
    """
    Process environment variables in a given configuration dictionary.

    This function retrieves environment variables based on the values starting with 'env:' prefix in the input dictionary.
    If a matching environment variable is found, it replaces the 'env:' prefixed value with the actual environment variable value.

    Args:
        config (dict or list): The input configuration containing environment variable placeholders.

    Returns:
        dict or list: The configuration with environment variables resolved.

    Raises:
        RuntimeError: If an environment variable specified in the configuration is not found.
    """
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("env:"):
                env_var_name = value[4:]
                env_value = os.getenv(env_var_name)
                if env_value is None:
                    raise RuntimeError(
                        f"Environment variable '{env_var_name}' not found"
                    )
                config[key] = env_value
            elif isinstance(value, (dict, list)):
                process_env_variables(value)
    elif isinstance(config, list):
        for index, item in enumerate(config):
            if isinstance(item, str) and item.startswith("env:"):
                env_var_name = item[4:]
                env_value = os.getenv(env_var_name)
                if env_value is None:
                    raise RuntimeError(
                        f"Environment variable '{env_var_name}' not found"
                    )
                config[index] = env_value
            elif isinstance(item, (dict, list)):
                process_env_variables(item)
    return config


def plugins_run_function(plugins_set, function_name, *args, **kwargs):
    """
    Run a specified function from a set of plugins.

    Args:
        plugins_set (set): A set of plugin objects.
        function_name (str): The name of the function to run.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        list: A list of results returned by running the specified function on each plugin.
    """
    results = []
    for plugin in plugins_set:
        function_target = getattr(plugin, function_name)
        results.append(function_target(*args, **kwargs))
    return results


def load_plugins(plugin_type, config):
    """
    Load and instantiate plugins of a specific type based on the provided configuration.

    Args:
        plugin_type (str): The type of plugin to load (options: 'iga', 'llm', 'scoring').
        config (dict): A dictionary containing plugin configurations, including names and settings.

    Returns:
        list: A list of instantiated plugin objects based on the configuration.

    Raises:
        ImportError: If the specified plugin file cannot be imported.
        AttributeError: If the specified plugin class is not found in the imported file.
    """
    plugin_dirs = {
        "iga": "gadjit/plugins/iga",
        "llm": "gadjit/plugins/llm",
        "scoring": "gadjit/plugins/scoring",
    }

    base_classes = {
        "iga": models.BaseGadjitIGAPlugin,
        "llm": models.BaseGadjitLLMPlugin,
        "scoring": models.BaseGadjitScoringPlugin,
    }

    loaded_plugins = []
    for plugin_config in config[f"{plugin_type}_plugins"]:
        if plugin_config["enabled"]:
            plugin_name = plugin_config["name"]
            plugin_path = os.path.join(
                plugin_dirs[plugin_type], plugin_name, "plugin.py"
            )

            # Dynamically import the plugin module
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Instantiate the plugin
            for attr in dir(module):
                plugin_class = getattr(module, attr)
                if (
                    isinstance(plugin_class, type)
                    and issubclass(plugin_class, base_classes[plugin_type])
                    and plugin_class is not base_classes[plugin_type]
                ):
                    plugin_instance = plugin_class(plugin_config["config"])
                    loaded_plugins.append(plugin_instance)
                    break

    return loaded_plugins
