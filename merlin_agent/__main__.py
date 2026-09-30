"""
Entrypoint for `python -m merlin_agent`.
Dispatches directly to the EX CLI.
"""
from merlin_agent.cli.main import main

if __name__ == "__main__":
    main()
