import importlib
import models
import os


def process_env_variables(config):
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("env:"):
                env_var_name = value[4:]
                env_value = os.getenv(env_var_name)
                if env_value is None:
                    raise RuntimeError(f"Environment variable '{env_var_name}' not found")
                config[key] = env_value
            elif isinstance(value, (dict, list)):
                process_env_variables(value)
    elif isinstance(config, list):
        for index, item in enumerate(config):
            if isinstance(item, str) and item.startswith("env:"):
                env_var_name = item[4:]
                env_value = os.getenv(env_var_name)
                if env_value is None:
                    raise RuntimeError(f"Environment variable '{env_var_name}' not found")
                config[index] = env_value
            elif isinstance(item, (dict, list)):
                process_env_variables(item)
    return config


def plugins_run_function(plugins_set, function_name, *args, **kwargs):
    results = []
    for plugin in plugins_set:
        function_target = getattr(plugin, function_name)
        results.append(function_target(*args, **kwargs))
    return results


def load_plugins(plugin_type, config):
    plugin_dirs = {
        'iga': 'plugins/iga',
        'llm': 'plugins/llm',
        'scoring': 'plugins/scoring',
    }

    base_classes = {
        'iga': models.BaseGadjitIGAPlugin,
        'llm': models.BaseGadjitLLMPlugin,
        'scoring': models.BaseGadjitScoringPlugin,
    }

    loaded_plugins = []
    for plugin_config in config[f'{plugin_type}_plugins']:
        if plugin_config['enabled']:
            plugin_name = plugin_config['name']
            plugin_path = os.path.join(plugin_dirs[plugin_type], plugin_name, "plugin.py")
            
            # Dynamically import the plugin module
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Instantiate the plugin
            for attr in dir(module):
                plugin_class = getattr(module, attr)
                if isinstance(plugin_class, type) and issubclass(plugin_class, base_classes[plugin_type]) and plugin_class is not base_classes[plugin_type]:
                    plugin_instance = plugin_class(plugin_config['config'])
                    loaded_plugins.append(plugin_instance)
                    break

    return loaded_plugins

