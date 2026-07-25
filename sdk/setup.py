from setuptools import find_packages, setup

setup(
    name="amf-sdk",
    version="1.0.0",
    description="Automated Manuscript Formatter - Python SDK",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "httpx>=0.27.0",
        "pydantic>=2.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.3.0",
            "pytest-asyncio>=0.24.0",
            "ruff>=0.6.0",
            "mypy>=1.11.0",
        ],
    },
    python_requires=">=3.11",
)
