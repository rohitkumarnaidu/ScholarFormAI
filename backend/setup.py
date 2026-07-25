from setuptools import find_packages, setup

setup(
    name="amf-backend",
    version="1.0.0",
    description="Automated Manuscript Formatter - Backend API",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.30.0",
        "python-docx>=1.1.2",
        "pydantic>=2.9.0",
        "pydantic-settings>=2.5.0",
        "python-multipart>=0.0.12",
        "aiofiles>=24.1.0",
    ],
    python_requires=">=3.11",
)
