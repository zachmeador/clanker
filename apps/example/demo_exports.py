"""Demo script showing the new export-based example app in action."""

import sys
import os

# Add the example app to Python path for demo
sys.path.insert(0, os.path.dirname(__file__))

# Import to trigger export registration
import example

from clanker.exports import get_app_exports, list_exported_apps
from clanker.tools import list_available_exports, create_cli_runner_from_exports

def demo_exports():
    """Demonstrate the export system."""

    print("=== Export-Based Example App Demo ===\n")

    # Show registered apps
    print("1. Registered Apps:")
    apps = list_exported_apps()
    for app in apps:
        print(f"   • {app}")
    print()

    # Show example app exports
    print("2. Example App Exports:")
    example_exports = get_app_exports("example")
    if example_exports:
        print("   CLI Commands:")
        for cmd_name, metadata in example_exports.get_cli_commands().items():
            print(f"     • {cmd_name}: {metadata.description}")

        print("\n   Tool Functions:")
        for func_name, metadata in example_exports.get_tool_functions().items():
            print(f"     • {func_name}: {metadata.description}")
    print()

    # Show all available exports
    print("3. All Available Exports:")
    all_exports = list_available_exports()
    for app_name, exports in all_exports.items():
        print(f"   {app_name}:")
        print(f"     CLI: {exports['cli_commands']}")
        print(f"     Tools: {exports['tool_functions']}")
    print()

    print("4. Example CLI Execution:")
    print("   Simulating: clanker example hello 'Alice'")

    try:
        result = create_cli_runner_from_exports("example", "hello", name="Alice")
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Error: {e}")
    print()

    print("5. Example Tool Function Calls:")
    print("   Simulating agent calling various functions")

    if example_exports:
        tool_funcs = example_exports.get_tool_functions()

        # Test get_system_info
        if "get_system_info" in tool_funcs:
            metadata = tool_funcs["get_system_info"]
            print(f"   • {metadata.name}: {metadata.description}")
            try:
                result = metadata.original_function()
                print(f"     Result: {result}")
            except Exception as e:
                print(f"     Error: {e}")

        # Test validate_name
        if "validate_name" in tool_funcs:
            metadata = tool_funcs["validate_name"]
            print(f"   • {metadata.name}: {metadata.description}")
            test_names = ["Alice", "", "A_@#$%", "Very Long Name That Exceeds Limits"]
            for name in test_names:
                try:
                    result = metadata.original_function(name)
                    print(f"     validate_name('{name}') = {result}")
                except Exception as e:
                    print(f"     Error validating '{name}': {e}")

        # Test create_greeting
        if "create_greeting" in tool_funcs:
            metadata = tool_funcs["create_greeting"]
            print(f"   • {metadata.name}: {metadata.description}")
            test_cases = [("Bob", "casual"), ("Dr. Smith", "formal"), ("Sam", "excited")]
            for name, style in test_cases:
                try:
                    result = metadata.original_function(name, style)
                    print(f"     create_greeting('{name}', '{style}') = '{result}'")
                except Exception as e:
                    print(f"     Error creating greeting for '{name}': {e}")

    print("\n=== Demo Complete ===")

if __name__ == "__main__":
    demo_exports()
