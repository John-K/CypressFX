#! /usr/bin/env python
"""CypressFX package setuptools installer."""

import setuptools

###############################################################################
# arguments for the setup command
###############################################################################
name = 'CypressFX'
desc = 'Python module to program Cypress FX EZ-USB series chipsets'
long_desc = ''

version = '0.2'

classifiers = [
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Natural Language :: English',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: POSIX :: Linux',
    'Operating System :: MacOS :: MacOS X',
    'Programming Language :: Python',
    'Topic :: Software Development :: Embedded Systems',
    'Topic :: System :: Boot',
    'Topic :: System :: Hardware',
    'Topic :: System :: Hardware :: Hardware Drivers',
    'Topic :: System :: Installation/Setup',
    'Topic :: System :: Recovery Tools',
    'Topic :: Utilities',
]

author = 'John Kelley'
author_email = 'john@kelley.ca'

url = 'https://github.com/John-K/CypressFX'
cp_license = 'BSD'

keywords = ['cypress', 'fx2', 'fxload', 'usb']

packages = ['CypressFX']

package_data = {'CypressFX' : ['*.hex']}

scripts = ['scripts/fxload.py']

install_requires = [
    'pyusb',
    'intelhex',
]

entry_points = {}
###############################################################################
# end arguments for setup
###############################################################################

setup_params = dict(
    name=name,
    description=desc,
    version=version,
    long_description=long_desc,
    classifiers=classifiers,
    author=author,
    author_email=author_email,
    url=url,
    license=cp_license,
    keywords=keywords,
    packages=packages,
    package_data=package_data,
    scripts=scripts,
    entry_points=entry_points,
    include_package_data=True,
    install_requires=install_requires,
    python_requires='>=2.7,!=3.0.*',
)

def main():
    """Package installation entry point."""
    setuptools.setup(**setup_params)

if __name__ == '__main__':
    main()
