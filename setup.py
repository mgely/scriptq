import setuptools

setuptools.setup(
    name="scriptq",
    version="1.0",
    author="Mario Gely",
    author_email="mario.f.gely@gmail.com",
    description="Python script queuer",
    long_description="A convinient way to run your python scripts one after the other.",
    long_description_content_type="text/markdown",
    url="https://github.com/mgely/scriptq",
    package_dir={"scriptq": "src"},
    packages=["scriptq"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">3.0.0",
    include_package_data=True,
    package_data={"scriptq": ["graphics/*"]},
)
