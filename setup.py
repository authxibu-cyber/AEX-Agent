from setuptools import setup, find_packages

setup(
    name="merlin-agent",
    version="1.0.0",
    packages=find_packages(),
    py_modules=["merlin_constants"],
    install_requires=[
        "pydantic>=2.0.0",
        "rich>=13.0.0",
        "prompt_toolkit>=3.0.0",
        "httpx>=0.24.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.22.0",
        "pyyaml>=6.0",
        "python-dotenv>=1.0.0",
        "aiofiles>=23.0.0",
        "croniter>=2.0.0",
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "merlin = merlin_agent.cli.main:main",
            "merlin-agent = merlin_agent.agent.core:main",
            "merlin-gateway = merlin_agent.gateway.server:main",
        ],
    },
)
