from setuptools import setup, find_packages
setup(
    name = 'longtermphotzp',
    version="8.1.17"
            "",
    author='Daniel Harbeck',
    author_email='dharbeck@lco.global',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages = find_packages(),
    entry_points = {
        'console_scripts': ['photcalibration = longtermphotzp.photcalibration:photzpmain',
                            'longtermphotzp = longtermphotzp.longtermphotzp:longtermphotzp']
    }
)
