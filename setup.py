import os
import sys
from setuptools import setup, find_packages
from tethys_apps.app_installation import custom_develop_command, custom_install_command

### Apps Definition ###
app_package = 'recession_analyzer'
release_package = 'tethysapp-' + app_package
app_class = 'recession_analyzer.app:RecessionAnalyzer'
app_package_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tethysapp', app_package)

### Python Dependencies ###
dependencies = ['simplejson', 'pandas', 'cPickle', 'simplejson', 'zipfile', 'scipy', 'lxml']

setup(
    name=release_package,
    version='0.0.1',
    description='Recession analyzer',
    long_description='',
    keywords='',
    author='David Dralle and Nathaniel Karst',
    author_email='dralle@berkeley.edu, nkarst@babson.edu',
    url='',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['tethysapp', 'tethysapp.' + app_package],
    include_package_data=True,
    zip_safe=False,
    install_requires=dependencies,
    cmdclass={
        'install': custom_install_command(app_package, app_package_dir, dependencies),
        'develop': custom_develop_command(app_package, app_package_dir, dependencies)
    }
)
