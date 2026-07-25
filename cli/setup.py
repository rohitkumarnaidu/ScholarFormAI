from setuptools import find_packages, setup

setup(
    name="amf-cli",
    version="1.0.0",
    description="Automated Manuscript Formatter - CLI tool",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click>=8.1.0",
        "rich>=13.8.0",
        "requests>=2.32.0",
        "pyyaml>=6.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.3.0",
            "ruff>=0.6.0",
        ],
        "local": [
            "python-docx>=1.1.2",
        ],
    },
    entry_points={
        "console_scripts": [
            "amf=amf.main:cli",
        ],
    },
    python_requires=">=3.11",
)
