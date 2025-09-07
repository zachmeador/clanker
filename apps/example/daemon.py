"""Background daemon for daily journal summarization."""

import time
import signal
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

from example.storage import JournalStorage
from clanker.storage import Vault


class JournalSummarizer:
    """Daemon that generates daily summaries of journal entries."""
    
    def __init__(self, interval: int = 86400):  # Default: 24 hours
        """Initialize the summarizer daemon.
        
        Args:
            interval: Seconds between summary generation runs
        """
        self.interval = interval
        self.running = True
        self.storage = JournalStorage()
        self.vault = Vault.for_app("example")
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        print(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def run(self):
        """Main daemon loop."""
        print(f"Journal summarizer started with interval {self.interval} seconds")
        
        while self.running:
            try:
                # Generate summary
                self._generate_daily_summary()
                
                
                # Sleep for the interval
                start_time = time.time()
                while self.running and (time.time() - start_time) < self.interval:
                    time.sleep(10)  # Check every 10 seconds for shutdown
                    
            except Exception as e:
                print(f"Error in daemon loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
        
        print("Journal summarizer daemon stopped")
    
    def _generate_daily_summary(self):
        """Generate a summary of journal entries from the last day."""
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_str = yesterday.strftime('%Y-%m-%d')
        
        print(f"Generating summary for {yesterday_str}")
        
        # Get all entries from the database
        all_entries = self.storage.db.query("entries")
        
        # Filter entries from yesterday
        yesterday_entries = [
            entry for entry in all_entries 
            if entry['created_at'].startswith(yesterday_str)
        ]
        
        if not yesterday_entries:
            print(f"No entries found for {yesterday_str}")
            return
        
        # Generate summary
        total_words = sum(entry['word_count'] for entry in yesterday_entries)
        all_tags = []
        
        summary_content = f"""# Daily Summary - {yesterday_str}

## Statistics
- **Entries written:** {len(yesterday_entries)}
- **Total words:** {total_words}
- **Average words per entry:** {total_words / len(yesterday_entries):.1f}

## Entries Overview
"""
        
        # Add brief overview of each entry
        for i, entry in enumerate(sorted(yesterday_entries, key=lambda x: x['created_at']), 1):
            time_part = entry['created_at'].split('T')[1].split('.')[0]  # Extract time
            summary_content += f"**{i}.** {time_part} - {entry['summary']}"
            if entry['tags']:
                summary_content += f" (Tags: {entry['tags']})"
                all_tags.extend(entry['tags'].split(', '))
            summary_content += "\n\n"
        
        # Add tags summary
        if all_tags:
            unique_tags = sorted(set(tag for tag in all_tags if tag))
            summary_content += f"## Tags Used\n{', '.join(unique_tags)}\n\n"
        
        summary_content += f"*Summary generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        
        # Save summary to vault
        summary_filename = f"summaries/daily_summary_{yesterday_str}.md"
        self.vault.write(summary_filename, summary_content)
        
        print(f"Summary saved to {summary_filename}")
    


def main():
    """Main entry point for the daemon."""
    parser = argparse.ArgumentParser(description="Journal summarizer daemon")
    parser.add_argument('--interval', type=int, default=86400,
                       help='Interval in seconds between runs (default: 86400 = 24 hours)')
    parser.add_argument('--once', action='store_true',
                       help='Run once and exit (for testing)')
    
    args = parser.parse_args()
    
    summarizer = JournalSummarizer(interval=args.interval)
    
    if args.once:
        # Run once for testing
        print("Running summarizer once...")
        summarizer._generate_daily_summary()
        print("Done")
    else:
        # Run as daemon
        summarizer.run()


if __name__ == "__main__":
    main()