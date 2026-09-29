"""
Entrypoint for `python -m ex_agent`.
Dispatches directly to the EX CLI.
"""
from ex_agent.cli.main import main

if __name__ == "__main__":
    main()
