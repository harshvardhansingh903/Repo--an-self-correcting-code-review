#!/usr/bin/env python
"""Setup configuration for code review agent."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="code-review-agent",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Self-correcting code review agent using LangGraph and GPT-4o",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/code-review-agent",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/code-review-agent/issues",
        "Documentation": "https://github.com/yourusername/code-review-agent/blob/main/README.md",
        "Source Code": "https://github.com/yourusername/code-review-agent",
    },
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Quality Assurance",
    ],
    python_requires=">=3.11",
    install_requires=[
        "langgraph>=0.0.61",
        "langchain>=1.2.10",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "docker>=7.0.0",
        "PyGithub>=2.1.0",
        "openai>=1.0.0",
        "sqlalchemy>=2.0.0",
        "asyncpg>=0.28.0",
        "aiosqlite>=0.19.0",
        "python-dotenv>=1.0.0",
        "pytest>=8.0.0",
        "pytest-asyncio>=0.21.0",
    ],
    extras_require={
        "dev": [
            "pytest-cov",
            "black",
            "flake8",
            "mypy",
        ],
    },
)
