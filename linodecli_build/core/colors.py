"""Terminal color utilities for consistent output formatting."""

class Colors:
    """ANSI color codes for terminal output."""
    # Basic colors
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright variants
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'


def success(text: str) -> str:
    """Format text as success (green)."""
    return f"{Colors.BRIGHT_GREEN}{text}{Colors.RESET}"


def info(text: str) -> str:
    """Format text as info (cyan)."""
    return f"{Colors.BRIGHT_CYAN}{text}{Colors.RESET}"


def warning(text: str) -> str:
    """Format text as warning (yellow)."""
    return f"{Colors.BRIGHT_YELLOW}{text}{Colors.RESET}"


def error(text: str) -> str:
    """Format text as error (red)."""
    return f"{Colors.BRIGHT_RED}{text}{Colors.RESET}"


def highlight(text: str) -> str:
    """Format text as highlighted (bold cyan)."""
    return f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}"


def bold(text: str) -> str:
    """Format text as bold."""
    return f"{Colors.BOLD}{text}{Colors.RESET}"


def dim(text: str) -> str:
    """Format text as dim."""
    return f"{Colors.DIM}{text}{Colors.RESET}"


def header(text: str) -> str:
    """Format text as section header (bold magenta)."""
    return f"{Colors.BOLD}{Colors.MAGENTA}{text}{Colors.RESET}"


def default(text: str) -> str:
    """Format text as default value (bright yellow)."""
    return f"{Colors.BRIGHT_YELLOW}{text}{Colors.RESET}"


def value(text: str) -> str:
    """Format text as a value (bright white)."""
    return f"{Colors.BRIGHT_WHITE}{text}{Colors.RESET}"
