"""
Entrypoint for `python -m aex_agent`.
Dispatches directly to the EX CLI.
"""
from aex_agent.cli.main import main

if __name__ == "__main__":
    main()
