"""Entry point for example app - now primarily for backwards compatibility."""

# Import the example package to trigger export registration
import example

if __name__ == "__main__":
    # The app is now primarily driven through exports
    # For backwards compatibility, you could add a simple CLI here
    # But the main interface is now through Clanker's export system
    print("Example app loaded. Use through Clanker: 'clanker example hello' or agent tools.")