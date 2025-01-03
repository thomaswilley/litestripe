import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="django-litestripe", 
    version="0.1.0",
    author="thomaswilley",
    description="A fast, lightweight Django app for integrating Stripe subscriptions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/thomaswilley/litestripe",
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=[
        "Django>=3.2",
        "stripe>=2.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Framework :: Django",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)


