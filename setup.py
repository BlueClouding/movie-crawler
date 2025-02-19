from setuptools import setup, find_packages

setup(
    name="123_crawler",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "urllib3>=2.0.0",
    ],
    python_requires=">=3.8",
    author="Anonymous",
    description="A crawler for 123av website",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
