"""Entry point for recipes app - now primarily for backwards compatibility."""

# Import the recipes package to trigger export registration
import recipes

if __name__ == "__main__":
    # The app is now primarily driven through exports
    # For backwards compatibility, you could add a simple CLI here
    # But the main interface is now through Clanker's export system
    print("Recipes app loaded. Use through Clanker: 'clanker recipes add ...' or agent tools.")