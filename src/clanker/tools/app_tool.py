"""Tool for running clanker apps through the agent."""

from typing import Optional
from pydantic_ai import RunContext, Tool
from .registry import ToolProtocol
from ..logger import get_logger

logger = get_logger("app_tool")


class AppTool(ToolProtocol):
    """Tool for running discovered clanker apps."""

    def __init__(self, app_info: Optional[dict] = None):
        """Initialize AppTool.

        Args:
            app_info: Specific app info, or None to create generic tool
        """
        self.app_info = app_info

        if app_info:
            # Specific app tool
            app_name = app_info["path"].split("/")[-1]
            self.name = f"run_{app_name}"
            self.description = f"Run the {app_name} app with optional arguments"
        else:
            # Generic app tool
            self.name = "run_app"
            self.description = "Run any clanker app with optional arguments"

    def get_tool_definition(self) -> Tool:
        """Return pydantic-ai tool definition."""
        if self.app_info:
            # Specific app tool
            return self._create_specific_app_tool()
        else:
            # Generic app runner
            return self._create_generic_app_tool()

    def _create_generic_app_tool(self) -> Tool:
        """Create tool for running any discovered app."""
        from ..apps import discover, run

        def run_app(
            ctx: RunContext,
            app_name: str,
            args: str = ""
        ) -> str:
            """Execute a specific clanker application with given arguments.

            ONLY use this tool when you need to actually run/execute/launch a clanker app.
            Do NOT use this for general conversation about apps.

            The user must specify:
            - app_name: The exact name of the app (must be one of: example, recipes)
            - args: The command-line arguments to pass to the app

            Examples of when to use:
            - User says "run the example app with hello world"
            - User says "execute recipes add pasta"
            - User says "launch example test"

            Args:
                app_name: Exact app name from available apps list
                args: Arguments string to pass to the app
            """
            logger.info(f"AppTool called with app_name='{app_name}', args='{args}'")

            # Validate parameters
            if not app_name or not isinstance(app_name, str):
                logger.error(f"Invalid app_name parameter: {app_name}")
                return "Error: app_name must be a non-empty string"

            try:
                # Discover available apps
                apps = discover()
                logger.debug(f"Discovered apps: {list(apps.keys())}")

                if app_name not in apps:
                    available = list(apps.keys())
                    logger.warning(f"App '{app_name}' not found. Available: {available}")
                    return f"App '{app_name}' not found. Available apps: {', '.join(available)}"

                # Parse arguments
                arg_list = args.split() if args.strip() else []

                # Run the app
                logger.info(f"Running app '{app_name}' with args: {arg_list}")
                returncode = run(app_name, arg_list)
                logger.debug(f"App '{app_name}' returned exit code: {returncode}")

                if returncode == 0:
                    logger.info(f"Successfully ran app '{app_name}'")
                    return f"Successfully ran app '{app_name}'"
                else:
                    logger.warning(f"App '{app_name}' completed with exit code {returncode}")
                    return f"App '{app_name}' completed with exit code {returncode}"

            except Exception as e:
                return f"Failed to run app '{app_name}': {str(e)}"

        return Tool(run_app)

    def _create_specific_app_tool(self) -> Tool:
        """Create tool for a specific app."""
        from ..apps import run

        app_name = self.app_info["path"].split("/")[-1]

        def run_specific_app(
            ctx: RunContext,
            args: str = ""
        ) -> str:
            """Run the {app_name} app with optional arguments.

            Args:
                args: Space-separated arguments to pass to the app
            """
            try:
                arg_list = args.split() if args.strip() else []
                returncode = run(app_name, arg_list)

                if returncode == 0:
                    return f"Successfully ran {app_name} app"
                else:
                    return f"{app_name} app completed with exit code {returncode}"

            except Exception as e:
                return f"Failed to run {app_name} app: {str(e)}"

        # Update function name and docstring
        run_specific_app.__name__ = f"run_{app_name}"
        run_specific_app.__doc__ = f"Run the {app_name} app with optional arguments.\n\nArgs:\n    args: Space-separated arguments to pass to the app"

        return Tool(run_specific_app)
