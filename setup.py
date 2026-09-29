from setuptools import setup, find_packages

setup(
    name="ex-agent",
    version="1.0.0",
    packages=find_packages(),
    py_modules=["ex_constants"],
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
            "ex = ex_agent.cli.main:main",
            "ex-agent = ex_agent.agent.core:main",
            "ex-gateway = ex_agent.gateway.server:main",
        ],
    },
)
