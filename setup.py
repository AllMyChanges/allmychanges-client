from setuptools import setup, find_packages

setup(version='0.6.1',
      name='allmychanges',
      description='A command line client to AllMyChanges.com.',
      license='BSD',
      keywords='changelog tracker allmychanges release notes',
      url='https://github.com/svetlyak40wt/allmychanges',
      author='Artemenko Alexander',
      author_email='svetlyak.40wt@gmail.com',
      packages=find_packages(),
      entry_points={
          'console_scripts': [
              'amch = allmychanges.client:main']},
      install_requires=['click>=2.2,<3.0',
                        'tablib>=0.10.0,<0.11.0',
                        'requests>=2.3.0,<3.0.0'])
