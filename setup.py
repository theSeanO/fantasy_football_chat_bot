from setuptools import setup

setup(
    name='gamedaybot',

    packages=['gamedaybot'],

    include_package_data=True,

    version='0.3.0',

    description='ESPN fantasy football Chat Bot',

    author=['Dean Carlson', 'Sean Gallardo'],

    author_email=['deantcarlson@gmail.com', 'sdvgallardo@gmail.com'],

    install_requires=['requests>=2.0.0,<3.0.0', 'espn_api>=0.30.0', 'apscheduler==3.3.0', 'datetime'],

    test_suite='nose.collector',

    tests_require=['nose', 'requests_mock'],

    url='https://github.com/sdvgallardo/fantasy_football_chat_bot-vS',

    classifiers=[
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
