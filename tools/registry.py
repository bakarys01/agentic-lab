from importlib import import_module

from smolagents import Tool

from agents.config_loader import load_tool_config


def create_tool(name: str) -> Tool:
    settings = load_tool_config(name)
    module_name, attribute_name = settings["target"].split(":")

    module = import_module(module_name)
    component = getattr(module, attribute_name)

    if settings["kind"] == "factory":
        if not callable(component):
            raise TypeError(f"Tool factory {name} is not callable.")
        tool = component()
    else:
        tool = component

    if not isinstance(tool, Tool):
        raise TypeError(f"Configured component {name} is not a Tool.")

    return tool