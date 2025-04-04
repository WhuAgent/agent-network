from setuptools import setup, find_packages

setup(
    name="agent_network",
    version="0.0.1",
    author="WhuAgent",
    author_email="zhuyuhan2333@whu.edu.cn",
    description="An Agent Self-Organizing Intelligent Network",
    long_description=open('README.md', encoding="UTF-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/WhuAgent/agent-network.git",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.10',
    install_requires=[
        'annotated-types==0.7.0',
        'anyio==4.4.0',
        'certifi==2024.8.30',
        'distro==1.9.0',
        'exceptiongroup==1.2.2',
        'h11==0.14.0',
        'httpcore==1.0.5',
        'httpx==0.27.2',
        'idna==3.8',
        'jiter==0.5.0',
        'numpy~=1.0',
        'openai==1.44.1',
        'pydantic==2.10.6',
        'pydantic_core==2.27.2',
        'PyYAML==6.0.2',
        'sniffio==1.3.1',
        'tqdm==4.66.5',
        'typing_extensions==4.12.2'
    ],
)
