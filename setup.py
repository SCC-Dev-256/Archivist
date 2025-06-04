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
    ],
    python_requires=">=3.8",
) 