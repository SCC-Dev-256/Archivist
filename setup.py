from setuptools import setup, find_packages

setup(
    name="archivist",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.100.0",
        "uvicorn>=0.22.0",
        "python-magic>=0.4.27",
        "pydantic>=2.0.0",
        "sqlalchemy>=2.0.0",
        "alembic>=1.11.0",
        "psycopg2-binary>=2.9.0",
        "redis>=4.5.0",
        "flask-limiter>=3.5.0",
        "flask-caching>=2.0.0",
        "certbot>=2.0.0",
        "prometheus-client>=0.17.0",
        "loguru>=0.7.0",
        "transformers>=4.30.0",
        "torch>=2.0.0",
        "numpy>=1.24.0",
        "matplotlib>=3.7.0",
        "pyannote.audio>=3.1.0",
        "huggingface-hub>=0.16.0",
    ],
    extras_require={
        'test': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-asyncio>=0.21.0',
            'pytest-mock>=3.10.0',
        ]
    },
    python_requires=">=3.8",
) 