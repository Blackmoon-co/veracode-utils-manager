from setuptools import setup, find_packages

setup(
    name="veracode-utils-manager",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.31.0",
        "pyyaml>=6.0.2",
        "veracode-api-signing>=22.3.0",
    ],
    entry_points={
        "console_scripts": [
            "create-teams=create_teams_from_csv:main",
        ],
    },
    author="Saúl Alfonso Quintero Pedroza",
    author_email="iam@saulquintero.com.co",
    description="Una herramienta para gestionar Teams en Veracode",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/saqpsaqp/veracode-teams-manager",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
)